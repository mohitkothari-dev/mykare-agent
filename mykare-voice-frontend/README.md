# Mykare Voice AI — Frontend

React + Vite frontend for the Mykare AI voice appointment agent.

## Stack
- **Vite + React 18** — fast dev + build
- **LiveKit Components React** — room connection, audio tracks
- **DM Sans / Syne / DM Mono** — clinical precision typography
- **CSS Variables** — full design system, no external CSS framework

## Project Structure
```
src/
├── App.jsx                    # Root component, shared state
├── main.jsx                   # Entry point
├── index.css                  # Design system (tokens, components)
├── lib/
│   └── api.js                 # Backend API calls
├── hooks/
│   └── useVoiceSession.js     # LiveKit connection + data channel
└── components/
    ├── Header.jsx             # Top bar with status
    ├── CallInterface.jsx      # Center: avatar + controls
    ├── Transcript.jsx         # Left: live conversation
    ├── ToolStatus.jsx         # Right-top: tool call feed
    ├── AppointmentPanel.jsx   # Right-bottom: appointments
    └── SummaryModal.jsx       # End-of-call summary sheet
```

## UI Layout
```
┌────────────────── Header (status + session ID) ──────────────────┐
│  Transcript   │        Avatar + Controls       │  Tool Events    │
│  (left panel) │         (center panel)         │ + Appointments  │
│               │                                │  (right panel)  │
└───────────────┴────────────────────────────────┴─────────────────┘
                         [Summary Modal on call end]
```

## Setup

```bash
git clone https://github.com/your-org/mykare-voice-frontend
cd mykare-voice-frontend
npm install
cp .env.example .env
npm run dev
```

## Environment Variables

```env
VITE_API_URL=http://localhost:8000   # Backend URL
```

## Data Flow

1. User clicks **Start Call** → `useVoiceSession` requests a LiveKit token
2. Frontend joins the LiveKit room → backend agent auto-joins
3. Agent handles voice pipeline (Deepgram STT → Gemini → Cartesia TTS)
4. Agent publishes `tool_event` JSON to LiveKit data channel
5. Frontend receives events → updates Tool Status + Appointment panels live
6. On call end → `SummaryModal` fetches generated summary from backend

## Design System

All design tokens are CSS variables in `index.css`. Key colors:

| Variable | Value | Use |
|----------|-------|-----|
| `--accent` | `#00c7a3` | Primary CTA, active states |
| `--bg-base` | `#050a0f` | Page background |
| `--bg-card` | `#101d2e` | Card backgrounds |
| `--text-primary` | `#e2eff8` | Main text |

## Deployment (Vercel)

```bash
npm run build
# Push to GitHub → Vercel auto-deploys
# Set VITE_API_URL to your Railway/Render backend URL
```
