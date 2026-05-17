"""
Tool implementations for the Mykare Voice AI Agent.
Each function maps 1:1 to a Gemini function declaration.
"""
import uuid
from datetime import datetime, date
from typing import Optional
from app.database import get_db


# ─── identify_user ─────────────────────────────────────────────────────────

async def identify_user(phone: str, name: Optional[str] = None) -> dict:
    """
    Look up a user by phone number. Create if not found.
    Returns user info — this is always the first tool called.
    """
    db = get_db()
    phone = phone.strip().replace(" ", "").replace("-", "")

    result = db.table("users").select("*").eq("phone", phone).execute()

    if result.data:
        user = result.data[0]
        # Update name if provided and not already set
        if name and not user.get("name"):
            db.table("users").update({"name": name}).eq("id", user["id"]).execute()
            user["name"] = name
        return {"status": "found", "user": user}

    # Create new user
    new_user = {
        "id": str(uuid.uuid4()),
        "phone": phone,
        "name": name,
        "created_at": datetime.utcnow().isoformat(),
    }
    db.table("users").insert(new_user).execute()
    return {"status": "created", "user": new_user}


# ─── fetch_slots ───────────────────────────────────────────────────────────

async def fetch_slots(
    specialty: Optional[str] = None,
    doctor_name: Optional[str] = None,
    date_str: Optional[str] = None,
) -> dict:
    """
    Return available appointment slots filtered by specialty / doctor / date.
    Joins slots with doctors table for full info.
    """
    db = get_db()

    # Build query
    query = (
        db.table("slots")
        .select("*, doctors(name, specialty)")
        .eq("is_available", True)
    )

    if date_str:
        query = query.eq("date", date_str)

    result = query.execute()
    slots = result.data or []

    # Filter by specialty / doctor in Python (Supabase join filtering is limited)
    if specialty:
        slots = [
            s for s in slots
            if specialty.lower() in s.get("doctors", {}).get("specialty", "").lower()
        ]
    if doctor_name:
        slots = [
            s for s in slots
            if doctor_name.lower() in s.get("doctors", {}).get("name", "").lower()
        ]

    # Flatten for readability
    formatted = [
        {
            "slot_id": s["id"],
            "doctor_name": s["doctors"]["name"],
            "specialty": s["doctors"]["specialty"],
            "date": s["date"],
            "time_slot": s["time_slot"],
        }
        for s in slots
    ]

    return {
        "available_slots": formatted,
        "count": len(formatted),
    }


# ─── book_appointment ──────────────────────────────────────────────────────

async def book_appointment(
    user_phone: str,
    slot_id: str,
    notes: Optional[str] = None,
) -> dict:
    """
    Book a slot for a user. Prevents double-booking via DB constraint.
    """
    db = get_db()

    # Get user
    user_result = db.table("users").select("id").eq("phone", user_phone).execute()
    if not user_result.data:
        return {"status": "error", "message": "User not found. Please identify first."}
    user_id = user_result.data[0]["id"]

    # Get slot + doctor info
    slot_result = (
        db.table("slots")
        .select("*, doctors(name, specialty)")
        .eq("id", slot_id)
        .eq("is_available", True)
        .execute()
    )
    if not slot_result.data:
        return {"status": "error", "message": "Slot not available or already booked."}

    slot = slot_result.data[0]
    doctor = slot["doctors"]

    # Insert appointment
    appointment = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "slot_id": slot_id,
        "doctor_name": doctor["name"],
        "specialty": doctor["specialty"],
        "date": slot["date"],
        "time_slot": slot["time_slot"],
        "status": "booked",
        "notes": notes,
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        db.table("appointments").insert(appointment).execute()
    except Exception as e:
        return {"status": "error", "message": f"Booking failed: {str(e)}"}

    # Mark slot as unavailable
    db.table("slots").update({"is_available": False}).eq("id", slot_id).execute()

    return {
        "status": "booked",
        "appointment": {
            "id": appointment["id"],
            "doctor": doctor["name"],
            "specialty": doctor["specialty"],
            "date": slot["date"],
            "time": slot["time_slot"],
        },
        "message": f"Appointment confirmed with Dr. {doctor['name']} on {slot['date']} at {slot['time_slot']}.",
    }


# ─── retrieve_appointments ─────────────────────────────────────────────────

async def retrieve_appointments(user_phone: str) -> dict:
    """Return all appointments for a user, sorted by date."""
    db = get_db()

    user_result = db.table("users").select("id, name").eq("phone", user_phone).execute()
    if not user_result.data:
        return {"status": "error", "message": "User not found."}

    user = user_result.data[0]
    appts = (
        db.table("appointments")
        .select("*")
        .eq("user_id", user["id"])
        .neq("status", "cancelled")
        .order("date")
        .execute()
    )

    return {
        "user_name": user.get("name"),
        "appointments": appts.data or [],
        "count": len(appts.data or []),
    }


# ─── cancel_appointment ────────────────────────────────────────────────────

async def cancel_appointment(appointment_id: str, user_phone: str) -> dict:
    """Cancel an appointment and free the slot."""
    db = get_db()

    user_result = db.table("users").select("id").eq("phone", user_phone).execute()
    if not user_result.data:
        return {"status": "error", "message": "User not found."}
    user_id = user_result.data[0]["id"]

    # Verify ownership
    appt_result = (
        db.table("appointments")
        .select("*")
        .eq("id", appointment_id)
        .eq("user_id", user_id)
        .eq("status", "booked")
        .execute()
    )
    if not appt_result.data:
        return {"status": "error", "message": "Appointment not found or already cancelled."}

    appt = appt_result.data[0]

    # Cancel appointment
    db.table("appointments").update({"status": "cancelled"}).eq("id", appointment_id).execute()

    # Free the slot
    db.table("slots").update({"is_available": True}).eq("id", appt["slot_id"]).execute()

    return {
        "status": "cancelled",
        "message": f"Appointment with Dr. {appt['doctor_name']} on {appt['date']} at {appt['time_slot']} has been cancelled.",
    }


# ─── modify_appointment ────────────────────────────────────────────────────

async def modify_appointment(
    appointment_id: str,
    user_phone: str,
    new_slot_id: str,
) -> dict:
    """Reschedule: cancel old slot, book new one in a single logical operation."""
    # Cancel existing
    cancel_result = await cancel_appointment(appointment_id, user_phone)
    if cancel_result["status"] != "cancelled":
        return cancel_result

    # Book new slot
    book_result = await book_appointment(user_phone, new_slot_id)
    if book_result["status"] != "booked":
        return {"status": "error", "message": f"Old appointment cancelled but new booking failed: {book_result['message']}"}

    return {
        "status": "modified",
        "new_appointment": book_result["appointment"],
        "message": f"Appointment rescheduled. {book_result['message']}",
    }


# ─── end_conversation ──────────────────────────────────────────────────────

async def end_conversation(session_id: str, user_phone: Optional[str] = None) -> dict:
    """
    Signal end of call. Returns summary trigger data.
    Actual summary is generated by Gemini in the summary endpoint.
    """
    return {
        "status": "ended",
        "session_id": session_id,
        "message": "Thank you for calling Mykare. Have a healthy day!",
    }
