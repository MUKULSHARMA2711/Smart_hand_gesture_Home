export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, { status = 0, code = 'unknown_error', details = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

// A hung backend must surface as an error, not an endless spinner. The AI planner may
// legitimately take longer (an LLM with tool calls); the backend caps it at 120 s.
export const REQUEST_TIMEOUT_MS = 15_000
export const AI_REQUEST_TIMEOUT_MS = 130_000

export async function request(path, { timeoutMs = REQUEST_TIMEOUT_MS, ...options } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    })
  } catch {
    if (controller.signal.aborted) {
      throw new ApiError(`The backend did not respond within ${Math.round(timeoutMs / 1000)} s.`, { code: 'timeout' })
    }
    throw new ApiError(`Cannot reach the backend at ${API_BASE_URL}.`, { code: 'network_error' })
  } finally {
    clearTimeout(timer)
  }

  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const error = body?.error
    throw new ApiError(error?.message ?? `Request failed with status ${response.status}.`, {
      status: response.status,
      code: error?.code,
      details: error?.details,
    })
  }
  return body
}

export const api = {
  getHomeState: () => request('/home/state'),

  getEvents: (limit = 20) => request(`/events?limit=${limit}`),

  sendCommand: (deviceId, action, value) => {
    const body = { action, source: 'frontend' }
    if (value !== undefined) body.value = value
    return request(`/devices/${encodeURIComponent(deviceId)}/command`, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  aiCommand: (message) =>
    request('/ai/command', { method: 'POST', body: JSON.stringify({ message }), timeoutMs: AI_REQUEST_TIMEOUT_MS }),

  /** Answer a held security-sensitive action (door unlock): 'confirm' or 'cancel'. */
  decideConfirmation: (confirmationId, decision) =>
    request(`/ai/confirmations/${encodeURIComponent(confirmationId)}`, {
      method: 'POST',
      body: JSON.stringify({ decision }),
      timeoutMs: AI_REQUEST_TIMEOUT_MS,
    }),

  getAIStatus: () => request('/ai/status'),

  getAIHistory: (limit = 20) => request(`/ai/history?limit=${limit}`),

  getMLStatus: () => request('/ml/status'),

  predict: (body = {}) => request('/ml/predict', { method: 'POST', body: JSON.stringify(body) }),

  getAnomalies: () => request('/ml/anomalies'),

  /** Assess one power reading, as a hardware power meter would report it. */
  checkPowerReading: (deviceId, powerW) =>
    request('/ml/anomalies/check', { method: 'POST', body: JSON.stringify({ device_id: deviceId, power_w: powerW }) }),

  getGestureConfig: () => request('/gestures/config'),

  getGestureEvents: (limit = 15) => request(`/gestures/events?limit=${limit}`),

  /** Sends only the recognition result — never camera frames. */
  sendGesture: ({ gesture, intent, confidence, targetDeviceId, value }) =>
    request('/gestures/commands', {
      method: 'POST',
      body: JSON.stringify({ gesture, intent, confidence, target_device_id: targetDeviceId, ...(value === undefined ? {} : { value }) }),
    }),
}
