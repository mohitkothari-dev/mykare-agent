"""
LiveKit Voice Agent — Mykare
Pipeline: Deepgram STT → Gemini LLM (with function calling) → Cartesia TTS

Run with:
    python -m app.agent dev
"""
import asyncio
import json
import logging
import uuid
from typing import Optional

from google import genai
from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
    DEFAULT_API_CONNECT_OPTIONS,
)
from livekit.agents.voice import Agent as VoiceAssistant
from livekit.plugins import cartesia, deepgram, silero

from app.config import settings
from app.gemini_tools import SYSTEM_PROMPT, TOOL_DECLARATIONS
from app.tools import (
    identify_user,
    fetch_slots,
    book_appointment,
    retrieve_appointments,
    cancel_appointment,
    modify_appointment,
    end_conversation,
)

logger = logging.getLogger("mykare.agent")

# Configure Gemini Client
client = genai.Client(api_key=settings.GEMINI_API_KEY)


# ─── WebSocket Event Emitter ───────────────────────────────────────────────
# We publish tool events to the LiveKit room's data channel so the
# frontend receives them in real-time without a separate WebSocket.

async def emit_tool_event(ctx: JobContext, event: dict):
    """Publish a tool event to all participants in the room."""
    try:
        payload = json.dumps(event).encode()
        await ctx.room.local_participant.publish_data(
            payload,
            reliable=True,
            topic="tool_event",
        )
    except Exception as e:
        logger.warning(f"Failed to emit tool event: {e}")


# ─── Gemini LLM Wrapper ────────────────────────────────────────────────────

class GeminiLLM(llm.LLM):
    """
    Wraps Google Gemini with function calling support.
    Maintains multi-turn conversation history within a session.
    """

    def __init__(self, ctx: JobContext, session_id: str):
        super().__init__()
        self._ctx = ctx
        self._session_id = session_id
        self._chat = client.chats.create(
            model=settings.GEMINI_MODEL,
            config={
                "tools": [{"function_declarations": TOOL_DECLARATIONS}],
                "system_instruction": SYSTEM_PROMPT,
            }
        )
        self._transcript: list[dict] = []

    @property
    def transcript(self) -> list[dict]:
        return self._transcript

    async def chat(
        self,
        chat_ctx: llm.ChatContext,
        fnc_ctx: Optional[llm.ToolContext] = None,
    ) -> "GeminiStream":
        # Extract the latest user message
        last_user_msg = ""
        for msg in reversed(chat_ctx.messages):
            if msg.role == llm.ChatRole.USER:
                last_user_msg = msg.content if isinstance(msg.content, str) else ""
                break

        return GeminiStream(
            gemini_llm=self,
            user_message=last_user_msg,
        )

    async def _process_message(self, user_message: str) -> str:
        """Send message to Gemini, handle tool calls, return final text response."""
        import time

        self._transcript.append({
            "role": "user",
            "content": user_message,
            "timestamp": time.time(),
        })

        # google-genai handles the conversation state in the chat object
        response = client.chats.send(message=user_message)

        # Agentic loop: keep processing until no more function calls
        while True:
            text_parts = []
            tool_calls = []

            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.call:
                        tool_calls.append(part.call)
                    elif part.text:
                        text_parts.append(part.text)

            if not tool_calls:
                # Final text response
                final_text = "".join(text_parts)
                self._transcript.append({
                    "role": "assistant",
                    "content": final_text,
                    "timestamp": time.time(),
                })
                return final_text

            # Execute all tool calls
            tool_responses = []
            for tc in tool_calls:
                tool_name = tc.name
                tool_args = tc.args

                logger.info(f"Tool call: {tool_name}({tool_args})")

                # Notify frontend
                await emit_tool_event(self._ctx, {
                    "type": "tool_start",
                    "tool": tool_name,
                    "args": tool_args,
                    "session_id": self._session_id,
                })

                # Execute tool
                result = await _execute_tool(tool_name, tool_args)

                logger.info(f"Tool result: {tool_name} → {result}")

                # Notify frontend with result
                await emit_tool_event(self._ctx, {
                    "type": "tool_done",
                    "tool": tool_name,
                    "result": result,
                    "session_id": self._session_id,
                })

                tool_responses.append(
                    {
                        "function_response": {
                            "name": tool_name,
                            "response": {"result": json.dumps(result, default=str)},
                        }
                    }
                )

            # Send all tool results back to Gemini
            response = client.chats.send(message=tool_responses)


class GeminiStream(llm.LLMStream):
    """Wraps GeminiLLM._process_message as an LLMStream."""

    def __init__(self, gemini_llm: GeminiLLM, user_message: str):
        super().__init__(
            gemini_llm,
            chat_ctx=llm.ChatContext(),
            tools=[],
            conn_options=llm.DEFAULT_API_CONNECT_OPTIONS,
        )
        self._gemini_llm = gemini_llm
        self._user_message = user_message

    async def _run(self):
        text = await self._gemini_llm._process_message(self._user_message)
        # Emit final text as a chat chunk
        self._event_ch.send_nowait(
            llm.ChatChunk(
                id=str(uuid.uuid4()),
                delta=llm.ChoiceDelta(role="assistant", content=text),
            )
        )


# ─── Tool Dispatcher ───────────────────────────────────────────────────────

async def _execute_tool(name: str, args: dict) -> dict:
    """Route tool calls to their implementations."""
    dispatch = {
        "identify_user": lambda: identify_user(**args),
        "fetch_slots": lambda: fetch_slots(
            specialty=args.get("specialty"),
            doctor_name=args.get("doctor_name"),
            date_str=args.get("date"),
        ),
        "book_appointment": lambda: book_appointment(**args),
        "retrieve_appointments": lambda: retrieve_appointments(**args),
        "cancel_appointment": lambda: cancel_appointment(**args),
        "modify_appointment": lambda: modify_appointment(**args),
        "end_conversation": lambda: end_conversation(**args),
    }
    handler = dispatch.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        return await handler()
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return {"error": str(e)}


# ─── Agent Entry Point ─────────────────────────────────────────────────────

async def entrypoint(ctx: JobContext):
    """Called by LiveKit Workers when a new room job is dispatched."""
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    session_id = str(uuid.uuid4())
    logger.info(f"Agent starting in room {ctx.room.name}, session={session_id}")

    gemini_llm = GeminiLLM(ctx=ctx, session_id=session_id)

    assistant = VoiceAssistant(
        instructions=SYSTEM_PROMPT,
        vad=silero.VAD.load(),
        stt=deepgram.STT(api_key=settings.DEEPGRAM_API_KEY),
        llm=gemini_llm,
        tts=cartesia.TTS(
            api_key=settings.CARTESIA_API_KEY,
            voice=settings.CARTESIA_VOICE_ID,
        ),
    )

    assistant.start(ctx.room)

    # Greet the patient on connect
    await asyncio.sleep(1)
    await assistant.say(
        "Hello! I'm Mia from Mykare Health. How can I help you today?",
        allow_interruptions=True,
    )


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
            ws_url=settings.LIVEKIT_URL,
        )
    )
