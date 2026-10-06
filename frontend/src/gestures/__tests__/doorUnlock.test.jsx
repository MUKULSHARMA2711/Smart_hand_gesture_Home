import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import { DoorUnlockPanel } from '../../components/gestures/DoorUnlockPanel'
import { createAdjustmentController } from '../adjustment'
import { createDoorUnlockController } from '../doorUnlock'
import { classifyHand } from '../ruleClassifier'
import { DEFAULT_GESTURE_INTENTS, GESTURES } from '../types'
import { makeHand, POSES } from './syntheticHand'

const text = (element) => renderToStaticMarkup(element).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ')
const flush = async () => {
  for (let i = 0; i < 5; i += 1) await Promise.resolve()
}

const T0 = Date.parse('2026-10-07T12:00:00Z')
const confirmation = {
  confirmation_id: 'c1',
  device_id: 'door_main',
  intent: 'UNLOCK_DOOR',
  source: 'gesture',
  prompt: 'Unlock the Main Door? Pinch again to confirm, open palm to cancel.',
  created_at: new Date(T0).toISOString(),
  expires_at: new Date(T0 + 30_000).toISOString(),
}
const pinchStart = { type: 'start', y: 0.5, confidence: 0.9 }

function controller({ door = true, confirmResponse, confirmError, requestError } = {}) {
  let clock = T0
  const requestUnlock = vi.fn(async () => {
    if (requestError) throw requestError
    return { confirmation, device: { name: 'Main Door' } }
  })
  const decide = vi.fn(async (id, decision) => {
    if (decision === 'confirm' && confirmError) throw confirmError
    return confirmResponse ?? { actions: [{ intent: 'UNLOCK_DOOR', status: decision === 'confirm' ? 'executed' : 'cancelled' }] }
  })
  const states = []
  const unlock = createDoorUnlockController({
    requestUnlock,
    decide,
    isDoorSelected: () => door,
    onChange: (s) => states.push(s),
    now: () => clock,
  })
  return { unlock, requestUnlock, decide, states, advance: (ms) => (clock += ms) }
}

/** One full pinch (start, a few moves, release), as the pinch detector reports it. */
function pinch(unlock) {
  for (const type of ['start', 'move', 'move', 'end']) unlock.pinch({ type, y: 0.5, confidence: 0.9 })
}

describe('OPEN_PALM is unchanged', () => {
  it('a normal open palm is still OPEN_PALM → STOP', () => {
    for (const rotation of [{}, { roll: 35 }, { yaw: 45 }]) {
      expect(classifyHand(makeHand(POSES.openPalm, rotation)).gesture).toBe('OPEN_PALM')
    }
    expect(DEFAULT_GESTURE_INTENTS.OPEN_PALM).toBe('STOP')
    expect(GESTURES.FOUR_FINGERS).toBeUndefined() // the four-finger gesture is gone
    expect(classifyHand(makeHand(POSES.openPalm)).confidence).toBe(1)
  })
})

