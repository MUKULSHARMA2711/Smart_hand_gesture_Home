import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import { DoorUnlockPanel } from '../../components/gestures/DoorUnlockPanel'
import { createAdjustmentController } from '../adjustment'
import { createDoorUnlockController } from '../doorUnlock'
import { classifyHand } from '../ruleClassifier'
import { DEFAULT_CONFIDENCE_THRESHOLD } from '../types'
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
  prompt: 'Unlock the Main Door? Pinch to confirm, open palm to cancel.',
  created_at: new Date(T0).toISOString(),
  expires_at: new Date(T0 + 30_000).toISOString(),
}

function controller({ response = { actions: [{ intent: 'UNLOCK_DOOR', status: 'executed' }] }, error = null } = {}) {
  let clock = T0
  const decide = vi.fn(async () => {
    if (error) throw error
    return response
  })
  const states = []
  const unlock = createDoorUnlockController({ decide, onChange: (s) => states.push(s), now: () => clock })
  return { unlock, decide, states, advance: (ms) => (clock += ms) }
}

describe('FOUR_FINGERS recognition', () => {
  it('recognises four fingers with the thumb folded, in any hand rotation', () => {
    for (const rotation of [{}, { roll: 35 }, { roll: -40 }, { yaw: 45 }]) {
      const result = classifyHand(makeHand(POSES.fourFingers, rotation))
      expect(result.gesture).toBe('FOUR_FINGERS')
      expect(result.confidence).toBeGreaterThanOrEqual(DEFAULT_CONFIDENCE_THRESHOLD)
    }
  })

  it('leaves the five existing gestures exactly as they were', () => {
    const expected = { openPalm: 'OPEN_PALM', fist: 'FIST', thumbsUp: 'THUMBS_UP', oneFinger: 'ONE_FINGER', twoFingers: 'TWO_FINGERS' }
    for (const [pose, gesture] of Object.entries(expected)) {
      expect(classifyHand(makeHand(POSES[pose])).gesture).toBe(gesture)
    }
    expect(classifyHand(makeHand(POSES.openPalm)).confidence).toBe(1) // spread thumb: still OPEN_PALM
  })
})

