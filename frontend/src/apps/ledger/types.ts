/**
 * Types and interfaces for the BolKhata Kirana Ledger PWA.
 */

export type ScriptMode = 'devanagari' | 'roman'
export type LanguageMode = 'hi' | 'en' | 'hinglish'

export interface CustomerSummary {
  id: string
  name: string
  phone: string | null
  balance: number
  created_at: string
}

export interface LedgerEntry {
  id: string
  event_type: string
  amount: number
  currency: string
  customer_id: string | null
  customer_name: string | null
  items: string[] | null
  quantity: number | null
  unit: string | null
  date_str: string
  notes: string | null
  idempotency_key: string
  is_compensated: boolean
  created_at: string
}

export interface ActionPayload {
  action_type: string
  parameters: {
    customer_id?: string | null
    amount: number
    items?: string[]
    date?: string
    notes?: string
  }
  requires_confirmation: boolean
  idempotency_key: string
}

export interface PendingEntryState {
  intent: {
    name: string
    customer: string | null
    amount: number | null
    currency?: string
    items?: string[]
    quantity?: number | null
    unit?: string | null
    date?: string
    payment_mode?: string
    confidence?: number
    provenance?: Record<string, string>
  }
  action: ActionPayload | null
  resolution: {
    resolved_id: string | null
    resolved_name: string | null
    is_resolved: boolean
    is_ambiguous: boolean
    is_new: boolean
    candidates: Array<{ id: string; name: string; score: number }>
  } | null
  read_back: string
  raw_text: string
}
