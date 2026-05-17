from pydantic import BaseModel
from typing import Optional, List
from datetime import date, time, datetime


# ─── User ──────────────────────────────────────────────────────────────────

class UserIdentify(BaseModel):
    phone: str
    name: Optional[str] = None


class UserOut(BaseModel):
    id: str
    phone: str
    name: Optional[str]
    created_at: datetime


# ─── Slots ─────────────────────────────────────────────────────────────────

class SlotFetch(BaseModel):
    specialty: Optional[str] = None
    doctor_name: Optional[str] = None
    date: Optional[str] = None          # ISO format: YYYY-MM-DD


class SlotOut(BaseModel):
    id: str
    doctor_id: str
    doctor_name: str
    specialty: str
    date: str
    time_slot: str


# ─── Appointment ───────────────────────────────────────────────────────────

class AppointmentBook(BaseModel):
    user_phone: str
    slot_id: str
    notes: Optional[str] = None


class AppointmentCancel(BaseModel):
    appointment_id: str
    user_phone: str


class AppointmentModify(BaseModel):
    appointment_id: str
    user_phone: str
    new_slot_id: str


class AppointmentOut(BaseModel):
    id: str
    doctor_name: str
    specialty: str
    date: str
    time_slot: str
    status: str
    notes: Optional[str]
    created_at: datetime


# ─── Session / Summary ─────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    session_id: str
    user_phone: Optional[str] = None


class SummaryRequest(BaseModel):
    session_id: str
    transcript: List[dict]          # [{role, content, timestamp}]
    user_phone: Optional[str] = None


class SummaryOut(BaseModel):
    summary: str
    appointments: List[dict]
    preferences: dict
    timestamp: datetime
    session_id: str


# ─── LiveKit Token ─────────────────────────────────────────────────────────

class TokenRequest(BaseModel):
    room_name: str
    participant_name: str = "user"


class TokenOut(BaseModel):
    token: str
    room_name: str
    livekit_url: str
