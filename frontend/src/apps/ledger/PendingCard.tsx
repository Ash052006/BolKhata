/**
 * Pending Entry Confirmation Card.
 * High-contrast, large-type confirmation interface allowing merchants to confirm or patch.
 */

import React from 'react'
import { PendingEntryState, ScriptMode } from './types'

interface PendingCardProps {
  pending: PendingEntryState
  scriptMode: ScriptMode
  isSubmitting: boolean
  onConfirm: () => void
  onCorrect: () => void
  onCancel: () => void
}

export const PendingCard: React.FC<PendingCardProps> = ({
  pending,
  scriptMode,
  isSubmitting,
  onConfirm,
  onCorrect,
  onCancel,
}) => {
  const isDev = scriptMode === 'devanagari'
  const { intent, action, read_back, resolution } = pending
  const amount = intent.amount || (action ? action.parameters.amount : 0)
  const isHighRisk = amount >= 5000 || intent.confidence! < 0.8 || (resolution && resolution.is_ambiguous)

  const actionLabels: Record<string, { hi: string; en: string }> = {
    add_credit_sale: { hi: 'उधार बिक्री', en: 'Credit Sale (Udhaar)' },
    payment_received: { hi: 'रुपये जमा', en: 'Payment Received (Jama)' },
    cash_sale: { hi: 'नकद बिक्री', en: 'Cash Sale (Nagad)' },
    expense: { hi: 'दुकान खर्चा', en: 'Store Expense (Kharcha)' },
    query_balance: { hi: 'हिसाब जाँच', en: 'Balance Check' },
    undo_last: { hi: 'रद्द / Undo', en: 'Compensating Undo' },
  }

  const actionLabel = actionLabels[intent.name] || { hi: intent.name, en: intent.name }

  return (
    <div
      role="region"
      aria-labelledby="pending-card-title"
      style={{
        background: '#ffffff',
        borderRadius: '1rem',
        border: isHighRisk ? '3px solid #d97706' : '3px solid #059669',
        boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
        padding: '1.25rem',
        marginBottom: '1.5rem',
      }}
    >
      {/* High Risk Banner */}
      {isHighRisk && (
        <div
          style={{
            background: '#fef3c7',
            color: '#92400e',
            padding: '0.4rem 0.8rem',
            borderRadius: '0.5rem',
            fontSize: '0.85rem',
            fontWeight: 700,
            marginBottom: '0.75rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <span>⚠️</span>
          <span>{isDev ? 'बड़ा अमाउंट या अस्पष्ट आवाज़ — कृपया ध्यान से जाँचें' : 'High amount or ambiguous voice — verify carefully'}</span>
        </div>
      )}

      {/* Header with Title and Amount */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
        <div>
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#6b7280' }}>
            {isDev ? 'नया लेन-देन पुष्टि' : 'Pending Transaction Confirmation'}
          </span>
          <h3 id="pending-card-title" style={{ fontSize: '1.4rem', fontWeight: 800, margin: '0.2rem 0', color: '#111827' }}>
            {intent.customer || (isDev ? 'ग्राहक' : 'Customer')}
          </h3>
          <span
            style={{
              display: 'inline-block',
              background: '#e0e7ff',
              color: '#3730a3',
              fontSize: '0.8rem',
              fontWeight: 700,
              padding: '0.2rem 0.6rem',
              borderRadius: '9999px',
            }}
          >
            {isDev ? actionLabel.hi : actionLabel.en}
          </span>
        </div>

        <div style={{ textAlign: 'right' }}>
          <span style={{ fontSize: '0.8rem', color: '#6b7280', display: 'block' }}>
            {isDev ? 'राशि (Amount)' : 'Amount'}
          </span>
          <span style={{ fontSize: '2rem', fontWeight: 900, color: '#059669' }}>
            ₹{amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
      </div>

      {/* Spoken Read-back Text */}
      <div
        style={{
          background: '#f0fdf4',
          borderLeft: '4px solid #059669',
          padding: '0.75rem 1rem',
          borderRadius: '0.375rem',
          margin: '1rem 0',
        }}
      >
        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#15803d', textTransform: 'uppercase' }}>
          {isDev ? 'आवाज़ पुष्टि (Spoken Read-Back):' : 'Spoken Confirmation:'}
        </span>
        <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#14532d', marginTop: '0.25rem' }}>
          {read_back}
        </div>
      </div>

      {/* Ambiguity Warning if present */}
      {resolution && resolution.is_ambiguous && (
        <div style={{ background: '#fef2f2', color: '#991b1b', padding: '0.5rem', borderRadius: '0.375rem', fontSize: '0.85rem', marginBottom: '1rem' }}>
          {isDev
            ? 'ग्राहक के नाम में संदेह है: क्या आप रमेश या सुरेश में से किसी को चुनना चाहते हैं?'
            : 'Customer ambiguity detected: Did you mean one of the existing customers?'}
        </div>
      )}

      {/* Interactive Action Buttons */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.5fr 1fr', gap: '0.5rem', marginTop: '1rem' }}>
        <button
          type="button"
          onClick={onConfirm}
          disabled={isSubmitting}
          style={{
            padding: '0.85rem 1rem',
            background: '#059669',
            color: '#ffffff',
            border: 'none',
            borderRadius: '0.5rem',
            fontSize: '1rem',
            fontWeight: 800,
            cursor: isSubmitting ? 'not-allowed' : 'pointer',
            boxShadow: '0 4px 6px -1px rgba(5, 150, 105, 0.4)',
          }}
        >
          {isDev ? '✓ हाँ, लिख लो' : '✓ Confirm & Save'}
        </button>

        <button
          type="button"
          onClick={onCorrect}
          disabled={isSubmitting}
          style={{
            padding: '0.85rem 0.5rem',
            background: '#f59e0b',
            color: '#ffffff',
            border: 'none',
            borderRadius: '0.5rem',
            fontSize: '0.95rem',
            fontWeight: 700,
            cursor: isSubmitting ? 'not-allowed' : 'pointer',
          }}
        >
          {isDev ? '✎ नहीं, बदलो' : '✎ Edit / Correct'}
        </button>

        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          style={{
            padding: '0.85rem 0.5rem',
            background: '#f3f4f6',
            color: '#4b5563',
            border: '1px solid #d1d5db',
            borderRadius: '0.5rem',
            fontSize: '0.9rem',
            fontWeight: 600,
            cursor: isSubmitting ? 'not-allowed' : 'pointer',
          }}
        >
          {isDev ? 'रद्द' : 'Cancel'}
        </button>
      </div>
    </div>
  )
}
