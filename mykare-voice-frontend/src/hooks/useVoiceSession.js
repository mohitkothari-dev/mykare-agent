/**
 * useVoiceSession
 * Manages LiveKit room connection, mic state, and data channel events.
 * Tool events come through the room's data channel (topic: "tool_event").
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { Room, RoomEvent, DataPacket_Kind } from 'livekit-client'
import { api } from '../lib/api'

const ROOM_PREFIX = 'mykare-'

function generateRoomName() {
  return ROOM_PREFIX + Math.random().toString(36).slice(2, 9)
}

export function useVoiceSession({ onToolEvent, onTranscript }) {
  const [status, setStatus] = useState('idle')     // idle | connecting | connected | ended
  const [isMuted, setIsMuted] = useState(false)
  const [roomName, setRoomName] = useState(null)
  const [sessionId] = useState(() => crypto.randomUUID())

  const roomRef = useRef(null)

  // ── Connect ──────────────────────────────────────────────
  const connect = useCallback(async () => {
    if (roomRef.current) return
    setStatus('connecting')

    try {
      const name = generateRoomName()
      setRoomName(name)

      const { token, livekit_url } = await api.getLiveKitToken(name, 'patient')

      const room = new Room({
        audioCaptureDefaults: { echoCancellation: true, noiseSuppression: true },
      })
      roomRef.current = room

      // ── Room Events ─────────────────────────────────────
      room.on(RoomEvent.Connected, () => setStatus('connected'))
      room.on(RoomEvent.Disconnected, () => setStatus('ended'))

      // Data channel → tool events from the agent
      room.on(RoomEvent.DataReceived, (payload, participant, kind, topic) => {
        if (topic !== 'tool_event') return
        try {
          const event = JSON.parse(new TextDecoder().decode(payload))
          onToolEvent?.(event)
        } catch (e) {
          console.warn('Failed to parse tool event', e)
        }
      })

      // Track subscriptions → detect agent speaking (for avatar sync)
      room.on(RoomEvent.TrackSubscribed, (track, pub, participant) => {
        if (track.kind === 'audio' && participant.isAgent) {
          track.on('audioPlaybackStarted', () => onTranscript?.({ role: 'agent', speaking: true }))
          track.on('audioPlaybackStopped', () => onTranscript?.({ role: 'agent', speaking: false }))
        }
      })

      await room.connect(livekit_url, token)
      await room.localParticipant.setMicrophoneEnabled(true)

    } catch (err) {
      console.error('Connection failed', err)
      setStatus('idle')
      roomRef.current = null
    }
  }, [onToolEvent, onTranscript])

  // ── Disconnect ────────────────────────────────────────────
  const disconnect = useCallback(async () => {
    await roomRef.current?.disconnect()
    roomRef.current = null
    setStatus('ended')
  }, [])

  // ── Mute toggle ───────────────────────────────────────────
  const toggleMute = useCallback(async () => {
    const room = roomRef.current
    if (!room) return
    const enabled = room.localParticipant.isMicrophoneEnabled
    await room.localParticipant.setMicrophoneEnabled(!enabled)
    setIsMuted(enabled)
  }, [])

  // Cleanup on unmount
  useEffect(() => () => { roomRef.current?.disconnect() }, [])

  return { status, isMuted, roomName, sessionId, connect, disconnect, toggleMute }
}
