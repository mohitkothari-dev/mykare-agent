"""
Mykare Voice AI — FastAPI Backend
Handles: REST tool endpoints, LiveKit token generation, call summaries
The LiveKit agent (app/agent.py) runs as a separate worker process.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from livekit import api as livekit_api

from app.config import settings
from app.schemas import (
    AppointmentBook,
    AppointmentCancel,
    AppointmentModify,
    SlotFetch,
    SummaryRequest,
    TokenRequest,
    UserIdentify,
)
from app.tools import (
    book_appointment,
    cancel_appointment,
    fetch_slots,
    identify_user,
    modify_appointment,
    retrieve_appointments,
)
from app.summary import generate_summary

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mykare.api")


# ─── App Lifecycle ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Mykare Voice API starting…")
    yield
    logger.info("Mykare Voice API shutting down")


app = FastAPI(
    title="Mykare Voice AI API",
    description="Backend for AI-powered healthcare appointment voice agent",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "mykare-voice-api"}


# ─── LiveKit Token ─────────────────────────────────────────────────────────

@app.post("/livekit/token")
async def get_livekit_token(req: TokenRequest):
    """
    Generate a LiveKit access token for the frontend to join a room.
    The agent worker will auto-join the same room.
    """
    token = (
        livekit_api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(req.participant_name)
        .with_name(req.participant_name)
        .with_grants(
            livekit_api.VideoGrants(
                room_join=True,
                room=req.room_name,
            )
        )
        .to_jwt()
    )
    return {
        "token": token,
        "room_name": req.room_name,
        "livekit_url": settings.LIVEKIT_URL,
    }


# ─── Tool Endpoints ────────────────────────────────────────────────────────
# These can also be called by external clients for testing.

@app.post("/tools/identify-user")
async def api_identify_user(req: UserIdentify):
    result = await identify_user(phone=req.phone, name=req.name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/tools/fetch-slots")
async def api_fetch_slots(req: SlotFetch):
    result = await fetch_slots(
        specialty=req.specialty,
        doctor_name=req.doctor_name,
        date_str=req.date,
    )
    return result


@app.post("/tools/book-appointment")
async def api_book_appointment(req: AppointmentBook):
    result = await book_appointment(
        user_phone=req.user_phone,
        slot_id=req.slot_id,
        notes=req.notes,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@app.get("/tools/appointments/{phone}")
async def api_get_appointments(phone: str):
    result = await retrieve_appointments(user_phone=phone)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@app.post("/tools/cancel-appointment")
async def api_cancel_appointment(req: AppointmentCancel):
    result = await cancel_appointment(
        appointment_id=req.appointment_id,
        user_phone=req.user_phone,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@app.post("/tools/modify-appointment")
async def api_modify_appointment(req: AppointmentModify):
    result = await modify_appointment(
        appointment_id=req.appointment_id,
        user_phone=req.user_phone,
        new_slot_id=req.new_slot_id,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result


# ─── Summary ───────────────────────────────────────────────────────────────

@app.post("/summary")
async def api_generate_summary(req: SummaryRequest):
    """
    Generate and persist a call summary.
    Called by the agent on end_conversation, or directly for testing.
    Target: < 10 seconds.
    """
    result = await generate_summary(
        session_id=req.session_id,
        transcript=req.transcript,
        user_phone=req.user_phone,
    )
    return result


# ─── Tavus Avatar (optional) ───────────────────────────────────────────────

@app.get("/avatar/session")
async def get_avatar_session():
    """Create a Tavus conversation session for the talking avatar."""
    if not settings.TAVUS_API_KEY or not settings.TAVUS_REPLICA_ID:
        return {"enabled": False, "message": "Tavus not configured"}

    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://tavusapi.com/v2/conversations",
            headers={"x-api-key": settings.TAVUS_API_KEY},
            json={
                "replica_id": settings.TAVUS_REPLICA_ID,
                "conversation_name": "Mykare Appointment Call",
                "custom_greeting": "Hello! I'm Mia from Mykare Health.",
                "properties": {"enable_recording": False},
            },
        )
        if resp.status_code != 200:
            return {"enabled": False, "error": resp.text}
        return {"enabled": True, **resp.json()}
