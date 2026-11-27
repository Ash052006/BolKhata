/**
 * BolKhata Kirana Voice Ledger — Complete PWA Application View.
 * Implements Sprint S5 UI: Accessible Push-to-Talk, Confirmation Cards, Balances, Offline Fallback, and Telemetry.
 */

import React, { useCallback, useEffect, useState } from 'react'
import { usePushToTalk } from './usePushToTalk'
import { ActionPayload, CustomerSummary, LedgerEntry, PendingEntryState, ScriptMode } from './types'
import { ConsentModal } from './ConsentModal'
import { PendingCard } from './PendingCard'
import { CustomerList } from './CustomerList'
import { EntriesList } from './EntriesList'
import { DevPanel } from './DevPanel'

export const LedgerApp: React.FC = () => {
  const {
    sessionState,
    isConnected,
    transcript,
    assistantText,
    timings,
    error: pttError,
    startRecording,
    stopRecording,
    cancelRecording,
  } = usePushToTalk()

  // Display & accessibility preferences
  const [scriptMode, setScriptMode] = useState<ScriptMode>('devanagari')
  const [activeTab, setActiveTab] = useState<'customers' | 'entries'>('customers')

  // Data states
  const [customers, setCustomers] = useState<CustomerSummary[]>([])
  const [entries, setEntries] = useState<LedgerEntry[]>([])
  const [pendingEntry, setPendingEntry] = useState<PendingEntryState | null>(null)
  const [isLoadingData, setIsLoadingData] = useState<boolean>(false)
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)
  const [appError, setAppError] = useState<string | null>(null)

  // Consent modal state
  const [hasMicConsent, setHasMicConsent] = useState<boolean>(() => {
    return localStorage.getItem('bolkhata_mic_consent') === 'true'
  })
  const [showConsentModal, setShowConsentModal] = useState<boolean>(false)

  // Offline detection
  const isOffline = !isConnected

  // Fetch ledger data from backend
  const refreshLedgerData = useCallback(async () => {
    setIsLoadingData(true)
    try {
      const [custRes, entryRes] = await Promise.all([
        fetch('/api/v1/ledger/customers'),
        fetch('/api/v1/ledger/entries?limit=50'),
      ])
      if (custRes.ok && entryRes.ok) {
        const custData = await custRes.json()
        const entryData = await entryRes.json()
        setCustomers(custData)
        setEntries(entryData)
        setAppError(null)
      }
    } catch {
      // In offline mode, keep existing cached data
    } finally {
      setIsLoadingData(false)
    }
  }, [])

  useEffect(() => {
    refreshLedgerData()
  }, [refreshLedgerData])

  // Handle Voice Utterance completion -> parse into PendingEntry
  useEffect(() => {
    if (transcript && sessionState === 'IDLE') {
      const parseUtterance = async () => {
        try {
          const res = await fetch('/api/v1/ledger/utterance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: transcript }),
          })
          if (res.ok) {
            const data = await res.json()
            if (data.action && data.intent.name !== 'query_balance' && data.intent.name !== 'undo_last') {
              setPendingEntry({
                intent: data.intent,
                action: data.action,
                resolution: data.resolution,
                read_back: data.read_back,
                raw_text: transcript,
              })
            } else if (data.intent.name === 'undo_last' && data.action) {
              // Execute undo automatically on explicit verbal undo request
              await handleConfirmEntryDirect(data.action)
            }
          }
        } catch {
          // If offline, fallback to typed input notification
        }
      }
      parseUtterance()
    }
  }, [transcript, sessionState])

  // Direct confirmation of an action
  const handleConfirmEntryDirect = async (action: ActionPayload) => {
    setIsSubmitting(true)
    try {
      const payload = {
        action_type: action.action_type,
        amount: action.parameters.amount,
        customer_id: action.parameters.customer_id,
        items: action.parameters.items || [],
        date: action.parameters.date || 'aaj',
        notes: action.parameters.notes || 'Voice confirmed',
        idempotency_key: action.idempotency_key,
      }
      const res = await fetch('/api/v1/ledger/entries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (res.ok) {
        setPendingEntry(null)
        await refreshLedgerData()
      } else {
        const err = await res.json()
        setAppError(err.detail || 'Failed to save entry')
      }
    } catch {
      setAppError('Network error: Could not commit entry.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleConfirmPending = async () => {
    if (!pendingEntry || !pendingEntry.action) return
    await handleConfirmEntryDirect(pendingEntry.action)
  }

  const handleCorrectPending = () => {
    // Prompt merchant to speak correction
    setAppError(
      scriptMode === 'devanagari'
        ? 'सुधारने के लिए बोलें (उदा: "नहीं 300 नहीं, 350" या "वर्मा जी हैं")'
        : 'Speak correction (e.g., "nahi 300 nahi 350" or "Verma ji hai")'
    )
  }

  const handleCancelPending = () => {
    setPendingEntry(null)
  }

  // Push-to-Talk activation guard (checks privacy consent first)
  const handleStartPushToTalk = async () => {
    if (!hasMicConsent) {
      setShowConsentModal(true)
      return
    }
    await startRecording()
  }

  const handleConsentAccept = async () => {
    setHasMicConsent(true)
    localStorage.setItem('bolkhata_mic_consent', 'true')
    setShowConsentModal(false)
    await startRecording()
  }

  const handleConsentDecline = () => {
    setShowConsentModal(false)
  }

  const isDev = scriptMode === 'devanagari'
  const isListening = sessionState === 'LISTENING'
  const isThinking = sessionState === 'THINKING'
  const isSpeaking = sessionState === 'SPEAKING'

  return (
    <main
      style={{
        fontFamily: 'system-ui, -apple-system, sans-serif',
        maxWidth: 580,
        margin: '1rem auto 3rem',
        padding: '0 1rem',
        color: '#111827',
      }}
    >
      {/* Offline Mode Banner */}
      {isOffline && (
        <div
          role="status"
          style={{
            background: '#fee2e2',
            border: '2px solid #ef4444',
            borderRadius: '0.75rem',
            padding: '0.6rem 1rem',
            color: '#991b1b',
            fontWeight: 700,
            fontSize: '0.9rem',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <span>⚡</span>
          <span>
            {isDev
              ? 'ऑफ़लाइन मोड (Offline Mode) — सर्वर से संपर्क टूटा है। स्क्रीन पर डेटा सुरक्षित है।'
              : 'Offline Mode — Server disconnected. Local session preserved.'}
          </span>
        </div>
      )}

      {/* App Header */}
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '2px solid #e5e7eb',
          paddingBottom: '0.75rem',
          marginBottom: '1.25rem',
        }}
      >
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 900, margin: 0, color: '#059669' }}>
            BolKhata{' '}
            <span style={{ fontSize: '1.25rem', fontWeight: 600, color: '#4b5563' }}>
              {scriptMode === 'bengali' ? '(বোলখাতা)' : '(बोलखाता)'}
            </span>
          </h1>
          <p style={{ margin: '0.15rem 0 0', fontSize: '0.85rem', color: '#6b7280' }}>
            {scriptMode === 'bengali'
              ? 'মুদি দোকানদারদের জন্য কণ্ঠস্বর-চালিত খাতা'
              : isDev
              ? 'किराना दुकानदारों के लिए आवाज़ से चलने वाला बहीखाता'
              : 'Voice-First Kirana Ledger'}
          </p>
        </div>

        {/* Script & Sync Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span
            style={{
              fontSize: '0.75rem',
              fontWeight: 700,
              padding: '0.25rem 0.5rem',
              borderRadius: '9999px',
              background: isOffline ? '#fee2e2' : '#dcfce7',
              color: isOffline ? '#991b1b' : '#166534',
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
            }}
          >
            <span>{isOffline ? '⚡' : '🟢'}</span>
            <span>{isOffline ? 'Offline' : 'Synced'}</span>
          </span>

          <button
            type="button"
            onClick={() =>
              setScriptMode((prev) => {
                if (prev === 'devanagari') return 'bengali'
                if (prev === 'bengali') return 'roman'
                return 'devanagari'
              })
            }
            style={{
              padding: '0.4rem 0.75rem',
              borderRadius: '0.5rem',
              border: '2px solid #059669',
              background: '#f0fdf4',
              color: '#059669',
              fontWeight: 800,
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            {scriptMode === 'devanagari'
              ? 'अ Devanagari'
              : scriptMode === 'bengali'
              ? 'বা বাংলা'
              : 'A Roman'}
          </button>
        </div>
      </header>

      {/* Error Notices */}
      {(pttError || appError) && (
        <div
          role="alert"
          style={{
            background: '#fef2f2',
            border: '1px solid #fecaca',
            color: '#991b1b',
            padding: '0.6rem 0.85rem',
            borderRadius: '0.5rem',
            marginBottom: '1rem',
            fontSize: '0.85rem',
          }}
        >
          {pttError || appError}
        </div>
      )}

      {/* Push-to-Talk Core Button Area */}
      <section
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          margin: '1.5rem 0 2rem',
        }}
      >
        <button
          type="button"
          aria-label={isDev ? 'आवाज़ से बोलने के लिए दबाकर रखें' : 'Hold to speak voice transaction'}
          onMouseDown={handleStartPushToTalk}
          onMouseUp={stopRecording}
          onTouchStart={handleStartPushToTalk}
          onTouchEnd={stopRecording}
          style={{
            width: 175,
            height: 175,
            borderRadius: '50%',
            border: 'none',
            outline: 'none',
            cursor: 'pointer',
            fontSize: '1.05rem',
            fontWeight: 800,
            color: '#ffffff',
            background: isListening
              ? '#dc2626'
              : isThinking
              ? '#d97706'
              : isSpeaking
              ? '#2563eb'
              : '#059669',
            boxShadow: isListening
              ? '0 0 0 16px rgba(220, 38, 38, 0.35)'
              : '0 8px 24px rgba(5, 150, 105, 0.3)',
            transition: 'all 0.15s ease',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1.25rem',
            textAlign: 'center',
            userSelect: 'none',
          }}
        >
          <span style={{ fontSize: '2.2rem', marginBottom: '0.35rem' }}>
            {isListening ? '🎙️' : isThinking ? '⏳' : isSpeaking ? '🔊' : '🎤'}
          </span>
          {isListening && (isDev ? 'सुन रहे हैं...' : 'Listening...')}
          {isThinking && (isDev ? 'समझ रहे हैं...' : 'Processing...')}
          {isSpeaking && (isDev ? 'बोल रहे हैं...' : 'Speaking...')}
          {!isListening && !isThinking && !isSpeaking && (isDev ? 'दबाकर बोलें' : 'Hold to Talk')}
        </button>

        {isListening && (
          <button
            type="button"
            onClick={cancelRecording}
            style={{
              marginTop: '0.75rem',
              padding: '0.35rem 0.85rem',
              background: '#f3f4f6',
              border: '1px solid #d1d5db',
              borderRadius: '0.375rem',
              color: '#4b5563',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {isDev ? 'रद्द करें (Cancel)' : 'Cancel'}
          </button>
        )}
      </section>

      {/* Pending Entry Card (shown when uncommitted entry exists) */}
      {pendingEntry && (
        <PendingCard
          pending={pendingEntry}
          scriptMode={scriptMode}
          isSubmitting={isSubmitting}
          onConfirm={handleConfirmPending}
          onCorrect={handleCorrectPending}
          onCancel={handleCancelPending}
        />
      )}

      {/* Live Transcript & Read-back Display Cards */}
      <section style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <div
          style={{
            background: '#ffffff',
            border: '1px solid #e5e7eb',
            borderRadius: '0.75rem',
            padding: '0.75rem 1rem',
            boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
          }}
        >
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#6b7280', textTransform: 'uppercase' }}>
            {isDev ? 'आपने कहा (Transcript):' : 'Spoken Voice:'}
          </span>
          <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#111827', marginTop: '0.2rem', minHeight: '1.8rem' }}>
            {transcript || <span style={{ color: '#9ca3af', fontStyle: 'italic' }}>{isDev ? 'बोलें...' : 'Speak...'}</span>}
          </div>
        </div>

        <div
          style={{
            background: '#f0fdf4',
            border: '1px solid #bbf7d0',
            borderRadius: '0.75rem',
            padding: '0.75rem 1rem',
            boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
          }}
        >
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#15803d', textTransform: 'uppercase' }}>
            {isDev ? 'असिस्टेंट उत्तर (Read-Back):' : 'Assistant Read-Back:'}
          </span>
          <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#14532d', marginTop: '0.2rem', minHeight: '1.8rem' }}>
            {assistantText || <span style={{ color: '#86efac', fontStyle: 'italic' }}>{isDev ? 'पुष्टि यहाँ दिखेगी' : 'Confirmation here'}</span>}
          </div>
        </div>
      </section>

      {/* Navigation Tabs (Customers vs Recent Entries) */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <button
          type="button"
          onClick={() => setActiveTab('customers')}
          style={{
            flex: 1,
            padding: '0.6rem',
            borderRadius: '0.5rem',
            border: 'none',
            background: activeTab === 'customers' ? '#059669' : '#f3f4f6',
            color: activeTab === 'customers' ? '#ffffff' : '#4b5563',
            fontWeight: 700,
            fontSize: '0.95rem',
            cursor: 'pointer',
          }}
        >
          👥 {isDev ? 'ग्राहक बहीखाता' : 'Customer Balances'}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('entries')}
          style={{
            flex: 1,
            padding: '0.6rem',
            borderRadius: '0.5rem',
            border: 'none',
            background: activeTab === 'entries' ? '#059669' : '#f3f4f6',
            color: activeTab === 'entries' ? '#ffffff' : '#4b5563',
            fontWeight: 700,
            fontSize: '0.95rem',
            cursor: 'pointer',
          }}
        >
          📜 {isDev ? 'हालिया हिसाब' : 'Recent Entries'}
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === 'customers' ? (
        <CustomerList
          customers={customers}
          scriptMode={scriptMode}
          isLoading={isLoadingData}
        />
      ) : (
        <EntriesList
          entries={entries}
          scriptMode={scriptMode}
          isLoading={isLoadingData}
        />
      )}

      {/* Developer Telemetry Diagnostics Panel */}
      <DevPanel
        timings={timings}
        scriptMode={scriptMode}
        isOffline={isOffline}
      />

      {/* Privacy Consent Modal */}
      <ConsentModal
        isOpen={showConsentModal}
        scriptMode={scriptMode}
        onAccept={handleConsentAccept}
        onDecline={handleConsentDecline}
      />
    </main>
  )
}
