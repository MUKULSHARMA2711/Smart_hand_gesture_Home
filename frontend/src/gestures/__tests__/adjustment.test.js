import { describe, expect, it } from 'vitest'
import { adjustmentRange, createAdjustment, previewValue } from '../adjustment'

const fan = {
  id: 'fan_living_room',
  state: { is_on: true, speed: 50 },
  supported_commands: [
    { action: 'turn_on' },
    { action: 'set_speed', value: { type: 'integer', minimum: 0, maximum: 100 } },
  ],
}
const ac = {
  id: 'ac_bedroom',
  state: { is_on: true, target_temperature_c: 24 },
  supported_commands: [{ action: 'set_temperature', value: { type: 'integer', minimum: 16, maximum: 30 } }],
}
const door = { id: 'door_main', state: { is_locked: true }, supported_commands: [{ action: 'lock' }, { action: 'unlock' }] }

describe('pinch-to-adjust preparation', () => {
  it('reads ranges from the backend and knows the direction per device', () => {
    expect(adjustmentRange(fan)).toMatchObject({ action: 'set_speed', min: 0, max: 100, direction: 1 })
    expect(adjustmentRange(ac)).toMatchObject({ action: 'set_temperature', min: 16, max: 30, direction: -1 })
    expect(adjustmentRange(door)).toBeNull() // nothing adjustable: never the lock
  })

  it('hand up speeds the fan up and cools the AC; values are clamped', () => {
    expect(previewValue(adjustmentRange(fan), 50, 0.6, 0.4)).toBe(90) // up
    expect(previewValue(adjustmentRange(fan), 50, 0.6, 0.8)).toBe(10) // down
    expect(previewValue(adjustmentRange(ac), 24, 0.6, 0.4)).toBe(18) // up → cooler
    expect(previewValue(adjustmentRange(ac), 24, 0.6, 0.0)).toBe(16) // clamped
  })

  it('previews on every frame but produces exactly one command, on release', () => {
    const adjustment = createAdjustment(fan, 0.6)
    const previews = [0.58, 0.55, 0.5, 0.45].map((y) => adjustment.update(y))

    expect(previews).toEqual([54, 60, 70, 80])
    expect(adjustment.release()).toEqual({ intent: 'ADJUST', value: 80, targetDeviceId: 'fan_living_room' })
    expect(adjustment.release()).toBeNull() // released once
  })

  it('sends nothing if the value did not change or the hand was lost', () => {
    const unchanged = createAdjustment(fan, 0.5)
    unchanged.update(0.5)
    expect(unchanged.release()).toBeNull()

    const lost = createAdjustment(ac, 0.5)
    lost.update(0.2)
    lost.cancel()
    expect(lost.release()).toBeNull()
    expect(createAdjustment(door, 0.5)).toBeNull()
  })
})
