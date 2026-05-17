/**
 * ToolStatus — right panel (top section)
 * Shows real-time tool calls made by the agent.
 */

const TOOL_META = {
  identify_user:          { icon: '👤', label: 'Identifying patient',       done: 'Patient identified' },
  fetch_slots:            { icon: '📅', label: 'Fetching available slots',  done: 'Slots retrieved' },
  book_appointment:       { icon: '✅', label: 'Booking appointment',       done: 'Appointment booked' },
  retrieve_appointments:  { icon: '📋', label: 'Loading appointments',      done: 'Appointments loaded' },
  cancel_appointment:     { icon: '❌', label: 'Cancelling appointment',    done: 'Appointment cancelled' },
  modify_appointment:     { icon: '🔄', label: 'Rescheduling appointment',  done: 'Appointment rescheduled' },
  end_conversation:       { icon: '👋', label: 'Ending call',               done: 'Call complete' },
}

function getResultBadge(tool, result) {
  if (!result) return null
  if (result.error) return <span className="badge badge-error">Error</span>
  if (tool === 'book_appointment' && result.status === 'booked')
    return <span className="badge badge-success">Confirmed</span>
  if (tool === 'cancel_appointment' && result.status === 'cancelled')
    return <span className="badge badge-warning">Cancelled</span>
  if (tool === 'fetch_slots')
    return <span className="badge badge-info">{result.count} slots</span>
  return <span className="badge badge-success">Done</span>
}

function ToolEventItem({ event }) {
  const meta = TOOL_META[event.tool] || { icon: '⚙️', label: event.tool, done: 'Done' }
  const isDone = event.type === 'tool_done'
  const isError = event.result?.error

  return (
    <div className={`tool-event ${isDone ? (isError ? 'error' : 'done') : 'active'}`}>
      <div className="tool-icon">{meta.icon}</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span className="tool-name">{event.tool}</span>
          {getResultBadge(event.tool, event.result)}
        </div>
        <div className="tool-desc">
          {isDone ? meta.done : meta.label + '…'}
        </div>

        {/* Show key result details */}
        {isDone && event.result && !isError && (
          <ResultDetail tool={event.tool} result={event.result} />
        )}
        {isError && (
          <div style={{ fontSize: 11, color: 'var(--error)', marginTop: 4 }}>
            {event.result.error}
          </div>
        )}
      </div>
      <div>{isDone ? '✓' : <div className="spinner" />}</div>
    </div>
  )
}

function ResultDetail({ tool, result }) {
  if (tool === 'identify_user' && result.user) {
    return (
      <div style={{ marginTop: 4, fontSize: 11, color: 'var(--text-secondary)' }}>
        {result.user.name || 'Unknown'} · {result.user.phone}
      </div>
    )
  }
  if (tool === 'book_appointment' && result.appointment) {
    const a = result.appointment
    return (
      <div style={{ marginTop: 4, fontSize: 11, color: 'var(--text-secondary)' }}>
        {a.doctor} · {a.date} · {a.time}
      </div>
    )
  }
  if (tool === 'fetch_slots') {
    return (
      <div style={{ marginTop: 4, fontSize: 11, color: 'var(--text-secondary)' }}>
        {result.count === 0 ? 'No slots found' : `${result.count} slots available`}
      </div>
    )
  }
  return null
}

export default function ToolStatus({ events }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: 'var(--sp-4) var(--sp-5)',
        borderBottom: '1px solid var(--border)',
        flexShrink: 0,
      }}>
        <h3>Agent Actions</h3>
        {events.length > 0 && (
          <span className="badge badge-dim">{events.length}</span>
        )}
      </div>

      <div style={{
        padding: 'var(--sp-4)',
        display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)',
        overflowY: 'auto', maxHeight: 280,
      }}>
        {events.length === 0 ? (
          <div className="empty-state" style={{ padding: 'var(--sp-6) var(--sp-4)' }}>
            <div className="empty-icon" style={{ fontSize: 20 }}>⚙️</div>
            <p>Tool calls will appear here in real time.</p>
          </div>
        ) : (
          [...events].reverse().map((ev, i) => (
            <ToolEventItem key={i} event={ev} />
          ))
        )}
      </div>
    </div>
  )
}
