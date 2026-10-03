import { describe, expect, it } from 'vitest'
import { GestureStabilizer } from '../stabilizer'

const FRAME_MS = 33

/** Feed `durationMs` of identical frames; return every commit. */
function feed(stabilizer, frame, startMs, durationMs) {
  const commits = []
  let now = startMs
  for (; now <= startMs + durationMs; now += FRAME_MS) {
    const { commit } = stabilizer.update(frame, now)
    if (commit) commits.push(commit)
  }
  return { commits, endMs: now }
}

const thumbsUp = { gesture: 'THUMBS_UP', confidence: 0.92 }
const fist = { gesture: 'FIST', confidence: 0.9 }
const noHand = { gesture: 'NEUTRAL', confidence: 0 }

describe('GestureStabilizer', () => {
  it('commits a gesture once it has been held long enough', () => {
    const stabilizer = new GestureStabilizer({ holdMs: 600 })

    expect(feed(stabilizer, thumbsUp, 0, 500).commits).toEqual([])
    const { commits } = feed(stabilizer, thumbsUp, 533, 200)

    expect(commits).toEqual([{ gesture: 'THUMBS_UP', confidence: 0.92 }])
  })

  it('never commits below the confidence threshold', () => {
    const stabilizer = new GestureStabilizer({ threshold: 0.75 })

    expect(feed(stabilizer, { gesture: 'THUMBS_UP', confidence: 0.7 }, 0, 3000).commits).toEqual([])
  })

  it('never commits NEUTRAL or UNKNOWN', () => {
    const stabilizer = new GestureStabilizer()

    expect(feed(stabilizer, noHand, 0, 2000).commits).toEqual([])
    expect(feed(stabilizer, { gesture: 'UNKNOWN', confidence: 0.99 }, 2100, 2000).commits).toEqual([])
  })

  it('fires once while a gesture is held, and again only after release', () => {
    const stabilizer = new GestureStabilizer({ holdMs: 600, cooldownMs: 1000 })

    const held = feed(stabilizer, thumbsUp, 0, 5000)
    expect(held.commits).toHaveLength(1)

    const released = feed(stabilizer, noHand, held.endMs, 500)
    const again = feed(stabilizer, thumbsUp, released.endMs, 1000)
    expect(again.commits).toHaveLength(1)
  })

  it('tolerates brief dropouts during a hold', () => {
    const stabilizer = new GestureStabilizer({ holdMs: 600, graceMs: 200 })

    const first = feed(stabilizer, thumbsUp, 0, 400)
    const blip = feed(stabilizer, noHand, first.endMs, 100)
    const { commits } = feed(stabilizer, thumbsUp, blip.endMs, 200)

    expect(commits).toHaveLength(1)
  })

  it('enforces a cooldown between different gestures', () => {
    const stabilizer = new GestureStabilizer({ holdMs: 300, cooldownMs: 1500 })

    const first = feed(stabilizer, thumbsUp, 0, 400)
    expect(first.commits).toHaveLength(1)

    // FIST is held long enough, but the cooldown delays it.
    const early = feed(stabilizer, fist, first.endMs, 700)
    expect(early.commits).toEqual([])
    const later = feed(stabilizer, fist, early.endMs, 1000)
    expect(later.commits).toEqual([{ gesture: 'FIST', confidence: 0.9 }])
  })

  it('reports hold progress for the UI', () => {
    const stabilizer = new GestureStabilizer({ holdMs: 600 })

    stabilizer.update(thumbsUp, 0)
    const { candidate, progress } = stabilizer.update(thumbsUp, 300)

    expect(candidate).toBe('THUMBS_UP')
    expect(progress).toBeCloseTo(0.5)
  })
})
