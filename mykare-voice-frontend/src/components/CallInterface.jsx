/**
 * CallInterface — center panel
 * Shows avatar, call status, and call controls.
 */
import { useState, useEffect, useRef } from 'react'
import { api } from '../lib/api'

export default function CallInterface({
  status,
  isMuted,
  agentSpeaking,
  localVideoTrack,
  onConnect,
  onDisconnect,
  onToggleMute,
}) {
  const [avatarUrl, setAvatarUrl] = useState(null)
  const videoRef = useRef(null)

  // Attach local video track
  useEffect(() => {
    if (localVideoTrack && videoRef.current) {
      localVideoTrack.attach(videoRef.current)
    }
    return () => {
      if (localVideoTrack && videoRef.current) {
        localVideoTrack.detach(videoRef.current)
      }
    }
  }, [localVideoTrack])

  // Try to load Tavus avatar on mount
  useEffect(() => {
    api.getAvatarSession()
      .then(data => { if (data.enabled && data.conversation_url) setAvatarUrl(data.conversation_url) })
      .catch(() => {}) // Avatar is optional
  }, [])

  const isActive = status === 'connected'
  const isConnecting = status === 'connecting'

  return (
    <div
      className="panel"
      style={{ borderRight: 'none', borderLeft: 'none', background: 'var(--bg-base)' }}
    >
      <div className="panel-header">
        <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14 }}>Mia — AI Assistant</h2>
        {isActive && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div className="waveform">
              {[...Array(5)].map((_, i) => (
                <div
                  key={i}
                  className={`waveform-bar ${agentSpeaking ? '' : 'idle'}`}
                />
              ))}
            </div>
            <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
              {agentSpeaking ? 'Speaking' : 'Listening'}
            </span>
          </div>
        )}
      </div>

      <div className="avatar-zone" style={{ position: 'relative' }}>
        {/* Avatar */}
        <div className={`avatar-frame ${agentSpeaking && isActive ? 'speaking' : ''}`}>
          {avatarUrl && isActive ? (
            <iframe
              src={avatarUrl}
              allow="microphone; camera"
              title="Mia Avatar"
            />
          ) : (
            <div className="avatar-placeholder">
              {isConnecting ? '⏳' : isActive ? '🩺' : '👩‍⚕️'}
            </div>
          )}
        </div>

        {/* User Local Video */}
        {localVideoTrack && isActive && (
          <div style={{
            position: 'absolute',
            bottom: '80px',
            right: '20px',
            width: '120px',
            height: '160px',
            borderRadius: '12px',
            overflow: 'hidden',
            border: '2px solid var(--border)',
            background: '#000',
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
          }}>
            <video 
              ref={videoRef} 
              autoPlay 
              playsInline 
              muted 
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          </div>
        )}

        {/* Status text */}
        <div style={{ textAlign: 'center' }}>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            {status === 'idle'        ? 'Click to start your appointment call'
            : status === 'connecting' ? 'Connecting to Mia…'
            : status === 'connected'  ? 'In conversation'
            : 'Call ended — summary below'}
          </p>
        </div>

        {/* Controls */}
        <div className="call-controls">
          {isActive && (
            <button
              className={`control-btn ${isMuted ? 'active' : ''}`}
              onClick={onToggleMute}
              title={isMuted ? 'Unmute' : 'Mute'}
            >
              {isMuted ? '🔇' : '🎤'}
            </button>
          )}

          {!isActive && status !== 'ended' ? (
            <button
              className="btn btn-primary"
              onClick={onConnect}
              disabled={isConnecting}
              style={{ padding: '10px 24px', fontSize: 14 }}
            >
              {isConnecting ? (
                <>
                  <span className="spinner" />
                  Connecting…
                </>
              ) : (
                '📞 Start Call'
              )}
            </button>
          ) : isActive ? (
            <button
              className="control-btn end"
              onClick={onDisconnect}
              title="End call"
            >
              📵
            </button>
          ) : (
            <button
              className="btn btn-ghost"
              onClick={() => window.location.reload()}
            >
              ↺ New Call
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
