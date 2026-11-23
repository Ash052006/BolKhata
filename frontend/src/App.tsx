/**
 * BolKhata — Push-to-Talk Voice Ledger UI (Sprint S1 Vertical Slice).
 */

import { useState } from 'react'
import { usePushToTalk } from './apps/ledger/usePushToTalk'

export default function App() {
  const {
    sessionState,
    isConnected,
    transcript,
    assistantText,
    timings,
    error,
    startRecording,
    stopRecording,
    cancelRecording,
  } = usePushToTalk()

  const [showDevPanel, setShowDevPanel] = useState<boolean>(true)

  const isListening = sessionState === 'LISTENING'
  const isThinking = sessionState === 'THINKING'
  const isSpeaking = sessionState === 'SPEAKING'

  return (
    <main
      style={{
        fontFamily: 'system-ui, -apple-system, sans-serif',
        maxWidth: 520,
        margin: '2rem auto',
        padding: '0 1rem',
      }}
    >
      {/* App Header */}
      <header style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', margin: '0 0 0.5rem', color: '#111827' }}>
          BolKhata <span style={{ fontWeight: 400, color: '#4b5563' }}>(बोलखाता)</span>
        </h1>
        <p style={{ margin: 0, color: '#6b7280', fontSize: '0.95rem' }}>
          किराना दुकानदारों के लिए आवाज़ से चलने वाला खाता
        </p>
        <div style={{ marginTop: '0.5rem' }}>
          <span
            style={{
              display: 'inline-block',
              padding: '0.2rem 0.6rem',
              borderRadius: '9999px',
              fontSize: '0.75rem',
              fontWeight: 600,
              background: isConnected ? '#dcfce7' : '#fee2e2',
              color: isConnected ? '#15803d' : '#b91c1c',
            }}
          >
            {isConnected ? '● Connected' : '○ Disconnected'}
          </span>
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div
          role="alert"
          style={{
            marginBottom: '1.5rem',
            padding: '0.75rem 1rem',
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '0.5rem',
            color: '#991b1b',
            fontSize: '0.9rem',
          }}
        >
          {error}
        </div>
      )}

      {/* Push-to-Talk Interactive Area */}
      <section
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '2rem 0',
        }}
      >
        <button
          type="button"
          onMouseDown={() => startRecording()}
          onMouseUp={() => stopRecording()}
          onTouchStart={() => startRecording()}
          onTouchEnd={() => stopRecording()}
          disabled={!isConnected}
          style={{
            width: '160px',
            height: '160px',
            borderRadius: '50%',
            border: 'none',
            outline: 'none',
            cursor: isConnected ? 'pointer' : 'not-allowed',
            fontSize: '1rem',
            fontWeight: 700,
            color: '#ffffff',
            background: isListening
              ? '#dc2626'
              : isThinking
              ? '#d97706'
              : isSpeaking
              ? '#2563eb'
              : '#059669',
            boxShadow: isListening
              ? '0 0 0 12px rgba(220, 38, 38, 0.3)'
              : '0 4px 14px rgba(0, 0, 0, 0.15)',
            transition: 'all 0.2s ease',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1rem',
            textAlign: 'center',
            userSelect: 'none',
          }}
        >
          {isListening && 'सुन रहे हैं... (Release to Send)'}
          {isThinking && 'समझ रहे हैं... (Thinking)'}
          {isSpeaking && 'बोल रहे हैं... (Speaking)'}
          {!isListening && !isThinking && !isSpeaking && 'दबाकर बोलें (Hold to Talk)'}
        </button>

        {isListening && (
          <button
            type="button"
            onClick={() => cancelRecording()}
            style={{
              marginTop: '1rem',
              padding: '0.4rem 0.8rem',
              borderRadius: '0.375rem',
              border: '1px solid #d1d5db',
              background: '#f9fafb',
              color: '#4b5563',
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            रद्द करें (Cancel)
          </button>
        )}
      </section>

      {/* Live Transcript & Assistant Response Cards */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '2rem' }}>
        <div
          style={{
            padding: '1rem',
            background: '#ffffff',
            borderRadius: '0.75rem',
            border: '1px solid #e5e7eb',
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          }}
        >
          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#6b7280', marginBottom: '0.25rem' }}>
            आपने कहा (Your Voice Transcript):
          </div>
          <div style={{ fontSize: '1.1rem', color: '#111827', minHeight: '1.5rem' }}>
            {transcript || <span style={{ color: '#9ca3af', fontStyle: 'italic' }}>बोलने के लिए बटन दबाएँ...</span>}
          </div>
        </div>

        <div
          style={{
            padding: '1rem',
            background: '#f0fdf4',
            borderRadius: '0.75rem',
            border: '1px solid #bbf7d0',
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          }}
        >
          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#15803d', marginBottom: '0.25rem' }}>
            खाता पुष्टि (Assistant Read-Back):
          </div>
          <div style={{ fontSize: '1.1rem', color: '#14532d', minHeight: '1.5rem' }}>
            {assistantText || (
              <span style={{ color: '#86efac', fontStyle: 'italic' }}>पुष्टि यहाँ सुनाई और दिखाई देगी...</span>
            )}
          </div>
        </div>
      </section>

      {/* Latency Timings Readout (Developer Panel) */}
      <section
        style={{
          border: '1px solid #e5e7eb',
          borderRadius: '0.75rem',
          background: '#f9fafb',
          padding: '0.75rem 1rem',
        }}
      >
        <div
          onClick={() => setShowDevPanel((prev) => !prev)}
          style={{
            cursor: 'pointer',
            fontSize: '0.85rem',
            fontWeight: 600,
            color: '#374151',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span>टर्न लेटेंसी टेलीमेट्री (Turn Timings)</span>
          <span>{showDevPanel ? '▲' : '▼'}</span>
        </div>

        {showDevPanel && (
          <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: '#4b5563' }}>
            {timings ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <div>ASR Latency: <strong>{timings.asr_ms.toFixed(1)} ms</strong></div>
                <div>LLM Latency: <strong>{timings.llm_ms.toFixed(1)} ms</strong></div>
                <div>TTS Latency: <strong>{timings.tts_ms.toFixed(1)} ms</strong></div>
                <div>Total Turn: <strong>{timings.total_ms.toFixed(1)} ms</strong></div>
              </div>
            ) : (
              <p style={{ margin: 0, color: '#9ca3af' }}>एक टर्न पूरा होने के बाद लेटेंसी यहाँ दिखेगी।</p>
            )}
          </div>
        )}
      </section>
    </main>
  )
}
