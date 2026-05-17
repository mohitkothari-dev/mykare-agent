/**
 * AppointmentPanel — right panel (bottom section)
 * Shows the patient's appointments, updated in real time via tool events.
 */
import { format, parseISO } from 'date-fns'

function formatDate(dateStr) {
  try { return format(parseISO(dateStr), 'EEE, MMM d') }
  catch { return dateStr }
}

function formatTime(timeStr) {
  try {
    const [h, m] = timeStr.split(':')
    const d = new Date(); d.setHours(+h, +m)
    return format(d, 'h:mm a')
  } catch { return timeStr }
}

function AppointmentCard({ appt }) {
  const isBooked    = appt.status === 'booked'
  const isCancelled = appt.status === 'cancelled'

  return (
    <div className="appt-card" style={{ opacity: isCancelled ? 0.5 : 1 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div className="appt-date">
          {formatDate(appt.date)} · {formatTime(appt.time_slot)}
        </div>
        <span className={`badge ${isBooked ? 'badge-success' : isCancelled ? 'badge-error' : 'badge-dim'}`}>
          {appt.status}
        </span>
      </div>
      <div className="appt-title">Dr. {appt.doctor_name}</div>
      <div className="appt-meta">{appt.specialty}</div>
      {appt.notes && (
        <div className="appt-meta" style={{ marginTop: 4, fontStyle: 'italic' }}>
          "{appt.notes}"
        </div>
      )}
    </div>
  )
}

export default function AppointmentPanel({ appointments }) {
  const active    = appointments.filter(a => a.status === 'booked')
  const cancelled = appointments.filter(a => a.status === 'cancelled')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: 'var(--sp-4) var(--sp-5)',
        borderTop: '1px solid var(--border)',
        borderBottom: '1px solid var(--border)',
        flexShrink: 0,
      }}>
        <h3>Appointments</h3>
        {active.length > 0 && (
          <span className="badge badge-success">{active.length} booked</span>
        )}
      </div>

      <div style={{ padding: 'var(--sp-4)', display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
        {appointments.length === 0 ? (
          <div className="empty-state" style={{ padding: 'var(--sp-6) var(--sp-4)' }}>
            <div className="empty-icon" style={{ fontSize: 20 }}>📅</div>
            <p>Appointments will appear here after booking.</p>
          </div>
        ) : (
          <>
            {active.map((a, i) => <AppointmentCard key={i} appt={a} />)}
            {cancelled.length > 0 && (
              <>
                <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4, fontFamily: 'var(--font-mono)', letterSpacing: 1, textTransform: 'uppercase' }}>
                  Cancelled
                </div>
                {cancelled.map((a, i) => <AppointmentCard key={`c${i}`} appt={a} />)}
              </>
            )}
          </>
        )}
      </div>
    </div>
  )
}
