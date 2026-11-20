import { useEffect, useState } from 'react'
import { getAuthToken } from '../services/api'

export interface SimulationProgress {
  status: 'pending' | 'running' | 'completed' | 'failed' | 'error'
  conversionScore: number | null
  verbatimResponse: string | null
  sentiment: string | null
  latencyMs: number | null
  errorDetail: string | null
}

export const TERMINAL_STATUSES = new Set(['completed', 'failed', 'error'])

const INITIAL: SimulationProgress = {
  status: 'pending',
  conversionScore: null,
  verbatimResponse: null,
  sentiment: null,
  latencyMs: null,
  errorDetail: null,
}

/** Shape of one frame from /ws/simulations/{run_id}. */
interface ProgressFrame {
  status?: SimulationProgress['status']
  conversion_score?: number | null
  verbatim_response?: string | null
  sentiment?: string | null
  latency_ms?: number | null
  error_detail?: string | null
  /** Set instead of `status` when the server cannot serve the run. */
  error?: string
}

function buildSocketUrl(runId: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const url = new URL(`${proto}://${window.location.host}/ws/simulations/${encodeURIComponent(runId)}`)
  // Browsers cannot set headers on a WebSocket handshake, so the JWT travels
  // as a query parameter (the API ignores it when auth is disabled).
  const token = getAuthToken()
  if (token) url.searchParams.set('token', token)
  return url.toString()
}

export function useSimulationProgress(runId: string | null): SimulationProgress {
  const [progress, setProgress] = useState<SimulationProgress>(INITIAL)

  useEffect(() => {
    if (!runId) return
    setProgress(INITIAL)

    let settled = false
    const fail = (detail: string): void => {
      if (settled) return
      settled = true
      setProgress((p) => ({ ...p, status: 'error', errorDetail: detail }))
    }

    const ws = new WebSocket(buildSocketUrl(runId))

    ws.onmessage = (event) => {
      let frame: ProgressFrame
      try {
        frame = JSON.parse(event.data as string) as ProgressFrame
      } catch {
        return // malformed frame — ignore
      }

      // Error frames ({error: "not_found" | "internal_error"}) carry no status;
      // without this branch the card would spin on "pending" forever.
      if (frame.error) {
        fail(frame.error)
        return
      }

      const status = frame.status ?? 'pending'
      if (TERMINAL_STATUSES.has(status)) settled = true
      setProgress({
        status,
        conversionScore: frame.conversion_score ?? null,
        verbatimResponse: frame.verbatim_response ?? null,
        sentiment: frame.sentiment ?? null,
        latencyMs: frame.latency_ms ?? null,
        errorDetail: frame.error_detail ?? null,
      })
    }

    ws.onerror = () => fail('connection_error')
    // The server closes the socket after the terminal frame. A close before
    // that (rejected handshake, dropped connection) must surface as an error.
    ws.onclose = () => fail('connection_closed')

    return () => {
      settled = true
      ws.close()
    }
  }, [runId])

  return progress
}
