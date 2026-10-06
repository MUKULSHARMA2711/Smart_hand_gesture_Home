import { describe, expect, it } from 'vitest'
import { buildActivityFeed, deviceEventLine } from '../activityFeed'
import {
  executionDuration,
  IDLE,
  lifecycleReducer,
  orbState,
  resultPhase,
  visualizedActions,
} from '../aiLifecycle'
import { appendSample, summarize } from '../energyHistory'
import { homeHealth } from '../homeHealth'

const response = (actions, extra = {}) => ({ plan_valid: true, errors: [], actions, ...extra })
const run = (events, start = IDLE) => events.reduce(lifecycleReducer, start)

describe('AI lifecycle', () => {
  it('moves through listening → thinking → planning → executing → success', () => {
    const r = response([{ device_id: 'light', status: 'executed' }])
    let state = run([{ type: 'focus' }])
    expect(state.phase).toBe('listening')
    state = run([{ type: 'send', request: 'turn on the light' }], state)
    expect(state.phase).toBe('thinking')
    state = run([{ type: 'response', response: r }], state)
    expect(state.phase).toBe('planning')
    state = run([{ type: 'execute' }], state)
    expect(state.phase).toBe('executing')
    state = run([{ type: 'complete' }], state)
    expect(state.phase).toBe('success')
    expect(run([{ type: 'reset' }], state)).toEqual(IDLE)
  })

  it('skips executing for query-only responses', () => {
    const state = run([
      { type: 'send', request: 'energy?' },
      { type: 'response', response: response([{ device_id: null, intent: 'GET_ENERGY', status: 'answered' }]) },
      { type: 'execute' },
    ])
    expect(state.phase).toBe('success')
  })

  it.each([
    [response([{ device_id: 'door', status: 'rejected' }]), 'error'],
    [response([{ device_id: 'fan', status: 'executed' }, { device_id: 'door', status: 'rejected' }]), 'success'],
    [response([{ device_id: 'fan', status: 'failed' }]), 'error'],
    [response([], { plan_valid: false, errors: ['provider down'] }), 'error'],
    [response([]), 'success'],
  ])('derives the result phase from real results (%#)', (r, phase) => {
    expect(resultPhase(r)).toBe(phase)
  })

  it('reports transport errors and ignores out-of-order events', () => {
    expect(run([{ type: 'send', request: 'x' }, { type: 'transport_error', message: 'offline' }]).phase).toBe('error')
    expect(run([{ type: 'complete' }])).toEqual(IDLE)
    expect(run([{ type: 'response', response: response([]) }])).toEqual(IDLE)
    expect(run([{ type: 'focus' }, { type: 'blur' }])).toEqual(IDLE)
  })

  it('animates only device-targeting results and sizes the execution phase from them', () => {
    const r = response([
      { device_id: 'light', status: 'executed' },
      { device_id: null, status: 'answered' },
      { device_id: 'door', status: 'rejected' },
    ])
    expect(visualizedActions(r).map((a) => a.device_id)).toEqual(['light', 'door'])
    expect(executionDuration(r)).toBeGreaterThan(executionDuration(response([{ device_id: 'light', status: 'executed' }])))
    expect(executionDuration(response([]))).toBe(0)
  })

  it('shows "listening" for an active gesture camera only when the assistant is idle', () => {
    expect(orbState('idle', { gestureActive: true })).toBe('listening')
    expect(orbState('thinking', { gestureActive: true })).toBe('thinking')
    expect(orbState('idle')).toBe('idle')
  })
})

const home = (overrides = {}) => ({
  timestamp: new Date(1_000_000).toISOString(),
  environment: { temperature_c: 22 },
  energy: { total_power_w: 100, energy_kwh: 0.01, per_device_w: { ac: 90, light: 10 } },
  devices: [
    { id: 'light', name: 'Light', device_type: 'light', status: 'online', power_w: 10, state: { is_on: true } },
    { id: 'ac', name: 'AC', device_type: 'ac', status: 'online', power_w: 90, state: { is_on: true } },
    { id: 'door', name: 'Main Door', device_type: 'door_lock', status: 'online', power_w: 0, state: { is_locked: true } },
  ],
  ...overrides,
})

describe('homeHealth', () => {
  it('passes every check for a healthy, locked home with fresh sensors', () => {
    const health = homeHealth(home(), 1_005_000)
    expect(health.passed).toBe(3)
    expect(health.total).toBe(3)
    expect(health.info.find((i) => i.id === 'anomalies').detail).toBe('Not available yet')
    expect(health.info.find((i) => i.id === 'energy').detail).toContain('AC 90%')
  })

  it('flags an unlocked door, offline devices and stale sensors', () => {
    const h = home()
    h.devices[2] = { ...h.devices[2], state: { is_locked: false } }
    h.devices[0] = { ...h.devices[0], status: 'offline' }
    const health = homeHealth(h, 1_000_000 + 60_000)
    expect(Object.fromEntries(health.checks.map((c) => [c.id, c.status]))).toEqual({
      devices: 'warning',
      security: 'warning',
      sensors: 'warning',
    })
    expect(health.checks.find((c) => c.id === 'security').detail).toBe('Main Door unlocked')
  })

  it('returns no checks without data', () => {
    expect(homeHealth(null)).toEqual({ checks: [], info: [], passed: 0, total: 0 })
  })
})

describe('energy history', () => {
  it('appends real samples in time order, ignores duplicates and caps the length', () => {
    let history = []
    for (let i = 1; i <= 5; i++) history = appendSample(history, home({ timestamp: new Date(i * 5000).toISOString() }), 3)
    history = appendSample(history, home({ timestamp: new Date(25000).toISOString() }), 3)
    expect(history.map((s) => s.t)).toEqual([15000, 20000, 25000])
    expect(summarize(history)).toMatchObject({ current: 100, peak: 100, samples: 3, spanMs: 10000 })
    expect(summarize([])).toBeNull()
  })
})

describe('activity feed', () => {
  it('merges device, gesture and AI activity newest first, without inventing entries', () => {
    const feed = buildActivityFeed({
      deviceEvents: [
        { event_id: 'd1', timestamp: '2026-10-04T10:00:02Z', device_id: 'light', action: 'turn_on', value: null, source: 'gesture' },
      ],
      gestureEvents: [
        { event_id: 'g1', timestamp: '2026-10-04T10:00:01Z', gesture: 'THUMBS_UP', confidence: 0.97, intent: 'TURN_ON', success: true, action: 'turn_on' },
      ],
      aiInteractions: [
        { interaction_id: 'a1', timestamp: '2026-10-04T10:00:03Z', request: 'turn off the fan', outcome: '1 executed.', any_rejected: false, plan_valid: true },
      ],
      deviceNames: { light: 'Living Room Light' },
    })
    expect(feed.map((e) => [e.tag, e.text])).toEqual([
      ['AI AGENT', '“turn off the fan”'],
      ['GESTURE', 'LIVING ROOM LIGHT → ON'],
      ['GESTURE', 'THUMBS_UP 97% → TURN_ON'],
    ])
  })

  it.each([
    [{ device_id: 'fan', action: 'set_speed', value: 70 }, 'FAN → SPEED 70%'],
    [{ device_id: 'door', action: 'unlock', value: null }, 'DOOR → UNLOCKED'],
    [{ device_id: 'ac', action: 'set_temperature', value: 22 }, 'AC → TARGET 22 °C'],
  ])('describes device events (%#)', (event, line) => {
    expect(deviceEventLine(event)).toBe(line)
  })
})