describe('secure gesture unlock', () => {
  it('FOUR_FINGERS only creates a pending request: nothing is sent until a pinch', () => {
    const { unlock, decide, states } = controller()
    unlock.requested(confirmation, 'Main Door')
    expect(states.at(-1)).toMatchObject({ status: 'pending', deviceName: 'Main Door' })
    expect(decide).not.toHaveBeenCalled()
  })

  it('a stable pinch confirms through the existing API exactly once', async () => {
    const { unlock, decide, states } = controller()
    unlock.requested(confirmation, 'Main Door')

    expect(unlock.pinch({ type: 'start', y: 0.5 })).toBe(true)
    expect(states.at(-1).status).toBe('confirming') // not "unlocked" before the backend says so
    for (const type of ['move', 'end', 'start']) unlock.pinch({ type, y: 0.5 })
    await flush()

    expect(decide).toHaveBeenCalledTimes(1)
    expect(decide).toHaveBeenCalledWith('c1', 'confirm')
    expect(states.at(-1)).toEqual({ status: 'confirmed', deviceName: 'Main Door' })
  })

  it('reports a backend refusal instead of pretending the door unlocked', async () => {
    const { unlock, states } = controller({ response: { actions: [{ status: 'rejected', reason: 'Unlocking is disabled.' }] } })
    unlock.requested(confirmation, 'Main Door')
    unlock.pinch({ type: 'start', y: 0.5 })
    await flush()
    expect(states.at(-1)).toMatchObject({ status: 'failed', message: 'Unlocking is disabled.' })
  })

  it('a pinch without a pending request is not consumed (fan / AC adjustment still works)', () => {
    const { unlock } = controller()
    expect(unlock.pinch({ type: 'start', y: 0.5 })).toBe(false)

    const send = vi.fn()
    const fan = {
      id: 'fan_living_room',
      name: 'Living Room Fan',
      state: { speed: 50 },
      supported_commands: [{ action: 'set_speed', value: { minimum: 0, maximum: 100 } }],
    }
    const adjuster = createAdjustmentController({ getDevice: () => fan, send })
    for (const event of [{ type: 'start', y: 0.6 }, { type: 'move', y: 0.5 }, { type: 'end', y: 0.5, confidence: 0.9 }]) {
      if (!unlock.pinch(event)) adjuster.handle(event)
    }
    expect(send).toHaveBeenCalledTimes(1)
    expect(send.mock.calls[0][0]).toMatchObject({ intent: 'ADJUST', value: 70 })
  })

  it('OPEN_PALM cancels and never unlocks', async () => {
    const { unlock, decide, states } = controller()
    unlock.requested(confirmation, 'Main Door')
    expect(unlock.gesture('OPEN_PALM')).toBe(true) // consumed: no STOP command is sent
    await flush()
    expect(decide).toHaveBeenCalledWith('c1', 'cancel')
    expect(decide).not.toHaveBeenCalledWith('c1', 'confirm')
    expect(states.at(-1).status).toBe('cancelled')
    expect(unlock.pinch({ type: 'start', y: 0.5 })).toBe(false) // a later pinch cannot confirm it
  })

  it.each(['THUMBS_UP', 'FIST', 'ONE_FINGER', 'TWO_FINGERS'])('another gesture (%s) cancels, then runs normally', async (gesture) => {
    const { unlock, decide } = controller()
    unlock.requested(confirmation, 'Main Door')
    expect(unlock.gesture(gesture)).toBe(false)
    await flush()
    expect(decide.mock.calls).toEqual([['c1', 'cancel']])
  })

  it('hand loss, camera stop or leaving the page cancels', async () => {
    const { unlock, decide, states } = controller()
    unlock.requested(confirmation, 'Main Door')
    unlock.cancel('Cancelled: hand out of view.')
    await flush()
    expect(decide.mock.calls).toEqual([['c1', 'cancel']])
    expect(states.at(-1)).toMatchObject({ status: 'cancelled', message: 'Cancelled: hand out of view.' })
  })

  it('an expired request cannot be confirmed', async () => {
    const { unlock, decide, states, advance } = controller()
    unlock.requested(confirmation, 'Main Door')
    advance(31_000)
    unlock.pinch({ type: 'start', y: 0.5 })
    await flush()
    expect(decide).not.toHaveBeenCalled()
    expect(states.at(-1).status).toBe('expired')
  })

  it('a backend "expired" answer is shown as expired', async () => {
    const { unlock, states } = controller({ error: Object.assign(new Error('The confirmation expired'), { code: 'confirmation_expired' }) })
    unlock.requested(confirmation, 'Main Door')
    unlock.pinch({ type: 'start', y: 0.5 })
    await flush()
    expect(states.at(-1).status).toBe('expired')
  })
})

describe('door unlock panel', () => {
  it('shows the request, the confirm and cancel gestures and the time left', () => {
    const html = text(<DoorUnlockPanel doorUnlock={{ status: 'pending', deviceName: 'Main Door', confirmation: { ...confirmation, expires_at: new Date(Date.now() + 25_000).toISOString() } }} />)
    expect(html).toContain('Unlock Main Door?')
    expect(html).toContain('Pinch to confirm')
    expect(html).toContain('Open palm to cancel')
    expect(html).toMatch(/Waiting for confirmation · 2[45] s/)
    expect(html).toContain('The door stays locked until the backend confirms the unlock.')
  })

  it.each([
    ['confirmed', '✓ Unlocked: confirmed by the door'],
    ['cancelled', 'Cancelled · the door stays locked'],
    ['failed', '✗ Not unlocked'],
    ['expired', 'Expired · the door stays locked'],
  ])('%s', (status, label) => {
    expect(text(<DoorUnlockPanel doorUnlock={{ status, deviceName: 'Main Door' }} />)).toContain(label)
  })
})