describe('double-pinch secure unlock', () => {
  it('the first pinch on the Main Door only requests an unlock', async () => {
    const { unlock, requestUnlock, decide, states } = controller()
    pinch(unlock)
    await flush()

    expect(requestUnlock).toHaveBeenCalledTimes(1)
    expect(requestUnlock).toHaveBeenCalledWith(0.9)
    expect(decide).not.toHaveBeenCalled() // nothing confirmed, nothing unlocked
    expect(states.at(-1)).toMatchObject({ status: 'pending', deviceName: 'Main Door' })
  })

  it('the second pinch confirms exactly once; more pinches cannot execute again', async () => {
    const { unlock, requestUnlock, decide, states } = controller()
    pinch(unlock)
    await flush()

    unlock.pinch(pinchStart)
    expect(states.at(-1).status).toBe('confirming') // not "unlocked" before the backend says so
    pinch(unlock) // more pinches while the confirmation is in flight are ignored
    pinch(unlock)
    await flush()

    expect(decide.mock.calls.filter(([, d]) => d === 'confirm')).toEqual([['c1', 'confirm']])
    expect(states.at(-1)).toEqual({ status: 'confirmed', deviceName: 'Main Door' })
    expect(requestUnlock).toHaveBeenCalledTimes(1) // and they started no new request
  })

  it('a quick second pinch while the first is still being answered is ignored', async () => {
    const { unlock, requestUnlock, decide } = controller()
    unlock.pinch(pinchStart)
    unlock.pinch(pinchStart) // before the backend replied
    await flush()
    expect(requestUnlock).toHaveBeenCalledTimes(1)
    expect(decide).not.toHaveBeenCalled()
  })

  it('reports a backend refusal instead of pretending the door unlocked', async () => {
    const { unlock, states } = controller({ confirmResponse: { actions: [{ status: 'rejected', reason: 'Unlocking is disabled.' }] } })
    pinch(unlock)
    await flush()
    unlock.pinch(pinchStart)
    await flush()
    expect(states.at(-1)).toMatchObject({ status: 'failed', message: 'Unlocking is disabled.' })
  })

  it('a blocked first pinch (e.g. AI unlock disabled) shows failed and creates nothing', async () => {
    const { unlock, decide, states } = controller({ requestError: Object.assign(new Error('Action not allowed'), { code: 'action_blocked' }) })
    pinch(unlock)
    await flush()
    expect(states.at(-1)).toMatchObject({ status: 'failed', message: 'Action not allowed' })
    expect(unlock.pending).toBe(false)
    expect(decide).not.toHaveBeenCalled()
  })

  it.each([
    ['fan', 'set_speed', { minimum: 0, maximum: 100 }, { speed: 50 }, 70],
    ['AC', 'set_temperature', { minimum: 16, maximum: 30 }, { target_temperature_c: 24 }, 22],
  ])('a pinch with the %s selected still adjusts (and never touches the door)', (_, action, value, state, expected) => {
    const { unlock, requestUnlock } = controller({ door: false })
    const send = vi.fn()
    const device = { id: 'x', name: 'X', state, supported_commands: [{ action, value }] }
    const adjuster = createAdjustmentController({ getDevice: () => device, send })
    const y = action === 'set_speed' ? 0.5 : 0.53 // fan: hand up = faster; AC: hand up = cooler
    for (const event of [{ type: 'start', y: 0.6 }, { type: 'move', y }, { type: 'end', y, confidence: 0.9 }]) {
      if (!unlock.pinch(event)) adjuster.handle(event)
    }
    expect(requestUnlock).not.toHaveBeenCalled()
    expect(send).toHaveBeenCalledTimes(1)
    expect(send.mock.calls[0][0]).toMatchObject({ intent: 'ADJUST', value: expected })
  })

  it('OPEN_PALM cancels (no STOP is sent) and never unlocks', async () => {
    const { unlock, decide, states } = controller()
    pinch(unlock)
    await flush()
    expect(unlock.gesture('OPEN_PALM')).toBe(true)
    await flush()
    expect(decide.mock.calls).toEqual([['c1', 'cancel']])
    expect(states.at(-1).status).toBe('cancelled')
  })

  it.each(['THUMBS_UP', 'FIST', 'ONE_FINGER', 'TWO_FINGERS'])('another gesture (%s) cancels, then runs normally', async (gesture) => {
    const { unlock, decide } = controller()
    pinch(unlock)
    await flush()
    expect(unlock.gesture(gesture)).toBe(false)
    await flush()
    expect(decide.mock.calls).toEqual([['c1', 'cancel']])
  })

  it('hand loss, camera stop or leaving the page cancels', async () => {
    const { unlock, decide, states } = controller()
    pinch(unlock)
    await flush()
    unlock.cancel('Cancelled: hand out of view.')
    await flush()
    expect(decide.mock.calls).toEqual([['c1', 'cancel']])
    expect(states.at(-1)).toMatchObject({ status: 'cancelled', message: 'Cancelled: hand out of view.' })
  })

  it('expiry cancels: a late second pinch cannot confirm', async () => {
    const { unlock, decide, states, advance } = controller()
    pinch(unlock)
    await flush()
    advance(31_000)
    unlock.tick()
    expect(states.at(-1).status).toBe('expired')
    unlock.pinch(pinchStart)
    await flush()
    expect(decide).not.toHaveBeenCalledWith('c1', 'confirm')
  })

  it('a backend "expired" answer is shown as expired', async () => {
    const { unlock, states } = controller({ confirmError: Object.assign(new Error('The confirmation expired'), { code: 'confirmation_expired' }) })
    pinch(unlock)
    await flush()
    unlock.pinch(pinchStart)
    await flush()
    expect(states.at(-1).status).toBe('expired')
  })
})

describe('door unlock panel', () => {
  it('asks for a second pinch, offers cancel, and shows the time left', () => {
    const html = text(
      <DoorUnlockPanel
        doorUnlock={{ status: 'pending', deviceName: 'Main Door', confirmation: { ...confirmation, expires_at: new Date(Date.now() + 25_000).toISOString() } }}
      />,
    )
    expect(html).toContain('Unlock Main Door?')
    expect(html).toContain('Pinch again to confirm')
    expect(html).toContain('Open palm to cancel')
    expect(html).toMatch(/Waiting for confirmation · 2[45] s/)
    expect(html).toContain('The door stays locked until the backend confirms the unlock.')
  })

  it.each([
    ['requesting', 'Requesting unlock confirmation'],
    ['confirmed', '✓ Unlocked: confirmed by the door'],
    ['cancelled', 'Cancelled · the door stays locked'],
    ['failed', '✗ Not unlocked'],
    ['expired', 'Expired · the door stays locked'],
  ])('%s', (status, label) => {
    expect(text(<DoorUnlockPanel doorUnlock={{ status, deviceName: 'Main Door' }} />)).toContain(label)
  })
})
