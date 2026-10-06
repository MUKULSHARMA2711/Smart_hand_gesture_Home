import { describe, expect, it, vi } from 'vitest'
import { createAdjustmentController, formatAdjustment } from '../adjustment'
import { createPinchDetector, pinchRatio } from '../pinch'
import { DEFAULT_GESTURE_INTENTS } from '../types'

/** 21 image landmarks: wrist at (0.5, y+0.3), middle knuckle 0.2 above it; thumb/index tips `gap` apart. */
function hand({ y = 0.5, gap = 0.02 } = {}) {
  const points = Array.from({ length: 21 }, () => ({ x: 0.5, y }))
  points[0] = { x: 0.5, y: y + 0.3 } // wrist
  points[9] = { x: 0.5, y: y + 0.1 } // middle MCP → hand size 0.2
  points[4] = { x: 0.45, y } // thumb tip
  points[8] = { x: 0.45 + gap, y } // index tip
  return points
}
const OPEN = { thumb: 0.5, index: 0.3, middle: 0.9, ring: 0.9, pinky: 0.8 } // "OK" pinch
const FIST = { thumb: 0.1, index: 0.1, middle: 0.1, ring: 0.1, pinky: 0.1 }
const frame = (opts, fingers = OPEN) => ({ landmarks: hand(opts), fingers })

function feed(detector, frames) {
  return frames.map((f) => detector.update(f)).filter(Boolean)
}

describe('pinch detection', () => {
  it('measures the thumb-index gap relative to hand size', () => {
    expect(pinchRatio(hand({ gap: 0.02 }))).toBeCloseTo(0.1)
    expect(pinchRatio(hand({ gap: 0.12 }))).toBeCloseTo(0.6)
    expect(pinchRatio(null)).toBeNull()
  })

  it('starts only after a stable pinch (no single-frame trigger) and ends on a clear release', () => {
    const detector = createPinchDetector()
    // A one-frame dip followed by open fingers never starts a pinch.
    expect(feed(detector, [frame({ gap: 0.02 }), frame({ gap: 0.12 }), frame({ gap: 0.02 })])).toEqual([])

    const events = feed(createPinchDetector(), [
      ...Array(4).fill(frame({ gap: 0.02 })),
      frame({ gap: 0.07 }), // between the thresholds: still pinching (hysteresis)
      ...Array(3).fill(frame({ gap: 0.12 })),
    ])
    expect(events.map((e) => e.type)).toEqual(['start', 'move', 'move', 'move', 'end'])
    expect(events.at(-1).confidence).toBeGreaterThanOrEqual(0.75)
  })

  it('is not triggered by a fist, where the thumb also rests near the index finger', () => {
    const detector = createPinchDetector()
    expect(feed(detector, Array(10).fill(frame({ gap: 0.02 }, FIST)))).toEqual([])
    expect(detector.engaged).toBe(false)
  })

  it('cancels when the hand is lost mid-pinch', () => {
    const detector = createPinchDetector()
    feed(detector, Array(4).fill(frame({ gap: 0.02 })))
    expect(detector.update({ landmarks: null }).type).toBe('cancel')
    expect(detector.pinching).toBe(false)
  })
})

const fan = {
  id: 'fan_living_room',
  name: 'Living Room Fan',
  state: { is_on: true, speed: 50 },
  supported_commands: [{ action: 'set_speed', value: { type: 'integer', minimum: 0, maximum: 100 } }],
}
const ac = {
  id: 'ac_bedroom',
  name: 'Bedroom AC',
  state: { is_on: true, target_temperature_c: 24 },
  supported_commands: [{ action: 'set_temperature', value: { type: 'integer', minimum: 16, maximum: 30 } }],
}
const door = { id: 'door_main', name: 'Main Door', state: { is_locked: true }, supported_commands: [{ action: 'lock' }, { action: 'unlock' }] }

