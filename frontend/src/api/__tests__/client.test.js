import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError, request } from '../client'

const json = (status, body) => ({ ok: status < 400, status, json: async () => body })

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('API client failure handling', () => {
  it('reports an unreachable backend as a network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const error = await api.getHomeState().catch((e) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error.code).toBe('network_error')
    expect(error.message).toMatch(/^Cannot reach the backend/)
  })

  it('times out a hung backend instead of waiting forever', async () => {
    vi.useFakeTimers()
    vi.stubGlobal(
      'fetch',
      vi.fn(
        (_url, { signal }) =>
          new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')))),
      ),
    )

    const pending = request('/home/state', { timeoutMs: 3000 }).catch((e) => e)
    await vi.advanceTimersByTimeAsync(3000)
    const error = await pending

    expect(error.code).toBe('timeout')
    expect(error.message).toBe('The backend did not respond within 3 s.')
  })

  it('gives the AI planner a longer timeout than ordinary requests', async () => {
    const fetch = vi.fn().mockResolvedValue(json(200, {}))
    vi.stubGlobal('fetch', fetch)
    vi.useFakeTimers()
    const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout')

    await api.aiCommand('hi')
    await api.getHomeState()

    const delays = setTimeoutSpy.mock.calls.map(([, ms]) => ms)
    expect(delays[0]).toBeGreaterThan(delays[1])
  })

  it('parses the backend error envelope, including AI outages', async () => {
    const envelope = {
      error: { code: 'ai_unavailable', message: 'AI service is currently unavailable.', details: { reason: 'no key' } },
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(503, envelope)))

    const error = await api.aiCommand('turn on the fan').catch((e) => e)

    expect([error.status, error.code, error.message, error.details.reason]).toEqual([
      503,
      'ai_unavailable',
      'AI service is currently unavailable.',
      'no key',
    ])
  })

  it('still produces a readable error when the body is not JSON', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 502, json: async () => JSON.parse('<html>') }))

    const error = await api.getEvents().catch((e) => e)

    expect([error.status, error.message]).toEqual([502, 'Request failed with status 502.'])
  })
})
