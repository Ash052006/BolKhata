/**
 * Push-to-Talk React hook managing WebSocket streaming, AudioWorklet microphone capture,
 * and flushable PCM audio playback.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

export type SessionState = 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING'

export interface TurnTimings {
  asr_ms: number
  llm_ms: number
  tts_ms: number
  total_ms: number
}

export interface PushToTalkReturn {
  sessionState: SessionState
  isConnected: boolean
  transcript: string
  assistantText: string
  timings: TurnTimings | null
  error: string | null
  startRecording: () => Promise<void>
  stopRecording: () => void
  cancelRecording: () => void
}

export function usePushToTalk(): PushToTalkReturn {
  const [sessionState, setSessionState] = useState<SessionState>('IDLE')
  const [isConnected, setIsConnected] = useState<boolean>(false)
  const [transcript, setTranscript] = useState<string>('')
  const [assistantText, setAssistantText] = useState<string>('')
  const [timings, setTimings] = useState<TurnTimings | null>(null)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const workletNodeRef = useRef<AudioWorkletNode | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const activeSourcesRef = useRef<AudioBufferSourceNode[]>([])
  const activeTurnIdRef = useRef<string | null>(null)

  // Flush any in-flight audio playback
  const flushAudioPlayback = useCallback(() => {
    activeSourcesRef.current.forEach((src) => {
      try {
        src.stop()
        src.disconnect()
      } catch {
        // Source may already have ended
      }
    })
    activeSourcesRef.current = []
  }, [])

  // Connect WebSocket
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/session`
    const ws = new WebSocket(wsUrl)
    ws.binaryType = 'arraybuffer'
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      setError(null)
    }

    ws.onclose = () => {
      setIsConnected(false)
      setSessionState('IDLE')
    }

    ws.onerror = () => {
      setError('WebSocket connection error')
    }

    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'session_state') {
            setSessionState(msg.state)
            if (msg.state === 'IDLE') {
              activeTurnIdRef.current = null
            }
          } else if (msg.type === 'transcript') {
            setTranscript(msg.text)
          } else if (msg.type === 'assistant_text') {
            setAssistantText((prev) => (msg.is_final ? prev : prev + msg.token))
          } else if (msg.type === 'audio_chunk') {
            playPCMChunk(msg.data_b64, msg.sample_rate || 16000)
          } else if (msg.type === 'timings') {
            setTimings({
              asr_ms: msg.asr_ms,
              llm_ms: msg.llm_ms,
              tts_ms: msg.tts_ms,
              total_ms: msg.total_ms,
            })
          } else if (msg.type === 'error') {
            setError(`${msg.code}: ${msg.message}`)
          }
        } catch {
          // Ignore malformed message
        }
      }
    }

    return () => {
      ws.close()
      flushAudioPlayback()
    }
  }, [flushAudioPlayback])

  // Play a base64 encoded 16-bit linear PCM audio chunk
  const playPCMChunk = useCallback(
    (base64Data: string, sampleRate: number) => {
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext ||
          (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)()
      }
      const ctx = audioContextRef.current
      if (ctx.state === 'suspended') {
        ctx.resume().catch(() => {})
      }

      const binaryStr = atob(base64Data)
      const len = binaryStr.length
      const bytes = new Uint8Array(len)
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryStr.charCodeAt(i)
      }

      const int16Array = new Int16Array(bytes.buffer)
      const numSamples = int16Array.length
      const audioBuffer = ctx.createBuffer(1, numSamples, sampleRate)
      const channelData = audioBuffer.getChannelData(0)

      for (let i = 0; i < numSamples; i++) {
        channelData[i] = int16Array[i] / 32768.0
      }

      const source = ctx.createBufferSource()
      source.buffer = audioBuffer
      source.connect(ctx.destination)
      activeSourcesRef.current.push(source)

      source.onended = () => {
        activeSourcesRef.current = activeSourcesRef.current.filter((s) => s !== source)
      }

      source.start()
    },
    []
  )

  const startRecording = useCallback(async () => {
    setError(null)
    flushAudioPlayback()
    setTranscript('')
    setAssistantText('')
    setTimings(null)

    const turnId = `turn-${Date.now()}`
    activeTurnIdRef.current = turnId

    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext ||
          (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)({
          sampleRate: 16000,
        })
      }
      const ctx = audioContextRef.current
      if (ctx.state === 'suspended') {
        await ctx.resume()
      }

      // Initialize Worklet node if not already attached
      if (!workletNodeRef.current) {
        await ctx.audioWorklet.addModule('/audio-recorder-worklet.js')
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,
            sampleRate: 16000,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        })
        mediaStreamRef.current = stream

        const sourceNode = ctx.createMediaStreamSource(stream)
        const workletNode = new AudioWorkletNode(ctx, 'pcm-recorder-processor')

        workletNode.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(event.data)
          }
        }

        sourceNode.connect(workletNode)
        workletNodeRef.current = workletNode
      }

      // Send start_utterance JSON control event
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            type: 'start_utterance',
            turn_id: turnId,
            language: 'hi',
          })
        )
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Microphone access denied'
      setError(msg)
      setSessionState('IDLE')
    }
  }, [flushAudioPlayback])

  const stopRecording = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'end_utterance',
          turn_id: activeTurnIdRef.current || `turn-${Date.now()}`,
        })
      )
    }
  }, [])

  const cancelRecording = useCallback(() => {
    flushAudioPlayback()
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'cancel_utterance',
          turn_id: activeTurnIdRef.current || `turn-${Date.now()}`,
        })
      )
    }
    setSessionState('IDLE')
  }, [flushAudioPlayback])

  return {
    sessionState,
    isConnected,
    transcript,
    assistantText,
    timings,
    error,
    startRecording,
    stopRecording,
    cancelRecording,
  }
}