function controller(device) {
  const send = vi.fn()
  const states = []
  const c = createAdjustmentController({ getDevice: () => device, send, onChange: (s) => states.push(s) })
  return { c, send, states }
}
const run = (c, startY, ys, ending = 'end') => {
  c.handle({ type: 'start', y: startY, confidence: 0.9 })
  for (const y of ys) c.handle({ type: 'move', y, confidence: 0.9 })
  c.handle({ type: ending, y: ys.at(-1), confidence: 0.92 })
}

describe('pinch adjustment', () => {
  it('fan: previews every move, hand up = faster, and sends ONE command on release', () => {
    const { c, send, states } = controller(fan)
    c.handle({ type: 'start', y: 0.6, confidence: 0.9 })
    const moves = [0.58, 0.55, 0.5, 0.48, 0.45]
    for (const y of moves) c.handle({ type: 'move', y, confidence: 0.9 })

    expect(send).not.toHaveBeenCalled() // zero commands during continuous movement
    expect(states.map((s) => s.value)).toEqual([50, 54, 60, 70, 74, 80])
    expect(formatAdjustment(states[0].range, 80)).toBe('80%')
    expect(states[0].range.title).toBe('Fan Speed')

    c.handle({ type: 'end', y: 0.45, confidence: 0.92 })
    expect(send).toHaveBeenCalledTimes(1)
    expect(send).toHaveBeenCalledWith({
      gesture: 'PINCH',
      intent: 'ADJUST',
      value: 80,
      targetDeviceId: 'fan_living_room',
      confidence: 0.92,
      deviceName: 'Living Room Fan',
    })
    c.handle({ type: 'end', y: 0.4, confidence: 0.9 }) // a stray release sends nothing more
    expect(send).toHaveBeenCalledTimes(1)
  })

  it('fan: hand down = slower, clamped at 0', () => {
    const { c, send } = controller(fan)
    run(c, 0.4, [0.6, 0.9, 1.0])
    expect(send.mock.calls[0][0].value).toBe(0)
  })

  it('AC: hand up = cooler, hand down = warmer, within 16–30 °C', () => {
    const up = controller(ac)
    run(up.c, 0.6, [0.5, 0.4])
    expect(up.states[0].range.title).toBe('AC Temperature')
    expect(up.send.mock.calls[0][0]).toMatchObject({ intent: 'ADJUST', value: 18, targetDeviceId: 'ac_bedroom' })

    const down = controller(ac)
    run(down.c, 0.4, [0.5, 0.6, 0.99])
    expect(down.send.mock.calls[0][0].value).toBe(30) // clamped to the published maximum
    expect(formatAdjustment(up.states[0].range, 22)).toBe('22 °C')
  })

  it('the door never enters adjustment mode and never receives ADJUST', () => {
    const { c, send, states } = controller(door)
    run(c, 0.6, [0.3, 0.1])
    expect(states[0]).toEqual({ status: 'unsupported', deviceName: 'Main Door' })
    expect(c.active).toBe(false)
    expect(send).not.toHaveBeenCalled()
  })

  it('sends nothing when the value is unchanged or the hand is lost', () => {
    const same = controller(fan)
    run(same.c, 0.5, [0.52, 0.5])
    expect(same.send).not.toHaveBeenCalled()
    expect(same.states.at(-1).status).toBe('unchanged')

    const lost = controller(fan)
    run(lost.c, 0.6, [0.4], 'cancel')
    expect(lost.send).not.toHaveBeenCalled()
    expect(lost.states.at(-1).status).toBe('cancelled')
  })

  it('leaves the five existing gesture mappings unchanged', () => {
    expect(DEFAULT_GESTURE_INTENTS).toEqual({
      THUMBS_UP: 'TURN_ON',
      FIST: 'TURN_OFF',
      OPEN_PALM: 'STOP',
      ONE_FINGER: 'SELECT',
      TWO_FINGERS: 'TOGGLE',
      PINCH: 'ADJUST',
      FOUR_FINGERS: 'UNLOCK_DOOR',
      NEUTRAL: 'NONE',
      UNKNOWN: 'NONE',
    })
  })
})
