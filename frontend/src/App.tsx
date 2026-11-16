/**
 * Bolkhata — placeholder App component for Sprint S0.
 *
 * This component calls GET /api/health (proxied to the backend by Vite in dev,
 * and by Nginx in production) and displays the backend status.
 *
 * The /api prefix is always relative — internal Docker hostnames are NEVER
 * embedded in the built JavaScript bundle.
 *
 * The actual ledger UI lives in src/apps/ledger/ and will be built in S3+.
 */
import { useEffect, useState } from 'react'

type HealthStatus = 'checking' | 'ok' | 'error'

interface HealthResponse {
  status: string
  version: string
}

export default function App() {
  const [healthStatus, setHealthStatus] = useState<HealthStatus>('checking')
  const [healthData, setHealthData] = useState<HealthResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 5000)

    fetch('/api/health', { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json() as Promise<HealthResponse>
      })
      .then((data) => {
        setHealthData(data)
        setHealthStatus('ok')
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : 'Unknown error'
        setErrorMessage(message)
        setHealthStatus('error')
      })
      .finally(() => clearTimeout(timeoutId))

    return () => {
      controller.abort()
      clearTimeout(timeoutId)
    }
  }, [])

  return (
    <main style={{ fontFamily: 'sans-serif', maxWidth: 480, margin: '4rem auto', padding: '0 1rem' }}>
      <h1>Bolkhata</h1>
      <p style={{ color: '#666' }}>Voice-first ledger for Indian kirana shopkeepers</p>

      <section style={{ marginTop: '2rem', padding: '1rem', border: '1px solid #ddd', borderRadius: 8 }}>
        <h2 style={{ margin: '0 0 0.5rem' }}>Backend status</h2>
        {healthStatus === 'checking' && <p>Checking…</p>}
        {healthStatus === 'ok' && healthData && (
          <p style={{ color: 'green' }}>
            ✓ {healthData.status} — v{healthData.version}
          </p>
        )}
        {healthStatus === 'error' && (
          <p style={{ color: 'red' }}>✗ Could not reach backend: {errorMessage}</p>
        )}
      </section>

      <section style={{ marginTop: '1.5rem', padding: '1rem', background: '#f9f9f9', borderRadius: 8 }}>
        <p style={{ margin: 0, fontSize: 14, color: '#888' }}>
          Sprint S0 — Foundation. Ledger UI coming in S3.
        </p>
      </section>
    </main>
  )
}
