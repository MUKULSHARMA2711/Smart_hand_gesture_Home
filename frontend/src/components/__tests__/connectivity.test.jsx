import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { buildActivityFeed, hardwareEventLine } from '../../state/activityFeed'
import { homeHealth } from '../../state/homeHealth'
import { connectivityLabel, deviceStatusLabel } from '../3d/visualState'
import { DeviceCard } from '../DeviceCard'

const text = (element) => renderToStaticMarkup(element).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ')

const fan = (status, state = { is_on: false, speed: 50 }) => ({
  id: 'fan_living_room',
  name: 'Living Room Fan',
  device_type: 'fan',
  room: 'living_room',
  status,
  state,
  power_w: 0.5,
  driver: 'esp32_mqtt',
  last_confirmed_at: '2026-10-06T12:00:00Z',
  supported_commands: [{ action: 'set_speed', capability: 'SET_SPEED', value: { type: 'integer', minimum: 0, maximum: 100 } }],
})

describe('hardware connectivity', () => {
  it.each([
    ['online', null],
    ['offline', 'OFFLINE'],
    ['unknown', 'UNKNOWN'],
  ])('%s → %s', (status, label) => {
    expect(connectivityLabel(fan(status))).toBe(label)
  })

  it('keeps showing the last confirmed state of an offline device, labelled offline', () => {
    const device = fan('offline', { is_on: true, speed: 70 })
    expect(deviceStatusLabel(device)).toBe('ON · 70%') // last confirmed, not guessed
    expect(connectivityLabel(device)).toBe('OFFLINE')
  })

  it('shows status and the ESP32 driver on the device card', () => {
    const html = text(<DeviceCard device={fan('unknown')} onCommand={() => {}} />)
    expect(html).toContain('Unknown')
    expect(html).toContain('ESP32')
    expect(text(<DeviceCard device={fan('offline')} onCommand={() => {}} />)).toContain('Offline')
  })

  it('counts a device that is not online in the home status', () => {
    const home = { timestamp: new Date(1_000_000).toISOString(), environment: null, energy: { total_power_w: 1 }, devices: [fan('offline')] }
    expect(homeHealth(home, 1_001_000).checks.find((c) => c.id === 'devices')).toMatchObject({ status: 'warning', detail: '0 of 1 online' })
  })
})

describe('MQTT events in the activity stream', () => {
  const names = { fan_living_room: 'Living Room Fan' }
  const base = { event_id: 'e', timestamp: '2026-10-06T12:00:00Z', device_id: 'fan_living_room', source: 'mqtt', value: null }

  it('shows availability changes as warnings when a device drops', () => {
    const event = { ...base, action: 'offline', event_type: 'availability', previous_state: {}, new_state: {}, details: { previous: 'online' } }
    const [entry] = buildActivityFeed({ deviceEvents: [event], deviceNames: names })
    expect(entry).toMatchObject({ tag: 'MQTT', tone: 'warning', text: 'LIVING ROOM FAN → OFFLINE' })
  })

  it('shows what a device reported on its own', () => {
    const event = {
      ...base,
      action: 'state_report',
      event_type: 'state_report',
      previous_state: { is_on: false, speed: 50 },
      new_state: { is_on: true, speed: 50 },
      details: { reason: 'late_acknowledgement' },
    }
    expect(hardwareEventLine(event, names)).toBe('LIVING ROOM FAN → REPORTED POWER OFF → ON')
    expect(buildActivityFeed({ deviceEvents: [event], deviceNames: names })[0].detail).toBe('late acknowledgement')
  })

  it('keeps commands attributed to who issued them, even over MQTT', () => {
    const command = {
      ...base,
      source: 'gesture',
      action: 'turn_on',
      event_type: 'device_command',
      previous_state: { is_on: false },
      new_state: { is_on: true },
      details: { transport: 'mqtt', command_id: 'x', ack_latency_ms: 42 },
    }
    expect(buildActivityFeed({ deviceEvents: [command], deviceNames: names })[0]).toMatchObject({ tag: 'GESTURE', text: 'LIVING ROOM FAN → ON' })
  })
})
