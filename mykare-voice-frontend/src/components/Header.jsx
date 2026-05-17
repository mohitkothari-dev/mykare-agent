export default function Header({ status, sessionId }) {
  return (
    <header className="app-header">
      <div className="logo">
        <div className="logo-mark">M</div>
        <div>
          Mykare
          <div className="logo-sub">Health AI</div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-4)' }}>
        <div className="status-bar">
          <span
            className={`dot ${
              status === 'connected' ? 'dot-active'
              : status === 'connecting' ? 'dot-warning'
              : status === 'ended'    ? 'dot-idle'
              : 'dot-idle'
            }`}
          />
          <span>
            {status === 'idle'       ? 'Ready'
            : status === 'connecting' ? 'Connecting…'
            : status === 'connected'  ? 'Live'
            : 'Call ended'}
          </span>
        </div>

        {sessionId && (
          <span className="mono" style={{ fontSize: 10, color: 'var(--text-dim)' }}>
            {sessionId.slice(0, 8)}
          </span>
        )}
      </div>
    </header>
  )
}
