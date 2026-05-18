/**
 * useVoiceSession
 * Manages LiveKit room connection, mic state, and data channel events.
 *
 * Agent emits these topics:
 *   "tool_event"    → { type, event, tool, args/result, session_id }
 *   "transcript"    → { type, role, content, timestamp, session_id }
 *   "speaking_state"→ { type, speaking, session_id }
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { Room, RoomEvent } from 'livekit-client'
import { api } from '../lib/api'

function generateRoomName() {
  return 'mykare-' + Math.random().toString(36).slice(2, 9)
}

export function useVoiceSession({ onToolEvent, onTranscript, onSpeakingState }) {
  const [status, setStatus] = useState('idle')
  const [isMuted, setIsMuted] = useState(false)
  const [roomName, setRoomName] = useState(null)
  const [sessionId] = useState(() => crypto.randomUUID())
  const [localVideoTrack, setLocalVideoTrack] = useState(null)

  const roomRef = useRef(null)

  const connect = useCallback(async () => {
    if (roomRef.current) return
    setStatus('connecting')

    try {
      const name = generateRoomName()
      setRoomName(name)

      const { token, livekit_url } = await api.getLiveKitToken(name, 'patient')

      const room = new Room({
        audioCaptureDefaults: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
      roomRef.current = room

      room.on(RoomEvent.Connected, () => {
        setStatus('connected')
        console.log('[LiveKit] Connected to room:', name)
      })

      room.on(RoomEvent.Disconnected, () => {
        setStatus('ended')
        console.log('[LiveKit] Disconnected')
      })

      room.on(RoomEvent.LocalTrackPublished, (trackPublication) => {
        if (trackPublication.kind === 'video') {
          setLocalVideoTrack(trackPublication.track)
        }
      })
      
      room.on(RoomEvent.LocalTrackUnpublished, (trackPublication) => {
        if (trackPublication.kind === 'video') {
          setLocalVideoTrack(null)
        }
      })

      room.on(RoomEvent.DataReceived, (payload, participant, kind, topic) => {
        let event
        try {
          event = JSON.parse(new TextDecoder().decode(payload))
        } catch (e) {
          console.warn('[LiveKit] Failed to parse data event:', e)
          return
        }

        console.log('[LiveKit] Data event:', topic, event)

        switch (topic) {
          case 'tool_event':
            onToolEvent?.(event)
            break
          case 'transcript':
            onTranscript?.({ type: 'message', ...event })
            break
          case 'speaking_state':
            onSpeakingState?.(event.speaking)
            break
          default:
            // Fallback: route by event.type field if topic is generic
            if (event.type === 'tool_event')     onToolEvent?.(event)
            else if (event.type === 'transcript') onTranscript?.({ type: 'message', ...event })
            else if (event.type === 'speaking_state') onSpeakingState?.(event.speaking)
        }
      })

      room.on(RoomEvent.ConnectionQualityChanged, (quality, participant) => {
        console.log('[LiveKit] Connection quality:', quality)
      })

      await room.connect(livekit_url, token)
      await room.localParticipant.setMicrophoneEnabled(true)
      await room.localParticipant.setCameraEnabled(true)

    } catch (err) {
      console.error('[LiveKit] Connection failed:', err)
      setStatus('idle')
      roomRef.current = null
    }
  }, [onToolEvent, onTranscript, onSpeakingState])

  const disconnect = useCallback(async () => {
    await roomRef.current?.disconnect()
    roomRef.current = null
    setLocalVideoTrack(null)
    setStatus('ended')
  }, [])

  const toggleMute = useCallback(async () => {
    const room = roomRef.current
    if (!room) return
    const enabled = room.localParticipant.isMicrophoneEnabled
    await room.localParticipant.setMicrophoneEnabled(!enabled)
    setIsMuted(enabled)
  }, [])

  useEffect(() => () => { roomRef.current?.disconnect() }, [])

  return { status, isMuted, roomName, sessionId, localVideoTrack, connect, disconnect, toggleMute }
}
