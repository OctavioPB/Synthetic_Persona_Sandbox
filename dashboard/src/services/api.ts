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

export interface HealthResponse {
  status: string
  version: string
  timestamp: number
}

export const api = {
  health: (): Promise<HealthResponse> => request<HealthResponse>('/health'),
}
