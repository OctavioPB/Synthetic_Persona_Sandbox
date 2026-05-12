/** Centralized API client — all backend calls go through here. */

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api'

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
}

function _getAuthHeaders(): Record<string, string> {
  try {
    const raw = localStorage.getItem('spb_auth_token')
    if (raw) return { Authorization: `Bearer ${raw}` }
  } catch { /* ignore */ }
  return {}
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, ...rest } = options
  const response = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: {
      'Content-Type': 'application/json',
      ..._getAuthHeaders(),
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

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface ApiKeyResponse {
  id: string
  name: string
  key_prefix: string
  role: string
  expires_at: string | null
  created_at: string
  is_active: boolean
  raw_key?: string
}

export interface OrgResponse {
  id: string
  name: string
  slug: string
  plan: string
}

export interface MemberResponse {
  user_id: string
  email: string
  role: string
  joined_at: string
}

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
  stimulus: Record<string, unknown>
  verbatim_response: string | null
  sentiment: string | null
  likelihood_to_convert: number | null
  conversion_score: number | null
  llm_metadata: Record<string, unknown>
  model_id: string | null
  created_at: string
  completed_at: string | null
}

export interface AdminStats {
  segments:          number
  campaigns:         number
  campaign_variants: number
  simulation_runs:   number
}

export interface SeedResult {
  segments:          number
  campaigns:         number
  campaign_variants: number
  simulation_runs:   number
  message:           string
}

export interface ClearResult {
  deleted_segments:  number
  deleted_campaigns: number
  deleted_runs:      number
  message:           string
}

// ── API surface ───────────────────────────────────────────────────────────────

export const api = {
  health: (): Promise<HealthResponse> =>
    request<HealthResponse>('/health'),

  segments: {
    list: (): Promise<SegmentSummary[]> =>
      request<{ items: SegmentSummary[] }>('/segments?size=100').then((r) => r.items),
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
      return request<{ items: SimulationRunResponse[] }>(`/simulate/runs${query ? `?${query}` : ''}`).then((r) => r.items)
    },
  },

  auth: {
    devToken: (body: { email?: string; role?: string }): Promise<TokenResponse> =>
      request<TokenResponse>('/auth/dev-token', { method: 'POST', body }),

    createKey: (body: { name: string; role?: string; expires_days?: number }): Promise<ApiKeyResponse> =>
      request<ApiKeyResponse>('/auth/keys', { method: 'POST', body }),

    listKeys: (): Promise<{ items: ApiKeyResponse[]; total: number }> =>
      request<{ items: ApiKeyResponse[]; total: number }>('/auth/keys'),

    revokeKey: (keyId: string): Promise<void> =>
      request<void>(`/auth/keys/${keyId}`, { method: 'DELETE' }),
  },

  org: {
    get: (): Promise<OrgResponse> =>
      request<OrgResponse>('/org'),

    listMembers: (): Promise<{ items: MemberResponse[]; total: number }> =>
      request<{ items: MemberResponse[]; total: number }>('/org/members'),

    inviteMember: (body: { email: string; role?: string }): Promise<{ detail: string }> =>
      request<{ detail: string }>('/org/members', { method: 'POST', body }),

    removeMember: (userId: string): Promise<void> =>
      request<void>(`/org/members/${userId}`, { method: 'DELETE' }),
  },

  admin: {
    stats: (): Promise<AdminStats> =>
      request<AdminStats>('/admin/stats'),

    seed: (params: { n_segments?: number; n_campaigns?: number; n_runs?: number }): Promise<SeedResult> => {
      const qs = new URLSearchParams()
      if (params.n_segments  != null) qs.set('n_segments',  String(params.n_segments))
      if (params.n_campaigns != null) qs.set('n_campaigns', String(params.n_campaigns))
      if (params.n_runs      != null) qs.set('n_runs',      String(params.n_runs))
      return request<SeedResult>(`/admin/seed?${qs.toString()}`, { method: 'POST' })
    },

    clear: (): Promise<ClearResult> =>
      request<ClearResult>('/admin/clear', { method: 'DELETE' }),
  },
}
