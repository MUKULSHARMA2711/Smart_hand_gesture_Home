import { DEFAULT_CONFIDENCE_THRESHOLD, isActionable } from './types'

/**
 * Turns a noisy per-frame gesture stream into discrete, deliberate commands.
 *
 * - A gesture must stay above the confidence threshold for `holdMs` to commit.
 * - Brief dropouts shorter than `graceMs` (a blurred frame) do not reset the hold.
 * - After a commit, the same gesture must be released before it can fire again, so
 *   holding a thumbs-up turns the light on once rather than repeatedly.
 * - `cooldownMs` enforces a minimum gap between any two commits.
 * Low-confidence frames are still reported for display but never commit.
 */
export class GestureStabilizer {
  constructor({ threshold = DEFAULT_CONFIDENCE_THRESHOLD, holdMs = 600, graceMs = 200, cooldownMs = 1000 } = {}) {
    Object.assign(this, { threshold, holdMs, graceMs, cooldownMs })
    this.reset()
  }

  reset() {
    this.candidate = null
    this.since = 0
    this.lastMatchAt = 0
    this.confidenceSum = 0
    this.samples = 0
    this.lastFired = null
    this.lastFiredAt = -Infinity
  }

  /**
   * @param {{gesture: string, confidence: number}} result  this frame's recognition
   * @param {number} nowMs  monotonic timestamp
   * @returns {{candidate: string|null, progress: number, awaitingRelease: boolean,
   *           commit: {gesture: string, confidence: number}|null}}
   */
  update({ gesture, confidence }, nowMs) {
    const qualifies = isActionable(gesture) && confidence >= this.threshold

    if (qualifies) {
      if (gesture !== this.candidate) {
        this.candidate = gesture
        this.since = nowMs
        this.confidenceSum = 0
        this.samples = 0
      }
      this.lastMatchAt = nowMs
      this.confidenceSum += confidence
      this.samples += 1
    } else if (this.candidate && nowMs - this.lastMatchAt > this.graceMs) {
      this.candidate = null
    }

    // Re-arm once the gesture that last fired is no longer being held.
    if (this.lastFired && this.candidate !== this.lastFired) this.lastFired = null

    const heldMs = this.candidate ? nowMs - this.since : 0
    let commit = null
    if (
      this.candidate &&
      !this.lastFired &&
      heldMs >= this.holdMs &&
      nowMs - this.lastFiredAt >= this.cooldownMs
    ) {
      commit = { gesture: this.candidate, confidence: Math.round((this.confidenceSum / this.samples) * 1000) / 1000 }
      this.lastFired = this.candidate
      this.lastFiredAt = nowMs
    }

    return {
      candidate: this.candidate,
      progress: this.lastFired ? 1 : Math.min(1, heldMs / this.holdMs),
      awaitingRelease: Boolean(this.lastFired),
      commit,
    }
  }
}
