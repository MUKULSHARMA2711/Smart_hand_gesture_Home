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

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    })
  } catch {
    throw new ApiError(`Cannot reach the backend at ${API_BASE_URL}.`, { code: 'network_error' })
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

  getGestureConfig: () => request('/gestures/config'),

  getGestureEvents: (limit = 15) => request(`/gestures/events?limit=${limit}`),

  /** Sends only the recognition result — never camera frames. */
  sendGesture: ({ gesture, intent, confidence, targetDeviceId }) =>
    request('/gestures/commands', {
      method: 'POST',
      body: JSON.stringify({ gesture, intent, confidence, target_device_id: targetDeviceId }),
    }),
}
