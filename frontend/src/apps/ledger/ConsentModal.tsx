/**
 * Microphone Consent Modal & Plain-Language Privacy Notice.
 * Explains DPDP Act compliance and local edge audio handling before mic capture.
 */

import React from 'react'
import { ScriptMode } from './types'

interface ConsentModalProps {
  isOpen: boolean
  scriptMode: ScriptMode
  onAccept: () => void
  onDecline: () => void
}

export const ConsentModal: React.FC<ConsentModalProps> = ({
  isOpen,
  scriptMode,
  onAccept,
  onDecline,
}) => {
  if (!isOpen) return null

  const isDev = scriptMode === 'devanagari'

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="consent-title"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1rem',
      }}
    >
      <div
        style={{
          background: '#ffffff',
          borderRadius: '1rem',
          maxWidth: 480,
          width: '100%',
          padding: '1.5rem',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
          border: '2px solid #059669',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
          <span style={{ fontSize: '1.8rem' }}>🔒</span>
          <h2
            id="consent-title"
            style={{
              fontSize: '1.25rem',
              fontWeight: 700,
              color: '#111827',
              margin: 0,
            }}
          >
            {isDev ? 'निजता और माइक्रोफ़ोन अनुमति' : 'Microphone Permission & Privacy'}
          </h2>
        </div>

        <div style={{ fontSize: '0.95rem', color: '#374151', lineHeight: '1.5', marginBottom: '1.25rem' }}>
          {isDev ? (
            <>
              <p style={{ margin: '0 0 0.75rem' }}>
                <strong>बोलखाता आपकी निजता का पूरा सम्मान करता है:</strong>
              </p>
              <ul style={{ paddingLeft: '1.25rem', margin: '0 0 0.75rem' }}>
                <li>आपकी आवाज़ केवल लेन-देन और हिसाब समझने के लिए इस्तेमाल होती है।</li>
                <li><strong>कच्चा ऑडियो (Raw Audio) कहीं भी स्थायी रूप से स्टोर नहीं किया जाता।</strong></li>
                <li>नाम, मोबाइल नंबर और खाते का हिसाब स्थानीय स्तर पर सुरक्षित रहता है।</li>
              </ul>
              <p style={{ margin: 0, fontSize: '0.85rem', color: '#6b7280' }}>
                क्या आप बातचीत शुरू करने के लिए माइक्रोफ़ोन चालू करना चाहते हैं?
              </p>
            </>
          ) : (
            <>
              <p style={{ margin: '0 0 0.75rem' }}>
                <strong>BolKhata strictly protects your privacy:</strong>
              </p>
              <ul style={{ paddingLeft: '1.25rem', margin: '0 0 0.75rem' }}>
                <li>Your voice is processed solely to extract ledger entries.</li>
                <li><strong>Raw audio is never permanently stored or shared with external parties.</strong></li>
                <li>Customer names, phone numbers, and balances remain secure.</li>
              </ul>
              <p style={{ margin: 0, fontSize: '0.85rem', color: '#6b7280' }}>
                Do you allow BolKhata to activate the microphone for push-to-talk voice recording?
              </p>
            </>
          )}
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
          <button
            type="button"
            onClick={onDecline}
            style={{
              padding: '0.6rem 1.2rem',
              borderRadius: '0.5rem',
              border: '1px solid #d1d5db',
              background: '#f9fafb',
              color: '#4b5563',
              fontSize: '0.95rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {isDev ? 'रद्द करें (Cancel)' : 'Cancel'}
          </button>
          <button
            type="button"
            onClick={onAccept}
            style={{
              padding: '0.6rem 1.4rem',
              borderRadius: '0.5rem',
              border: 'none',
              background: '#059669',
              color: '#ffffff',
              fontSize: '0.95rem',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: '0 2px 4px rgba(5, 150, 105, 0.3)',
            }}
          >
            {isDev ? 'मंजूर है (I Agree)' : 'I Agree & Enable Mic'}
          </button>
        </div>
      </div>
    </div>
  )
}
