# Mykare Voice AI — Backend

FastAPI backend for the Mykare AI voice appointment agent.

## Stack
- **FastAPI** — REST API + WebSocket
- **LiveKit Agents** — voice pipeline orchestration
- **Deepgram** — speech-to-text
- **Cartesia** — text-to-speech
- **Google Gemini** — LLM with function calling
- **Supabase** — PostgreSQL database

## Project Structure
```
app/
├── main.py          # FastAPI app, REST endpoints
├── agent.py         # LiveKit voice agent (run separately)
├── gemini_tools.py  # Gemini function declarations + system prompt
├── tools.py         # Tool implementations (DB operations)
├── summary.py       # Call summary generation
├── schemas.py       # Pydantic request/response models
├── database.py      # Supabase client
└── config.py        # Settings from .env

supabase/
└── schema.sql       # Database schema + seed data
```

## Setup

### 1. Clone and install
```bash
git clone https://github.com/your-org/mykare-voice-backend
cd mykare-voice-backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Set up Supabase
- Create a project at https://supabase.com
- Open the SQL editor and run `supabase/schema.sql`
- Copy your project URL and anon key to `.env`

### 4. Run the API server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Run the LiveKit Agent (separate terminal)
```bash
python -m app.agent dev
```

> The agent connects to LiveKit and waits for rooms. When the frontend
> creates a room and connects, the agent auto-joins and starts the voice session.

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/livekit/token` | Get LiveKit room token |
| GET | `/avatar/session` | Get Tavus avatar session |
| POST | `/tools/identify-user` | Identify patient |
| POST | `/tools/fetch-slots` | Get available slots |
| POST | `/tools/book-appointment` | Book appointment |
| GET | `/tools/appointments/{phone}` | Get patient appointments |
| POST | `/tools/cancel-appointment` | Cancel appointment |
| POST | `/tools/modify-appointment` | Reschedule appointment |
| POST | `/summary` | Generate call summary |

Full docs at `http://localhost:8000/docs`

## Tool Event Flow

The agent publishes tool events to the LiveKit room data channel (topic: `tool_event`).
The frontend subscribes to these and updates the UI in real time.

```json
// Tool started
{ "type": "tool_start", "tool": "book_appointment", "args": {...}, "session_id": "..." }

// Tool completed  
{ "type": "tool_done", "tool": "book_appointment", "result": {...}, "session_id": "..." }
```

## Deployment

```bash
# Railway
railway init && railway up

# Or Docker
docker build -t mykare-backend .
docker run -p 8000:8000 --env-file .env mykare-backend
```
