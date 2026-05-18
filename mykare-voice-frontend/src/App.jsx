/**
 * App.jsx — Root component
 *
 * IMPORTANT: Do NOT import anything from @livekit/components-react here.
 * We use the raw livekit-client Room via useVoiceSession only.
 * LiveKit's prebuilt React UI will override our custom layout if imported.
 */
import { useState, useCallback, useRef } from 'react'
import { useVoiceSession } from './hooks/useVoiceSession'
import Header from './components/Header'
import Transcript from './components/Transcript'
import CallInterface from './components/CallInterface'
import ToolStatus from './components/ToolStatus'
import AppointmentPanel from './components/AppointmentPanel'
import SummaryModal from './components/SummaryModal'

export default function App() {
  const [transcript, setTranscript]       = useState([])
  const [toolEvents, setToolEvents]       = useState([])
  const [appointments, setAppointments]   = useState([])
  const [agentSpeaking, setAgentSpeaking] = useState(false)
  const [showSummary, setShowSummary]     = useState(false)
  const [userPhone, setUserPhone]         = useState(null)

  const transcriptRef = useRef(transcript)
  transcriptRef.current = transcript

  // ── Tool event handler ─────────────────────────────────────────────────
  const handleToolEvent = useCallback((event) => {
    // Normalise: agent can emit {type, event, tool} or {type, tool, event}
    const toolName  = event.tool
    const eventKind = event.event   // "tool_start" | "tool_done"

    setToolEvents(prev => [...prev, { ...event, type: eventKind }])

    if (eventKind === 'tool_done') {
      const result = event.result || {}

      // Extract user phone from identify_user
      if (toolName === 'identify_user' && result.user?.phone) {
        setUserPhone(result.user.phone)
      }

      // Update appointment list live
      if (toolName === 'book_appointment' && result.status === 'booked' && result.appointment) {
        setAppointments(prev => [...prev, { ...result.appointment, status: 'booked' }])
      }
      if (toolName === 'retrieve_appointments' && result.appointments) {
        setAppointments(result.appointments)
      }
      if (toolName === 'cancel_appointment' && result.status === 'cancelled') {
        setAppointments(prev =>
          prev.map(a =>
            a.doctor === event.args?.doctor || a.id === event.args?.appointment_id
              ? { ...a, status: 'cancelled' }
              : a
          )
        )
      }
      if (toolName === 'end_conversation') {
        setShowSummary(true)
      }
    }
  }, [])

  // ── Transcript handler ─────────────────────────────────────────────────
  const handleTranscript = useCallback((data) => {
    if (data.type === 'message' && data.content) {
      setTranscript(prev => [...prev, {
        role:      data.role,
        content:   data.content,
        timestamp: data.timestamp || Date.now() / 1000,
      }])
    }
  }, [])

  // ── Speaking state handler ─────────────────────────────────────────────
  const handleSpeakingState = useCallback((speaking) => {
    setAgentSpeaking(speaking)
  }, [])

  // ── Voice session ──────────────────────────────────────────────────────
  const { status, isMuted, sessionId, localVideoTrack, connect, disconnect, toggleMute } =
    useVoiceSession({
      onToolEvent:     handleToolEvent,
      onTranscript:    handleTranscript,
      onSpeakingState: handleSpeakingState,
    })

  const handleDisconnect = useCallback(async () => {
    await disconnect()
    setShowSummary(true)
  }, [disconnect])

  return (
    <div className="app-layout">
      <Header status={status} sessionId={sessionId} />

      {/* Left — Transcript */}
      <Transcript messages={transcript} />

      {/* Center — Main Interface */}
      <CallInterface
        status={status}
        isMuted={isMuted}
        agentSpeaking={agentSpeaking}
        localVideoTrack={localVideoTrack}
        onConnect={connect}
        onDisconnect={handleDisconnect}
        onToggleMute={toggleMute}
      />

      {/* Right — Tool events + Appointments */}
      <div className="panel" style={{ overflow: 'hidden' }}>
        <div style={{ flex: '0 0 auto' }}>
          <ToolStatus events={toolEvents} />
        </div>
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <AppointmentPanel appointments={appointments} />
        </div>
      </div>

      {/* Summary modal — slides up on call end */}
      {showSummary && (
        <SummaryModal
          sessionId={sessionId}
          transcript={transcriptRef.current}
          userPhone={userPhone}
          onClose={() => setShowSummary(false)}
        />
      )}
    </div>
  )
}
