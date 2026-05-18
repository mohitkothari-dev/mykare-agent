"""
LiveKit Voice Agent — Mykare
Pipeline: Deepgram STT → Gemini LLM (with function calling) → Cartesia TTS

Run with:
    python -m app.agent dev
"""
import asyncio
import json
import logging
import time
import uuid
from typing import Optional

from google import genai
from google.genai import types
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    DEFAULT_API_CONNECT_OPTIONS,
    JobContext,
    NOT_GIVEN,
    WorkerOptions,
    cli,
    llm,
)
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


# ─── Event Emitter ─────────────────────────────────────────────────────────

async def emit_event(ctx: JobContext, event: dict):
    try:
        payload = json.dumps(event, default=str).encode()
        await ctx.room.local_participant.publish_data(
            payload,
            reliable=True,
            topic=event.get("type", "event"),
        )
    except Exception as e:
        logger.warning(f"emit_event failed: {e}")


# ─── Gemini LLM Wrapper ────────────────────────────────────────────────────

class GeminiLLM(llm.LLM):
    def __init__(self, ctx: JobContext, session_id: str):
        super().__init__()
        self._ctx = ctx
        self._session_id = session_id
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # FIX 2: trailing comma after create(...) was making _chat a tuple, not a chat object
        # Before: self._chat = self._client.aio.chats.create(...),   ← tuple!
        # After:  self._chat = self._client.aio.chats.create(...)    ← chat object
        self._chat = self._client.aio.chats.create(
            model=settings.GEMINI_MODEL,
            config=types.GenerateContentConfig(
                tools=[types.Tool(function_declarations=TOOL_DECLARATIONS)],
                system_instruction=SYSTEM_PROMPT,
            ),
        )

    def chat(
        self,
        *,
        chat_ctx: llm.ChatContext,
        tools=None,
        conn_options=DEFAULT_API_CONNECT_OPTIONS,
        parallel_tool_calls=NOT_GIVEN,
        tool_choice=NOT_GIVEN,
        extra_kwargs=NOT_GIVEN,
    ) -> "GeminiStream":
        last_user_msg = ""
        for msg in reversed(chat_ctx.messages()):
            if msg.role == "user":
                last_user_msg = msg.text_content or ""
                break
        return GeminiStream(
            gemini_llm=self,
            user_message=last_user_msg,
            chat_ctx=chat_ctx,
            tools=tools or [],
            conn_options=conn_options,
        )

    async def _process_message(self, user_message: str) -> str:
        """Agentic loop: call Gemini, handle tool calls, return final text."""
        response = await self._chat.send_message(message=user_message)

        while True:
            text_parts = []
            function_calls = []

            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        function_calls.append(part.function_call)
                    elif part.text:
                        text_parts.append(part.text)

            if not function_calls:
                return " ".join(text_parts)

            function_responses = []
            for fc in function_calls:
                tool_name = fc.name
                tool_args = dict(fc.args)
                logger.info(f"Tool call: {tool_name}({tool_args})")

                await emit_event(self._ctx, {
                    "type": "tool_event",
                    "event": "tool_start",
                    "tool": tool_name,
                    "args": tool_args,
                    "session_id": self._session_id,
                })

                result = await _execute_tool(tool_name, tool_args)
                logger.info(f"Tool result: {tool_name} → {result}")

                await emit_event(self._ctx, {
                    "type": "tool_event",
                    "event": "tool_done",
                    "tool": tool_name,
                    "result": result,
                    "session_id": self._session_id,
                })

                function_responses.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=tool_name,
                            response={"result": json.dumps(result, default=str)},
                        )
                    )
                )

            response = await self._chat.send_message(message=function_responses)


class GeminiStream(llm.LLMStream):
    def __init__(self, gemini_llm: GeminiLLM, user_message: str, chat_ctx, tools, conn_options):
        super().__init__(gemini_llm, chat_ctx=chat_ctx, tools=tools, conn_options=conn_options)
        self._gemini_llm = gemini_llm
        self._user_message = user_message

    async def _run(self):
        text = await self._gemini_llm._process_message(self._user_message)
        self._event_ch.send_nowait(
            llm.ChatChunk(
                id=str(uuid.uuid4()),
                delta=llm.ChoiceDelta(role="assistant", content=text),
            )
        )


# ─── Tool Dispatcher ───────────────────────────────────────────────────────

async def _execute_tool(name: str, args: dict) -> dict:
    dispatch = {
        "identify_user":         lambda: identify_user(**args),
        "fetch_slots":           lambda: fetch_slots(
            specialty=args.get("specialty"),
            doctor_name=args.get("doctor_name"),
            date_str=args.get("date"),
        ),
        "book_appointment":      lambda: book_appointment(**args),
        "retrieve_appointments": lambda: retrieve_appointments(**args),
        "cancel_appointment":    lambda: cancel_appointment(**args),
        "modify_appointment":    lambda: modify_appointment(**args),
        "end_conversation":      lambda: end_conversation(**args),
    }
    handler = dispatch.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        return await handler()
    except Exception as e:
        logger.error(f"Tool {name} raised: {e}")
        return {"error": str(e)}


# ─── Entry Point ───────────────────────────────────────────────────────────

async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    session_id = str(uuid.uuid4())
    logger.info(f"Agent joined room={ctx.room.name} session={session_id}")

    gemini_llm = GeminiLLM(ctx=ctx, session_id=session_id)

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(api_key=settings.DEEPGRAM_API_KEY),
        llm=gemini_llm,
        tts=cartesia.TTS(
            api_key=settings.CARTESIA_API_KEY,
            voice=settings.CARTESIA_VOICE_ID,
        ),
        turn_handling={
            "interruption": {"mode": "vad"}
        }
    )
    agent = Agent(instructions=SYSTEM_PROMPT)

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(ev):
        if not ev.is_final:
            return
        asyncio.ensure_future(emit_event(ctx, {
            "type": "transcript",
            "role": "user",
            "content": ev.transcript,
            "timestamp": time.time(),
            "session_id": session_id,
        }))

    @session.on("conversation_item_added")
    def on_conversation_item_added(ev):
        item = ev.item
        if getattr(item, "type", None) != "message" or getattr(item, "role", None) != "assistant":
            return
        content = item.text_content or ""
        if not content:
            return
        asyncio.ensure_future(emit_event(ctx, {
            "type": "transcript",
            "role": "agent",
            "content": content,
            "timestamp": time.time(),
            "session_id": session_id,
        }))

    @session.on("agent_state_changed")
    def on_agent_state_changed(ev):
        if ev.new_state == "speaking":
            speaking = True
        elif ev.old_state == "speaking":
            speaking = False
        else:
            return
        asyncio.ensure_future(emit_event(ctx, {
            "type": "speaking_state",
            "speaking": speaking,
            "session_id": session_id,
        }))

    await session.start(agent, room=ctx.room)

    await asyncio.sleep(1)
    session.say(
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
