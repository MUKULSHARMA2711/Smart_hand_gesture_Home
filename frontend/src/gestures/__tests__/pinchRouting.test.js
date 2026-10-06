import { describe, expect, it, vi } from 'vitest'
import { createAdjustmentController } from '../adjustment'
import { createDoorUnlockController } from '../doorUnlock'
import { routePinch } from '../pinchRouting'
import { DEFAULT_GESTURE_INTENTS } from '../types'

const flush = async () => {
  for (let i = 0; i < 5; i += 1) await Promise.resolve()
}

const door = { id: 'door_main', name: 'Main Door', device_type: 'door_lock', state: { is_locked: true }, supported_commands: [{ action: 'lock' }, { action: 'unlock' }] }
const fan = { id: 'fan_living_room', name: 'Living Room Fan', device_type: 'fan', state: { is_on: true, speed: 50 }, supported_commands: [{ action: 'set_speed', value: { minimum: 0, maximum: 100 } }] }
const ac = { id: 'ac_bedroom', name: 'Bedroom AC', device_type: 'ac', state: { is_on: true, target_temperature_c: 24 }, supported_commands: [{ action: 'set_temperature', value: { minimum: 16, maximum: 30 } }] }
const confirmation = {
  confirmation_id: 'c1',
  device_id: 'door_main',
  expires_at: new Date(Date.now() + 30_000).toISOString(),
}

/** The Gesture page's wiring: one selection, the real unlock and adjustment controllers. */
function page(selected) {
  let device = selected
  const adjustments = []
  const unlockStates = []
  const send = vi.fn() // the adjustment's one command
  const requestUnlock = vi.fn(async () => ({ confirmation, device: { name: 'Main Door' } }))
  const decide = vi.fn(async (id, decision) => ({ actions: [{ status: decision === 'confirm' ? 'executed' : 'cancelled' }] }))
  const unlock = createDoorUnlockController({
    requestUnlock,
    decide,
    isDoorSelected: () => device?.device_type === 'door_lock',
    onChange: (s) => unlockStates.push(s),
  })
  const adjuster = createAdjustmentController({ getDevice: () => device, send, onChange: (s) => adjustments.push(s) })
  const routes = []
  const pinch = (ys = [0.6, 0.5, 0.45]) => {
    const events = [{ type: 'start', y: ys[0], confidence: 0.9 }, ...ys.slice(1).map((y) => ({ type: 'move', y, confidence: 0.9 })), { type: 'end', y: ys.at(-1), confidence: 0.9 }]
    for (const event of events) routes.push(routePinch(event, { device, unlock, adjuster }))
  }
  return { pinch, unlock, adjuster, adjustments, unlockStates, send, requestUnlock, decide, routes, select: (d) => (device = d) }
}

describe('pinch routing by selected device', () => {
  it('Main Door: the first pinch requests an unlock and never enters adjustment', async () => {
    const p = page(door)
    p.pinch()
    await flush()

    expect(p.routes.every((r) => r === 'door')).toBe(true)
    expect(p.requestUnlock).toHaveBeenCalledTimes(1)
    expect(p.unlockStates.at(-1)).toMatchObject({ status: 'pending', deviceName: 'Main Door' })
    expect(p.decide).not.toHaveBeenCalled() // the first pinch never unlocks
    // Regression: the adjustment never sees the door, so "no adjustable value" cannot appear.
    expect(p.adjustments).toEqual([])
    expect(p.send).not.toHaveBeenCalled()
  })

  it('Main Door with an unlock pending: the next pinch confirms that request, once', async () => {
    const p = page(door)
    p.pinch()
    await flush()
    p.pinch()
    await flush()

    expect(p.requestUnlock).toHaveBeenCalledTimes(1) // no second request
    expect(p.decide.mock.calls).toEqual([['c1', 'confirm']])
    expect(p.unlockStates.at(-1)).toEqual({ status: 'confirmed', deviceName: 'Main Door' })
    expect(p.adjustments).toEqual([])
  })

  it('pinches while the request or the confirmation is in flight are ignored', async () => {
    const p = page(door)
    p.pinch()
    p.pinch() // the first request has not been answered yet
    await flush()
    expect(p.requestUnlock).toHaveBeenCalledTimes(1)
    expect(p.decide).not.toHaveBeenCalled()

    p.pinch() // confirm
    p.pinch() // while the confirmation is in flight
    await flush()
    expect(p.decide.mock.calls).toEqual([['c1', 'confirm']])
    expect(p.adjustments).toEqual([])
  })

  it('Fan: a pinch adjusts the speed exactly as before', () => {
    const p = page(fan)
    p.pinch([0.6, 0.5, 0.45])
    expect(p.routes.every((r) => r === 'adjust')).toBe(true)
    expect(p.send).toHaveBeenCalledTimes(1)
    expect(p.send.mock.calls[0][0]).toMatchObject({ intent: 'ADJUST', value: 80, targetDeviceId: 'fan_living_room' })
    expect(p.requestUnlock).not.toHaveBeenCalled()
  })

  it('AC: a pinch adjusts the temperature exactly as before', () => {
    const p = page(ac)
    p.pinch([0.6, 0.5, 0.4]) // hand up = cooler
    expect(p.send).toHaveBeenCalledTimes(1)
    expect(p.send.mock.calls[0][0]).toMatchObject({ intent: 'ADJUST', value: 18, targetDeviceId: 'ac_bedroom' })
    expect(p.requestUnlock).not.toHaveBeenCalled()
  })

  it('open palm still cancels the pending door unlock', async () => {
    const p = page(door)
    p.pinch()
    await flush()
    expect(p.unlock.gesture('OPEN_PALM')).toBe(true) // consumed: no STOP sent to the door
    await flush()
    expect(p.decide.mock.calls).toEqual([['c1', 'cancel']])
    expect(p.unlockStates.at(-1).status).toBe('cancelled')

    p.select(fan) // after cancelling, fan pinches adjust again
    p.pinch()
    expect(p.send).toHaveBeenCalledTimes(1)
  })

  it('OPEN_PALM → STOP is unchanged for the fan (no pending unlock: not consumed)', () => {
    const p = page(fan)
    expect(p.unlock.gesture('OPEN_PALM')).toBe(false) // runs as the normal STOP gesture
    expect(DEFAULT_GESTURE_INTENTS.OPEN_PALM).toBe('STOP')
  })
})
