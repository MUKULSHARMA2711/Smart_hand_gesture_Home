import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import { doorVisual } from '../../components/3d/visualState'
import { LastActionPanel } from '../../components/gestures/LastActionPanel'
import { createDoorUnlockController } from '../doorUnlock'
import { gestureIntent } from '../gestureIntent'
import { GestureStabilizer } from '../stabilizer'
import { DEFAULT_GESTURE_INTENTS } from '../types'

const flush = async () => {
  for (let i = 0; i < 5; i += 1) await Promise.resolve()
}
const text = (element) => renderToStaticMarkup(element).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ')

// Devices as GET /home/state returns them (capabilities come from the backend).
const door = { id: 'door_main', name: 'Main Door', device_type: 'door_lock', capabilities: ['LOCK', 'UNLOCK'], state: { is_locked: false } }
const fan = { id: 'fan_living_room', device_type: 'fan', capabilities: ['TURN_ON', 'TURN_OFF', 'SET_SPEED'] }
const ac = { id: 'ac_bedroom', device_type: 'ac', capabilities: ['TURN_ON', 'TURN_OFF', 'SET_TEMPERATURE'] }
const light = { id: 'light_living_room', device_type: 'light', capabilities: ['TURN_ON', 'TURN_OFF', 'SET_BRIGHTNESS'] }
const intents = DEFAULT_GESTURE_INTENTS
const confirmation = { confirmation_id: 'c1', device_id: 'door_main', expires_at: new Date(Date.now() + 30_000).toISOString() }

/** The Gesture page's committed-gesture path: the unlock flow first, then the device-aware intent. */
function gesturePage(selected) {
  const sent = []
  const requestUnlock = vi.fn(async () => ({ confirmation, device: { name: 'Main Door' } }))
  const decide = vi.fn(async (id, decision) => ({ actions: [{ status: decision === 'confirm' ? 'executed' : 'cancelled' }] }))
  const states = []
  const unlock = createDoorUnlockController({ requestUnlock, decide, isDoorSelected: () => selected === door, onChange: (s) => states.push(s) })
  const commit = (gesture) => {
    if (unlock.gesture(gesture)) return
    const intent = gestureIntent(gesture, selected, intents)
    if (intent && intent !== 'NONE') sent.push({ gesture, intent, targetDeviceId: selected.id })
  }
  return { unlock, commit, sent, decide, requestUnlock, states }
}

describe('FIST is routed by the selected device', () => {
  it('FIST with the Main Door selected requests LOCK_DOOR', () => {
    expect(gestureIntent('FIST', door, intents)).toBe('LOCK_DOOR')
    const page = gesturePage(door)
    page.commit('FIST')
    expect(page.sent).toEqual([{ gesture: 'FIST', intent: 'LOCK_DOOR', targetDeviceId: 'door_main' }])
  })

  it.each([
    ['fan', fan],
    ['AC', ac],
    ['light', light],
  ])('FIST on the %s is still TURN_OFF', (_, device) => {
    expect(gestureIntent('FIST', device, intents)).toBe('TURN_OFF')
  })

  it('every other gesture keeps its mapping on the door, and no gesture ever means UNLOCK_DOOR', () => {
    for (const gesture of ['THUMBS_UP', 'OPEN_PALM', 'ONE_FINGER', 'TWO_FINGERS', 'PINCH', 'NEUTRAL', 'UNKNOWN']) {
      expect(gestureIntent(gesture, door, intents)).toBe(intents[gesture])
    }
    for (const device of [door, fan, ac, light, null]) {
      for (const gesture of Object.keys(intents)) expect(gestureIntent(gesture, device, intents)).not.toBe('UNLOCK_DOOR')
    }
  })

  it('without a LOCK capability (or a selection) a fist is TURN_OFF, and the global mapping is unchanged', () => {
    expect(gestureIntent('FIST', { device_type: 'door_lock', capabilities: [] }, intents)).toBe('TURN_OFF')
    expect(gestureIntent('FIST', null, intents)).toBe('TURN_OFF')
    expect(DEFAULT_GESTURE_INTENTS.FIST).toBe('TURN_OFF')
  })
})

