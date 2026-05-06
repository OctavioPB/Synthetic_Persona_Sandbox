import { useEffect, useRef, useState } from 'react'

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

export function useSimulationProgress(runId: string | null): SimulationProgress {
  const [progress, setProgress] = useState<SimulationProgress>(INITIAL)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!runId) return
    setProgress(INITIAL)

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/simulations/${runId}`)
    wsRef.current = ws

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string) as Record<string, unknown>
        setProgress({
          status: (data['status'] as SimulationProgress['status']) ?? 'pending',
          conversionScore: (data['conversion_score'] as number | null) ?? null,
          verbatimResponse: (data['verbatim_response'] as string | null) ?? null,
          sentiment: (data['sentiment'] as string | null) ?? null,
          latencyMs: (data['latency_ms'] as number | null) ?? null,
          errorDetail: (data['error_detail'] as string | null) ?? null,
        })
      } catch {
        // malformed frame — ignore
      }
    }

    ws.onerror = () => setProgress((p) => ({ ...p, status: 'error' }))

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [runId])

  return progress
}
