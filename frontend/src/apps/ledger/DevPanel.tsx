/**
 * Developer Diagnostics & Per-Turn Latency Telemetry Panel.
 */

import React, { useState } from 'react'
import { TurnTimings } from './usePushToTalk'
import { ScriptMode } from './types'

interface DevPanelProps {
  timings: TurnTimings | null
  scriptMode: ScriptMode
  isOffline: boolean
}

export const DevPanel: React.FC<DevPanelProps> = ({
  timings,
  scriptMode,
  isOffline,
}) => {
  const [isOpen, setIsOpen] = useState<boolean>(false)
  const isDev = scriptMode === 'devanagari'

  return (
    <div
      style={{
        border: '1px solid #e5e7eb',
        borderRadius: '0.75rem',
        background: '#f9fafb',
        padding: '0.75rem 1rem',
        marginTop: '1.5rem',
      }}
    >
      <div
        onClick={() => setIsOpen((prev) => !prev)}
        style={{
          cursor: 'pointer',
          fontSize: '0.85rem',
          fontWeight: 700,
          color: '#374151',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          userSelect: 'none',
        }}
      >
        <span>
          ⚙️ {isDev ? 'डेवलपर पैनल और लेटेंसी टेलीमेट्री' : 'Developer Panel & Telemetry'}
        </span>
        <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>
          {isOpen ? '▲ छिपाएँ (Hide)' : '▼ देखें (Expand)'}
        </span>
      </div>

      {isOpen && (
        <div style={{ marginTop: '0.75rem', fontSize: '0.8rem', color: '#4b5563' }}>
          {/* Active Model Stack */}
          <div style={{ marginBottom: '0.75rem', padding: '0.5rem', background: '#ffffff', borderRadius: '0.375rem', border: '1px solid #e5e7eb' }}>
            <div style={{ fontWeight: 700, color: '#111827', marginBottom: '0.25rem' }}>
              सक्रिय मॉडल स्टैक (Active Runtime Stack):
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.25rem' }}>
              <div>ASR: <strong>Apple MLX-Whisper</strong></div>
              <div>LLM: <strong>{isOffline ? 'Rules-Only (Offline)' : 'Mock / Rules-First'}</strong></div>
              <div>TTS: <strong>Sine-PCM / Mock</strong></div>
              <div>Hardware: <strong>Apple Silicon M5</strong></div>
            </div>
          </div>

          {/* Per-Turn Stage Latencies */}
          <div style={{ padding: '0.5rem', background: '#ffffff', borderRadius: '0.375rem', border: '1px solid #e5e7eb' }}>
            <div style={{ fontWeight: 700, color: '#111827', marginBottom: '0.25rem' }}>
              टर्न लेटेंसी टाइमिंग्स (Per-Turn Latency Breakdown):
            </div>
            {timings ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.35rem' }}>
                <div>ASR Stage: <strong>{timings.asr_ms.toFixed(1)} ms</strong></div>
                <div>LLM Stage: <strong>{timings.llm_ms.toFixed(1)} ms</strong></div>
                <div>TTS Stage: <strong>{timings.tts_ms.toFixed(1)} ms</strong></div>
                <div>Total Turn: <strong style={{ color: '#059669' }}>{timings.total_ms.toFixed(1)} ms</strong></div>
              </div>
            ) : (
              <span style={{ color: '#9ca3af', fontStyle: 'italic' }}>
                {isDev ? 'एक वॉयस टर्न पूरा होने के बाद यहाँ लाइव आंकड़े दिखेंगे।' : 'Complete a voice turn to see live stage timings.'}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
