/** Centralized API client — all backend calls go through here. */

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api'

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, ...rest } = options
  const response = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: {
      'Content-Type': 'application/json',
      ...rest.headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${await response.text()}`)
  }

  return response.json() as Promise<T>
}

// ── Domain types ──────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string
  version: string
  timestamp: number
}

export interface SegmentSummary {
  id: string
  name: string
  description: string
  is_stale: boolean
  last_trained_at: string | null
  created_at: string
}

export interface CampaignResponse {
  id: string
  name: string
  description: string
  segment_id: string
  status: string
  created_at: string
}

export interface VariantResponse {
  id: string
  campaign_id: string
  name: string
  stimulus: Record<string, unknown>
  rank: number | null
  score: number | null
  run_id: string | null
}

export interface SimulationRunResponse {
  id: string
  segment_id: string
  status: string
  stimulus_type: string
  verbatim_response: string | null
  sentiment: string | null
  likelihood_to_convert: number | null
  conversion_score: number | null
  error_code: string | null
  error_detail: string | null
  latency_ms: number | null
  model_id: string | null
  created_at: string
  completed_at: string | null
}

// ── API surface ───────────────────────────────────────────────────────────────

export const api = {
  health: (): Promise<HealthResponse> =>
    request<HealthResponse>('/health'),

  segments: {
    list: (): Promise<SegmentSummary[]> =>
      request<SegmentSummary[]>('/segments'),
  },

  campaigns: {
    create: (body: { name: string; description: string; segment_id: string }): Promise<CampaignResponse> =>
      request<CampaignResponse>('/campaigns', { method: 'POST', body }),

    createVariant: (
      campaignId: string,
      body: { name: string; stimulus: Record<string, unknown> },
    ): Promise<VariantResponse> =>
      request<VariantResponse>(`/campaigns/${campaignId}/variants`, { method: 'POST', body }),
  },

  simulations: {
    run: (body: {
      segment_id: string
      stimulus: Record<string, unknown>
      temperature?: number
    }): Promise<SimulationRunResponse> =>
      request<SimulationRunResponse>('/simulate/run', { method: 'POST', body }),

    get: (runId: string): Promise<SimulationRunResponse> =>
      request<SimulationRunResponse>(`/simulate/runs/${runId}`),

    list: (params: { segment_id?: string; status?: string; size?: number } = {}): Promise<SimulationRunResponse[]> => {
      const qs = new URLSearchParams()
      if (params.segment_id) qs.set('segment_id', params.segment_id)
      if (params.status)     qs.set('status', params.status)
      if (params.size)       qs.set('size', String(params.size))
      const query = qs.toString()
      return request<SimulationRunResponse[]>(`/simulate/runs${query ? `?${query}` : ''}`)
    },
  },
}
