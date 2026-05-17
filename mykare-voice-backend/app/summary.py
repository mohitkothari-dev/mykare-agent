"""
Generates a structured call summary using Gemini at end of conversation.
Target: < 10 seconds generation time (use gemini-2.0-flash).
"""
import json
import time
import logging
from datetime import datetime

from google import genai

from app.config import settings
from app.database import get_db

logger = logging.getLogger("mykare.summary")

client = genai.Client(api_key=settings.GEMINI_API_KEY)

SUMMARY_PROMPT = """
You are a medical call transcription assistant. Given a conversation transcript, generate a structured JSON summary.

Return ONLY valid JSON with this exact shape:
{{
  "summary": "2-3 sentence plain English summary of what happened in the call",
  "appointments": [
    {{
      "doctor": "Doctor name",
      "specialty": "Specialty",
      "date": "YYYY-MM-DD",
      "time": "HH:MM",
      "action": "booked | cancelled | modified"
    }}
  ],
  "preferences": {{
    "preferred_specialty": "if mentioned",
    "preferred_time": "morning | afternoon | evening | if mentioned",
    "notes": "any other patient preference"
  }},
  "intent": "booking | cancellation | inquiry | modification | other",
  "patient_name": "extracted name or null",
  "patient_phone": "extracted phone or null"
}}

TRANSCRIPT:
{transcript}
"""


async def generate_summary(
    session_id: str,
    transcript: list[dict],
    user_phone: str | None = None,
) -> dict:
    """
    Generate a call summary from transcript. Saves to DB and returns result.
    Completes in < 10 seconds using Gemini Flash.
    """
    start = time.time()

    # Format transcript for Gemini
    formatted = "\n".join(
        f"[{t.get('role', 'unknown').upper()}]: {t.get('content', '')}"
        for t in transcript
    )

    prompt = SUMMARY_PROMPT.format(transcript=formatted)

    try:
        response = await client.aio.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt
        )
        raw = response.text.strip()

        # Strip markdown code blocks if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        summary_data = json.loads(raw)

    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        summary_data = {
            "summary": "Call completed. Summary generation encountered an issue.",
            "appointments": [],
            "preferences": {},
            "intent": "other",
            "patient_name": None,
            "patient_phone": user_phone,
        }

    elapsed = time.time() - start
    logger.info(f"Summary generated in {elapsed:.2f}s")

    result = {
        **summary_data,
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat(),
        "generation_time_ms": int(elapsed * 1000),
    }

    # Persist to DB
    _save_session(session_id, user_phone, transcript, result)

    return result


def _save_session(
    session_id: str,
    user_phone: str | None,
    transcript: list[dict],
    summary: dict,
):
    """Persist call session and summary to Supabase."""
    try:
        db = get_db()
        user_id = None

        if user_phone:
            user_res = db.table("users").select("id").eq("phone", user_phone).execute()
            if user_res.data:
                user_id = user_res.data[0]["id"]

        db.table("call_sessions").upsert({
            "session_id": session_id,
            "user_id": user_id,
            "transcript": transcript,
            "summary": summary.get("summary"),
            "appointments_made": summary.get("appointments", []),
            "user_preferences": summary.get("preferences", {}),
            "ended_at": datetime.utcnow().isoformat(),
        }).execute()

    except Exception as e:
        logger.warning(f"Failed to save session to DB: {e}")
