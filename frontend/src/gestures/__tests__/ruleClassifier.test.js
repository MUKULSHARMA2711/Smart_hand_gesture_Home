import { describe, expect, it } from 'vitest'
import { classifyHand, measureFingers } from '../ruleClassifier'
import { DEFAULT_CONFIDENCE_THRESHOLD } from '../types'
import { makeHand, POSES } from './syntheticHand'

const CASES = [
  ['openPalm', 'OPEN_PALM'],
  ['fist', 'FIST'],
  ['thumbsUp', 'THUMBS_UP'],
  ['oneFinger', 'ONE_FINGER'],
  ['twoFingers', 'TWO_FINGERS'],
]

describe('classifyHand', () => {
  it.each(CASES)('recognises %s as %s above the confidence threshold', (pose, expected) => {
    const result = classifyHand(makeHand(POSES[pose]))

    expect(result.gesture).toBe(expected)
    expect(result.confidence).toBeGreaterThanOrEqual(DEFAULT_CONFIDENCE_THRESHOLD)
    expect(result.confidence).toBeLessThanOrEqual(1)
  })

  it.each(CASES.filter(([pose]) => pose !== 'thumbsUp'))(
    'recognises %s regardless of hand rotation',
    (pose, expected) => {
      for (const rotation of [{ roll: 35 }, { roll: -40 }, { yaw: 45 }, { roll: 20, yaw: -30 }]) {
        expect(classifyHand(makeHand(POSES[pose], rotation)).gesture).toBe(expected)
      }
    },
  )

  it('requires the thumb to point up for THUMBS_UP', () => {
    const result = classifyHand(makeHand(POSES.thumbsDown))

    expect(result.gesture).not.toBe('THUMBS_UP')
  })

  it('reports an ambiguous, half-closed hand below the threshold', () => {
    const result = classifyHand(makeHand(POSES.halfClosed))

    expect(result.gesture === 'UNKNOWN' || result.confidence < DEFAULT_CONFIDENCE_THRESHOLD).toBe(true)
  })

  it('exposes per-finger extension scores', () => {
    const fingers = measureFingers(makeHand(POSES.oneFinger).worldLandmarks)

    expect(fingers.index).toBeGreaterThan(0.9)
    expect(fingers.middle).toBeLessThan(0.1)
    expect(fingers.thumb).toBeLessThan(0.5)
  })
})
