"""
Gemini function declarations + system prompt — new google.genai SDK style.
TOOL_DECLARATIONS is a plain list of dicts, which types.Tool(function_declarations=...)
accepts directly.
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

ERROR HANDLING
- If a slot is unavailable, autonomously call fetch_slots again and suggest alternatives
- If you are missing a required piece of info, ask for just that one thing
- If the patient is confused, gently guide them back

WHAT TO EXTRACT
- Name (ask if not given)
- Phone number (10-digit, used as unique ID)
- Specialty or doctor name
- Preferred date and time
- Reason or notes (optional)

NEVER
- Make up slot availability — always call fetch_slots
- Confirm a booking without calling book_appointment
- End the call without calling end_conversation
""".strip()


# ─── Function Declarations ─────────────────────────────────────────────────
# Plain dicts — compatible with types.Tool(function_declarations=TOOL_DECLARATIONS)
# in the new google.genai SDK.

TOOL_DECLARATIONS = [
    {
        "name": "identify_user",
        "description": "Identify or register a patient by their phone number. Call this before any appointment action.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone": {
                    "type": "string",
                    "description": "Patient's 10-digit phone number",
                },
                "name": {
                    "type": "string",
                    "description": "Patient's full name if provided",
                },
            },
            "required": ["phone"],
        },
    },
    {
        "name": "fetch_slots",
        "description": "Fetch available appointment slots. Filter by specialty, doctor name, and/or date.",
        "parameters": {
            "type": "object",
            "properties": {
                "specialty": {
                    "type": "string",
                    "description": "Medical specialty e.g. Cardiology, Dermatology, General Physician",
                },
                "doctor_name": {
                    "type": "string",
                    "description": "Specific doctor name if patient has a preference",
                },
                "date": {
                    "type": "string",
                    "description": "Requested date in YYYY-MM-DD format",
                },
            },
        },
    },
    {
        "name": "book_appointment",
        "description": "Book a specific slot for a patient. Prevents double booking.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_phone": {
                    "type": "string",
                    "description": "Patient's phone number",
                },
                "slot_id": {
                    "type": "string",
                    "description": "The slot ID from fetch_slots result",
                },
                "notes": {
                    "type": "string",
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
            "type": "object",
            "properties": {
                "user_phone": {
                    "type": "string",
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
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "string",
                    "description": "The appointment ID to cancel",
                },
                "user_phone": {
                    "type": "string",
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
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "string",
                    "description": "Current appointment ID",
                },
                "user_phone": {
                    "type": "string",
                    "description": "Patient's phone number",
                },
                "new_slot_id": {
                    "type": "string",
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
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Current session ID",
                },
                "user_phone": {
                    "type": "string",
                    "description": "Patient's phone number if identified",
                },
            },
            "required": ["session_id"],
        },
    },
]
