import { describe, expect, it } from 'vitest'
import { anomalous, prediction, reportWith } from '../../components/ml/__tests__/fixtures'
import { anomalyEventLine, buildActivityFeed } from '../../state/activityFeed'
import { homeHealth } from '../../state/homeHealth'
import {
  anomalousDeviceIds,
  describeReading,
  formatProbability,
  formatScore,
  predictedDevices,
  predictionHeadline,
  predictionReasons,
} from '../ml'

describe('probability formatting', () => {
  it.each([
    [0.9132, '91%'],
    [0.005, '1%'],
    [0, '0%'],
    [1, '100%'],
    [null, '—'],
    [Number.NaN, '—'],
  ])('%s → %s', (value, expected) => {
    expect(formatProbability(value)).toBe(expected)
  })

  it('builds a headline and reasons from the backend prediction', () => {
    expect(predictionHeadline(prediction)).toBe('91% · likely to be needed in the next 30 min')
    expect(predictionReasons(prediction)).toEqual(['Temperature 30.2 °C (typical 25.6 °C)', 'Room occupied'])
    expect(predictionReasons(null)).toEqual([])
  })
})

describe('anomaly device highlighting', () => {
  it('highlights devices the backend flagged, from recent readings or live checks', () => {
    expect([...anomalousDeviceIds(reportWith([anomalous]))]).toEqual(['fan_living_room'])
    const live = reportWith([])
    live.live[1] = { ...live.live[1], is_anomaly: true }
    expect([...anomalousDeviceIds(live)]).toEqual(['light_living_room'])
    expect(anomalousDeviceIds(reportWith([])).size).toBe(0)
    expect(anomalousDeviceIds(null).size).toBe(0)
  })

  it('badges only devices predicted ON', () => {
    expect(predictedDevices(prediction)).toEqual({ fan_living_room: 0.9132 })
    expect(predictedDevices({ ...prediction, prediction: 'OFF' })).toEqual({})
  })

  it('formats readings and scores', () => {
    expect(describeReading(anomalous)).toBe('170.0 W observed · normal 34.6–42.5 W')
    expect(formatScore(-0.1181)).toBe('-0.118')
    expect(formatScore(0.12)).toBe('+0.120')
  })
})

describe('ML in health checks and the event stream', () => {
  const home = {
    timestamp: new Date(1_000_000).toISOString(),
    environment: { temperature_c: 22 },
    energy: { total_power_w: 41, per_device_w: {} },
    devices: [{ id: 'fan_living_room', name: 'Living Room Fan', device_type: 'fan', status: 'online', power_w: 41, state: { is_on: true } }],
  }

  it('adds a real energy-anomaly check when ML results exist', () => {
    const flagged = homeHealth(home, 1_001_000, reportWith([anomalous]))
    expect(flagged.checks.find((c) => c.id === 'energy_anomalies')).toMatchObject({
      status: 'warning',
      detail: 'Living Room Fan: 170.0 W (normal 34.6–42.5 W)',
    })
    expect(homeHealth(home, 1_001_000, reportWith([])).checks.find((c) => c.id === 'energy_anomalies').status).toBe('ok')
    expect(homeHealth(home, 1_001_000).info.find((i) => i.id === 'anomalies').detail).toBe('Not available yet')
  })

  it('shows ML anomaly events in the activity stream', () => {
    const event = {
      event_id: 'e1',
      timestamp: '2026-10-06T10:01:00Z',
      device_id: 'fan_living_room',
      action: 'energy_anomaly',
      event_type: 'energy_anomaly',
      value: 170,
      source: 'ml',
      details: { score: -0.118, expected_range: { min: 34.59, max: 42.53 } },
      previous_state: {},
      new_state: {},
    }
    const [entry] = buildActivityFeed({ deviceEvents: [event], deviceNames: { fan_living_room: 'Living Room Fan' } })
    expect(entry).toMatchObject({ tag: 'ML', kind: 'ml', tone: 'error' })
    expect(entry.text).toBe(anomalyEventLine(event, { fan_living_room: 'Living Room Fan' }))
    expect(entry.text).toBe('LIVING ROOM FAN → ENERGY ANOMALY 170.0 W (normal 34.6–42.5 W)')
  })
})
