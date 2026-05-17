/**
 * App.jsx — Root component
 * Owns all shared state: session, tool events, transcript, appointments, summary.
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
  const [transcript, setTranscript]     = useState([])
  const [toolEvents, setToolEvents]     = useState([])
  const [appointments, setAppointments] = useState([])
  const [agentSpeaking, setAgentSpeaking] = useState(false)
  const [showSummary, setShowSummary]   = useState(false)
  const [userPhone, setUserPhone]       = useState(null)

  const transcriptRef = useRef(transcript)
  transcriptRef.current = transcript

  // ── Tool event handler ───────────────────────────────────
  const handleToolEvent = useCallback((event) => {
    setToolEvents(prev => [...prev, event])

    // Extract user phone from identify_user result
    if (event.type === 'tool_done' && event.tool === 'identify_user') {
      const phone = event.result?.user?.phone
      if (phone) setUserPhone(phone)
    }

    // Update appointments from booking / retrieval results
    if (event.type === 'tool_done') {
      if (event.tool === 'book_appointment' && event.result?.appointment) {
        const a = event.result.appointment
        setAppointments(prev => [...prev, { ...a, status: 'booked' }])
      }
      if (event.tool === 'retrieve_appointments' && event.result?.appointments) {
        setAppointments(event.result.appointments)
      }
      if (event.tool === 'cancel_appointment' && event.result?.status === 'cancelled') {
        setAppointments(prev =>
          prev.map(a => a.id === event.result.appointment_id ? { ...a, status: 'cancelled' } : a)
        )
      }
      if (event.tool === 'end_conversation') {
        setShowSummary(true)
      }
    }
  }, [])

  // ── Transcript / speaking handler ────────────────────────
  const handleTranscript = useCallback((data) => {
    if (typeof data.speaking === 'boolean') {
      setAgentSpeaking(data.speaking)
      return
    }
    if (data.content) {
      setTranscript(prev => [...prev, { ...data, timestamp: Date.now() / 1000 }])
    }
  }, [])

  // ── Voice session ────────────────────────────────────────
  const { status, isMuted, sessionId, connect, disconnect, toggleMute } = useVoiceSession({
    onToolEvent: handleToolEvent,
    onTranscript: handleTranscript,
  })

  const handleDisconnect = useCallback(async () => {
    await disconnect()
    setShowSummary(true)
  }, [disconnect])

  return (
    <div className="app-layout">
      <Header status={status} sessionId={sessionId} />

      {/* Left: Transcript */}
      <Transcript messages={transcript} />

      {/* Center: Call interface */}
      <CallInterface
        status={status}
        isMuted={isMuted}
        agentSpeaking={agentSpeaking}
        onConnect={connect}
        onDisconnect={handleDisconnect}
        onToggleMute={toggleMute}
      />

      {/* Right: Tool status + Appointments */}
      <div className="panel" style={{ overflow: 'hidden' }}>
        <div style={{ flex: '0 0 auto' }}>
          <ToolStatus events={toolEvents} />
        </div>
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <AppointmentPanel appointments={appointments} />
        </div>
      </div>

      {/* Summary modal */}
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
