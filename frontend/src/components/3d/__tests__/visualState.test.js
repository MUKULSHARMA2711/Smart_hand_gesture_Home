import { describe, expect, it } from 'vitest'
import {
  acVisual,
  approach,
  DOOR_AJAR_ANGLE,
  deviceStatusLabel,
  deviceVisual,
  doorVisual,
  FAN_MAX_RAD_PER_S,
  FAN_MIN_RAD_PER_S,
  fanVisual,
  LIGHT_MIN_LEVEL,
  lightVisual,
  ORB_STATES,
  orbAppearance,
} from '../visualState'

describe('lightVisual', () => {
  it('is dark when the backend says the light is off', () => {
    expect(lightVisual({ is_on: false, brightness: 100 })).toMatchObject({ on: false, level: 0, pointIntensity: 0 })
  })

  it('maps brightness 0-100 monotonically to light intensity', () => {
    const levels = [1, 20, 50, 70, 100].map((brightness) => lightVisual({ is_on: true, brightness }).level)
    expect(levels).toEqual([...levels].sort((a, b) => a - b))
    expect(lightVisual({ is_on: true, brightness: 100 }).level).toBe(1)
    expect(lightVisual({ is_on: true, brightness: 20 }).level).toBeCloseTo(LIGHT_MIN_LEVEL + (1 - LIGHT_MIN_LEVEL) * 0.2)
  })

  it('treats brightness 0 as off and clamps out-of-range values', () => {
    expect(lightVisual({ is_on: true, brightness: 0 }).on).toBe(false)
    expect(lightVisual({ is_on: true, brightness: 250 }).level).toBe(1)
  })
})

describe('fanVisual', () => {
  it('stops the blades when off', () => {
    expect(fanVisual({ is_on: false, speed: 80 })).toMatchObject({ on: false, angularVelocity: 0, multiplier: 0 })
  })

  it('maps speed to a rotation multiplier and angular velocity', () => {
    expect(fanVisual({ is_on: true, speed: 20 }).multiplier).toBe(0.2)
    expect(fanVisual({ is_on: true, speed: 50 }).multiplier).toBe(0.5)
    expect(fanVisual({ is_on: true, speed: 100 }).angularVelocity).toBe(FAN_MAX_RAD_PER_S)
    const slow = fanVisual({ is_on: true, speed: 20 }).angularVelocity
    const medium = fanVisual({ is_on: true, speed: 50 }).angularVelocity
    expect(FAN_MIN_RAD_PER_S < slow && slow < medium && medium < FAN_MAX_RAD_PER_S).toBe(true)
  })
})

describe('acVisual', () => {
  it('shows no airflow when off but keeps the real set point', () => {
    expect(acVisual({ is_on: false, target_temperature_c: 22 })).toMatchObject({ on: false, airflow: 0, temperature: 22 })
  })

  it('blows harder for colder set points', () => {
    expect(acVisual({ is_on: true, target_temperature_c: 16 }).airflow).toBeGreaterThan(
      acVisual({ is_on: true, target_temperature_c: 28 }).airflow,
    )
  })
})

describe('doorVisual', () => {
  it('is closed with a secure indicator when locked', () => {
    expect(doorVisual({ is_locked: true })).toEqual({ locked: true, angle: 0, indicator: 'secure', label: 'LOCKED' })
  })

  it('is ajar with a warning indicator when unlocked', () => {
    expect(doorVisual({ is_locked: false })).toEqual({
      locked: false,
      angle: DOOR_AJAR_ANGLE,
      indicator: 'warning',
      label: 'UNLOCKED',
    })
  })
})

describe('device dispatch and labels', () => {
  it.each([
    [{ device_type: 'light', state: { is_on: true, brightness: 70 } }, 'ON · 70%'],
    [{ device_type: 'fan', state: { is_on: true, speed: 50 } }, 'ON · 50%'],
    [{ device_type: 'ac', state: { is_on: false, target_temperature_c: 24 } }, 'OFF · 24 °C'],
    [{ device_type: 'door_lock', state: { is_locked: true } }, 'LOCKED'],
  ])('labels %o', (device, label) => {
    expect(deviceStatusLabel(device)).toBe(label)
    expect(deviceVisual(device)).not.toBeNull()
  })

  it('returns null for unknown device types', () => {
    expect(deviceVisual({ device_type: 'toaster', state: {} })).toBeNull()
  })
})

describe('approach', () => {
  it('moves toward the target without overshooting, independent of frame rate', () => {
    const oneStep = approach(0, 10, 2, 0.1)
    const twoSteps = approach(approach(0, 10, 2, 0.05), 10, 2, 0.05)
    expect(oneStep).toBeGreaterThan(0)
    expect(oneStep).toBeLessThan(10)
    expect(twoSteps).toBeCloseTo(oneStep)
  })
})

describe('orbAppearance', () => {
  it('defines every AI core state, with success green and error red', () => {
    for (const state of ORB_STATES) expect(orbAppearance(state)).toBeDefined()
    expect(orbAppearance('success').color).toBe('#34d399')
    expect(orbAppearance('error').color).toBe('#f87171')
    expect(orbAppearance('thinking').particles).toBe(true)
    expect(orbAppearance('idle').particles).toBe(false)
    expect(orbAppearance('unknown')).toEqual(orbAppearance('idle'))
  })
})
