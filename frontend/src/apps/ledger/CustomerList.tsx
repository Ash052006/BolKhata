/**
 * Customer Balances Table / Card Component.
 */

import React from 'react'
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
          {isDev ? 'ग्राहक बहीखाता (Customer Balances)' : 'Customer Balances'}
        </h3>
        <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>
          {isDev ? `कुल ग्राहक: ${customers.length}` : `Total: ${customers.length}`}
        </span>
      </div>

      {isLoading ? (
        <div style={{ padding: '1rem', textAlign: 'center', color: '#9ca3af', fontSize: '0.9rem' }}>
          {isDev ? 'लोड हो रहा है...' : 'Loading balances...'}
        </div>
      ) : customers.length === 0 ? (
        <div style={{ padding: '1.5rem', textAlign: 'center', color: '#6b7280', fontSize: '0.9rem' }}>
          {isDev ? 'कोई ग्राहक खाता नहीं मिला। बोलकर नया उधार जोड़ें।' : 'No customer records found. Add a credit sale via voice.'}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: 280, overflowY: 'auto' }}>
          {customers.map((c) => {
            const isDue = c.balance > 0
            return (
              <div
                key={c.id}
                onClick={() => onSelectCustomer && onSelectCustomer(c)}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '0.6rem 0.75rem',
                  borderRadius: '0.5rem',
                  background: isDue ? '#fffbeb' : '#f9fafb',
                  border: isDue ? '1px solid #fde68a' : '1px solid #f3f4f6',
                  cursor: onSelectCustomer ? 'pointer' : 'default',
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, fontSize: '1rem', color: '#1f2937' }}>
                    {c.name}
                  </div>
                  {c.phone && (
                    <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                      📞 {c.phone}
                    </div>
                  )}
                </div>

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
                    {isDue ? (isDev ? 'उधार बाकी' : 'Due') : (isDev ? 'चुक्ता' : 'Settled')}
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
