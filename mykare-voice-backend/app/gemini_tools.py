"""
Gemini function declarations + system prompt for the Mykare voice agent.
These are passed directly to google.genai as tool definitions.
"""

SYSTEM_PROMPT = """
You are Mia, the AI front-desk assistant for Mykare Health — a multi-specialty healthcare platform.
Your job is to help patients book, manage, and inquire about doctor appointments via a voice call.

PERSONA
- Warm, professional, and clear — like a great human receptionist
- Speak in short, natural sentences (you are being spoken aloud via TTS)
- Never use bullet points, markdown, or lists in your responses
- Be concise: prefer 1-2 sentence responses

WORKFLOW (strictly follow this order)
1. Greet the patient and ask how you can help
2. ALWAYS call identify_user before performing any appointment action
3. Extract name, phone, specialty/doctor preference, and desired date from conversation
4. Call fetch_slots when the patient wants to book or see availability
5. Call book_appointment once slot is confirmed
6. Call retrieve_appointments when patient asks about their existing bookings
7. Call cancel_appointment or modify_appointment as needed
8. Call end_conversation when the patient is done — always before saying goodbye

ERROR HANDLING (agentic behavior)
- If a slot is unavailable, autonomously call fetch_slots again and suggest alternatives
- If you're missing a required piece of info, ask for just that one thing
- If the patient is confused, gently guide them back

WHAT TO EXTRACT
- Name (ask if not given)
- Phone number (10-digit, used as unique ID)
- Specialty or doctor name
- Preferred date and time
- Reason/notes (optional)

NEVER
- Make up slot availability — always call fetch_slots
- Confirm a booking without calling book_appointment
- End the call without calling end_conversation
""".strip()


# ─── Function Declarations ─────────────────────────────────────────────────

TOOL_DECLARATIONS = [
    {
        "name": "identify_user",
        "description": "Identify or register a patient by their phone number. Call this before any appointment action.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "phone": {
                    "type": "STRING",
                    "description": "Patient's 10-digit phone number",
                },
                "name": {
                    "type": "STRING",
                    "description": "Patient's full name (if provided)",
                },
            },
            "required": ["phone"],
        },
    },
    {
        "name": "fetch_slots",
        "description": "Fetch available appointment slots. Filter by specialty, doctor name, and/or date.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "specialty": {
                    "type": "STRING",
                    "description": "Medical specialty e.g. Cardiology, Dermatology, General Physician",
                },
                "doctor_name": {
                    "type": "STRING",
                    "description": "Specific doctor's name if patient has a preference",
                },
                "date": {
                    "type": "STRING",
                    "description": "Requested date in YYYY-MM-DD format",
                },
            },
        },
    },
    {
        "name": "book_appointment",
        "description": "Book a specific slot for a patient. Prevents double booking.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "user_phone": {
                    "type": "STRING",
                    "description": "Patient's phone number",
                },
                "slot_id": {
                    "type": "STRING",
                    "description": "The slot ID from fetch_slots result",
                },
                "notes": {
                    "type": "STRING",
                    "description": "Optional notes or reason for visit",
                },
            },
            "required": ["user_phone", "slot_id"],
        },
    },
    {
        "name": "retrieve_appointments",
        "description": "Retrieve all active appointments for a patient.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "user_phone": {
                    "type": "STRING",
                    "description": "Patient's phone number",
                },
            },
            "required": ["user_phone"],
        },
    },
    {
        "name": "cancel_appointment",
        "description": "Cancel a booked appointment and free the slot.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "appointment_id": {
                    "type": "STRING",
                    "description": "The appointment ID to cancel",
                },
                "user_phone": {
                    "type": "STRING",
                    "description": "Patient's phone number for verification",
                },
            },
            "required": ["appointment_id", "user_phone"],
        },
    },
    {
        "name": "modify_appointment",
        "description": "Reschedule an existing appointment to a new slot.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "appointment_id": {
                    "type": "STRING",
                    "description": "Current appointment ID",
                },
                "user_phone": {
                    "type": "STRING",
                    "description": "Patient's phone number",
                },
                "new_slot_id": {
                    "type": "STRING",
                    "description": "New slot ID from fetch_slots",
                },
            },
            "required": ["appointment_id", "user_phone", "new_slot_id"],
        },
    },
    {
        "name": "end_conversation",
        "description": "End the call gracefully. Always call this before saying goodbye.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "session_id": {
                    "type": "STRING",
                    "description": "Current session ID",
                },
                "user_phone": {
                    "type": "STRING",
                    "description": "Patient's phone number if identified",
                },
            },
            "required": ["session_id"],
        },
    },
]
