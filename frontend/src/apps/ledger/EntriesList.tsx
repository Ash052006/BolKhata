/**
 * Append-Only Ledger Events List Component.
 * Displays real-time immutable transaction feed with timestamps and compensation tags.
 */

import React from 'react'
import { LedgerEntry, ScriptMode } from './types'

interface EntriesListProps {
  entries: LedgerEntry[]
  scriptMode: ScriptMode
  isLoading: boolean
}

export const EntriesList: React.FC<EntriesListProps> = ({
  entries,
  scriptMode,
  isLoading,
}) => {
  const isDev = scriptMode === 'devanagari'

  const eventBadge = (type: string, isCompensated: boolean) => {
    if (isCompensated) {
      return { text: isDev ? 'रद्द (Undone)' : 'Compensated', bg: '#fee2e2', color: '#991b1b' }
    }
    switch (type) {
      case 'add_credit_sale':
        return { text: isDev ? 'उधार' : 'Credit', bg: '#fef3c7', color: '#92400e' }
      case 'payment_received':
        return { text: isDev ? 'जमा' : 'Payment', bg: '#dcfce7', color: '#166534' }
      case 'cash_sale':
        return { text: isDev ? 'नकद' : 'Cash', bg: '#e0e7ff', color: '#3730a3' }
      case 'expense':
        return { text: isDev ? 'खर्चा' : 'Expense', bg: '#f3e8ff', color: '#6b21a8' }
      case 'compensation_undo':
        return { text: isDev ? 'रद्द / Undo' : 'Undo', bg: '#f1f5f9', color: '#475569' }
      default:
        return { text: type, bg: '#f3f4f6', color: '#374151' }
    }
  }

  return (
    <div
      style={{
        background: '#ffffff',
        borderRadius: '0.75rem',
        border: '1px solid #e5e7eb',
        padding: '1rem',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0, color: '#111827' }}>
          {isDev ? 'हालिया लेन-देन (Recent Ledger Entries)' : 'Recent Ledger Entries'}
        </h3>
        <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>
          {isDev ? `कुल: ${entries.length}` : `Entries: ${entries.length}`}
        </span>
      </div>

      {isLoading ? (
        <div style={{ padding: '1rem', textAlign: 'center', color: '#9ca3af', fontSize: '0.9rem' }}>
          {isDev ? 'लोड हो रहा है...' : 'Loading entries...'}
        </div>
      ) : entries.length === 0 ? (
        <div style={{ padding: '1.5rem', textAlign: 'center', color: '#6b7280', fontSize: '0.9rem' }}>
          {isDev ? 'अभी तक कोई लेन-देन दर्ज नहीं हुआ।' : 'No transactions recorded yet.'}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: 280, overflowY: 'auto' }}>
          {entries.map((e) => {
            const badge = eventBadge(e.event_type, e.is_compensated)
            const dateStr = new Date(e.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            return (
              <div
                key={e.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '0.5rem 0.75rem',
                  borderRadius: '0.5rem',
                  background: e.is_compensated ? '#fafafa' : '#ffffff',
                  border: '1px solid #f3f4f6',
                  opacity: e.is_compensated ? 0.65 : 1.0,
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        padding: '0.15rem 0.5rem',
                        borderRadius: '9999px',
                        background: badge.bg,
                        color: badge.color,
                      }}
                    >
                      {badge.text}
                    </span>
                    <strong style={{ fontSize: '0.95rem', color: '#1f2937' }}>
                      {e.customer_name || (isDev ? 'दुकान' : 'Store')}
                    </strong>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '0.15rem' }}>
                    🕒 {dateStr} {e.items && e.items.length > 0 ? `• ${e.items.join(', ')}` : ''}
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <span
                    style={{
                      fontSize: '1rem',
                      fontWeight: 800,
                      color: e.is_compensated ? '#9ca3af' : '#111827',
                      textDecoration: e.is_compensated ? 'line-through' : 'none',
                    }}
                  >
                    ₹{e.amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