describe('FIST and the double-pinch unlock', () => {
  it('a fist during a pending unlock only cancels it: no unlock, no lock in the same gesture', async () => {
    const page = gesturePage(door)
    page.unlock.pinch({ type: 'start', y: 0.5, confidence: 0.9 }) // first pinch → pending
    await flush()
    expect(page.unlock.pending).toBe(true)

    page.commit('FIST')
    await flush()

    expect(page.decide.mock.calls).toEqual([['c1', 'cancel']]) // never 'confirm'
    expect(page.sent).toEqual([]) // the same fist did not also lock
    expect(page.states.at(-1)).toMatchObject({ status: 'cancelled', message: 'Cancelled with a fist. The door stays locked.' })

    page.commit('FIST') // a separate, later fist locks
    expect(page.sent).toEqual([{ gesture: 'FIST', intent: 'LOCK_DOOR', targetDeviceId: 'door_main' }])
  })

  it('a fist while the unlock request is still being answered is ignored', async () => {
    const page = gesturePage(door)
    page.unlock.pinch({ type: 'start', y: 0.5, confidence: 0.9 })
    page.commit('FIST') // before the backend replied
    expect(page.sent).toEqual([])
    await flush()
    expect(page.decide).not.toHaveBeenCalled()
  })

  it('the second pinch still confirms, and open palm still cancels', async () => {
    const confirmPage = gesturePage(door)
    confirmPage.unlock.pinch({ type: 'start', y: 0.5, confidence: 0.9 })
    await flush()
    confirmPage.unlock.pinch({ type: 'start', y: 0.5, confidence: 0.9 })
    await flush()
    expect(confirmPage.decide.mock.calls).toEqual([['c1', 'confirm']])

    const palmPage = gesturePage(door)
    palmPage.unlock.pinch({ type: 'start', y: 0.5, confidence: 0.9 })
    await flush()
    palmPage.commit('OPEN_PALM')
    await flush()
    expect(palmPage.decide.mock.calls).toEqual([['c1', 'cancel']])
    expect(palmPage.sent).toEqual([])
  })
})

describe('unchanged pieces and backend-confirmed display', () => {
  it('the stabilizer still needs a 0.6 s hold', () => {
    const stabilizer = new GestureStabilizer({ threshold: 0.75 })
    expect(stabilizer.holdMs).toBe(600)
    expect(stabilizer.update({ gesture: 'FIST', confidence: 0.9 }, 0).commit).toBeNull()
    expect(stabilizer.update({ gesture: 'FIST', confidence: 0.9 }, 599).commit).toBeNull()
    expect(stabilizer.update({ gesture: 'FIST', confidence: 0.9 }, 600).commit).toEqual({ gesture: 'FIST', confidence: 0.9 })
  })

  it('the 3D door follows only the backend snapshot, before and after the fist', () => {
    const page = gesturePage(door)
    page.commit('FIST')
    // The request carries only the recognition result, never a door state to apply.
    expect(Object.keys(page.sent[0]).sort()).toEqual(['gesture', 'intent', 'targetDeviceId'])
    expect(doorVisual(door.state)).toMatchObject({ locked: false, label: 'UNLOCKED' }) // until the backend confirms
    const confirmed = { gesture_event: { outcome: 'executed', action: 'lock' }, device: { ...door, state: { is_locked: true } } }
    expect(doorVisual(confirmed.device.state)).toMatchObject({ locked: true, angle: 0, label: 'LOCKED' })
  })

  it('an already-locked door is reported, not re-locked', () => {
    const html = text(
      <LastActionPanel
        lastAction={{ status: 'success', gesture: 'FIST', intent: 'LOCK_DOOR', confidence: 0.92, targetId: 'door_main', action: 'lock', message: 'Main Door is already locked.' }}
        deviceNames={{ door_main: 'Main Door' }}
      />,
    )
    expect(html).toContain('Main Door is already locked.')
    expect(html).toContain('LOCK_DOOR')
  })
})
