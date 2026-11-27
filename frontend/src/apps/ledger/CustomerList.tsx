/**
 * Customer Balances Table / Card Component.
 * Integrates Feature F3 (Debt Ageing Badges) and Feature F4 (WhatsApp Click-to-Chat Reminders).
 */

import React, { useState } from 'react'
import { CustomerSummary, ScriptMode } from './types'

interface CustomerListProps {
  customers: CustomerSummary[]
  scriptMode: ScriptMode
  isLoading: boolean
  onSelectCustomer?: (customer: CustomerSummary) => void
}

export const CustomerList: React.FC<CustomerListProps> = ({
  customers,
  scriptMode,
  isLoading,
  onSelectCustomer,
}) => {
  const isDev = scriptMode === 'devanagari'
  const isBn = scriptMode === 'bengali'
  const [remindingCustId, setRemindingCustId] = useState<string | null>(null)
  const [reminderError, setReminderError] = useState<string | null>(null)

  const handleSendReminder = async (c: CustomerSummary, evt: React.MouseEvent) => {
    evt.stopPropagation()
    setRemindingCustId(c.id)
    setReminderError(null)

    try {
      const res = await fetch(`/api/v1/ledger/customers/${c.id}/reminder?tone=neutral`, {
        method: 'POST',
      })
      if (res.ok) {
        const data = await res.json()
        if (data.whatsapp_url) {
          window.open(data.whatsapp_url, '_blank', 'noopener,noreferrer')
        }
      } else {
        const err = await res.json()
        setReminderError(err.detail || 'Could not draft reminder')
        setTimeout(() => setReminderError(null), 3500)
      }
    } catch {
      setReminderError('Failed to generate WhatsApp link')
      setTimeout(() => setReminderError(null), 3500)
    } finally {
      setRemindingCustId(null)
    }
  }

  // Deterministic ageing bucket preview (0-7d vs 8-30d vs 31-60d vs 60+d)
  const getAgeingBadge = (balance: number, createdAt: string) => {
    if (balance <= 0) return null
    const daysOld = Math.floor((Date.now() - new Date(createdAt).getTime()) / (1000 * 60 * 60 * 24))
    if (daysOld <= 7) {
      return { text: isBn ? '০-৭ দিন' : isDev ? '०-७ दिन' : '0-7d Current', bg: '#dcfce7', color: '#166534' }
    }
    if (daysOld <= 30) {
      return { text: isBn ? '৮-৩০ দিন' : isDev ? '८-३० दिन' : '8-30d Recent', bg: '#fef3c7', color: '#92400e' }
    }
    if (daysOld <= 60) {
      return { text: isBn ? '৩১-৬০ দিন' : isDev ? '३१-६० दिन' : '31-60d Overdue', bg: '#ffedd5', color: '#9a3412' }
    }
    return { text: isBn ? '৬০+ দিন বাকি' : isDev ? '६०+ दिन बकाया' : '60+d Critical', bg: '#fee2e2', color: '#991b1b' }
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
          {isBn ? 'গ্রাহক খাতা (Customer Balances)' : isDev ? 'ग्राहक बहीखाता (Customer Balances)' : 'Customer Balances'}
        </h3>
        <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>
          {isBn ? `মোট: ${customers.length}` : isDev ? `कुल ग्राहक: ${customers.length}` : `Total: ${customers.length}`}
        </span>
      </div>

      {reminderError && (
        <div
          role="alert"
          style={{
            background: '#fef2f2',
            border: '1px solid #fecaca',
            color: '#991b1b',
            padding: '0.4rem 0.6rem',
            borderRadius: '0.375rem',
            marginBottom: '0.6rem',
            fontSize: '0.8rem',
          }}
        >
          {reminderError}
        </div>
      )}

      {isLoading ? (
        <div style={{ padding: '1rem', textAlign: 'center', color: '#9ca3af', fontSize: '0.9rem' }}>
          {isBn ? 'লোড হচ্ছে...' : isDev ? 'लोड हो रहा है...' : 'Loading balances...'}
        </div>
      ) : customers.length === 0 ? (
        <div style={{ padding: '1.5rem', textAlign: 'center', color: '#6b7280', fontSize: '0.9rem' }}>
          {isBn
            ? 'কোনো গ্রাহকের হিসাব নেই। মুখে বলে নতুন হিসাব যোগ করুন।'
            : isDev
            ? 'कोई ग्राहक खाता नहीं मिला। बोलकर नया उधार जोड़ें।'
            : 'No customer records found. Add a credit sale via voice.'}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: 380, overflowY: 'auto' }}>
          {customers.map((c) => {
            const isDue = c.balance > 0
            const ageing = getAgeingBadge(c.balance, c.created_at)

            return (
              <div
                key={c.id}
                onClick={() => onSelectCustomer && onSelectCustomer(c)}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '0.65rem 0.75rem',
                  borderRadius: '0.5rem',
                  background: isDue ? '#fffbeb' : '#f9fafb',
                  border: isDue ? '1px solid #fde68a' : '1px solid #f3f4f6',
                  cursor: onSelectCustomer ? 'pointer' : 'default',
                  transition: 'background 0.15s ease',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <div style={{ fontWeight: 700, fontSize: '1rem', color: '#1f2937' }}>
                      {c.name}
                    </div>
                    {ageing && (
                      <span
                        style={{
                          fontSize: '0.65rem',
                          fontWeight: 700,
                          padding: '0.1rem 0.4rem',
                          borderRadius: '9999px',
                          background: ageing.bg,
                          color: ageing.color,
                        }}
                      >
                        {ageing.text}
                      </span>
                    )}
                  </div>
                  {c.phone && (
                    <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.1rem' }}>
                      📞 {c.phone}
                    </div>
                  )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <div style={{ textAlign: 'right' }}>
                    <span
                      style={{
                        fontSize: '1.1rem',
                        fontWeight: 800,
                        color: isDue ? '#b45309' : '#059669',
                      }}
                    >
                      ₹{c.balance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                    <span style={{ display: 'block', fontSize: '0.7rem', color: '#6b7280' }}>
                      {isDue ? (isBn ? 'বাকি' : isDev ? 'उधार बाकी' : 'Due') : (isBn ? 'পরিশোধিত' : isDev ? 'चुक्ता' : 'Settled')}
                    </span>
                  </div>

                  {/* WhatsApp Reminder Draft Trigger (F4) */}
                  {isDue && (
                    <button
                      type="button"
                      aria-label={`Send reminder to ${c.name}`}
                      disabled={remindingCustId === c.id}
                      onClick={(evt) => handleSendReminder(c, evt)}
                      style={{
                        padding: '0.35rem 0.6rem',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        borderRadius: '0.375rem',
                        border: '1px solid #16a34a',
                        background: '#f0fdf4',
                        color: '#16a34a',
                        cursor: 'pointer',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {remindingCustId === c.id ? '...' : '💬 Remind'}
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
