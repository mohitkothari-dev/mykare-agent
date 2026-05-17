/**
 * Transcript — left panel
 * Shows the live conversation between patient and Mia.
 */
import { useEffect, useRef } from 'react'
import { format } from 'date-fns'

export default function Transcript({ messages }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="panel">
      <div className="panel-header">
        <h3>Transcript</h3>
        <span className="badge badge-dim">{messages.length}</span>
      </div>

      <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
        {messages.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">💬</div>
            <p>Conversation will appear here once the call starts.</p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`msg msg-${msg.role}`}>
              <div className="msg-bubble">{msg.content}</div>
              <div className="msg-meta">
                {msg.role === 'agent' ? 'Mia' : 'You'} ·{' '}
                {format(new Date(msg.timestamp * 1000), 'HH:mm:ss')}
              </div>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
