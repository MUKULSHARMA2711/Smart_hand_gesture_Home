/**
 * Pinch detection for the adjustment gesture, from the same MediaPipe landmarks and finger
 * scores the gesture classifier already produces (the classifier and the five gestures are
 * unchanged).
 *
 * A pinch is the thumb tip touching the index tip *with the other fingers open* (like an
 * "OK" sign). Requiring open fingers keeps it apart from a fist, where the thumb also rests
 * near the index finger. Hysteresis avoids flicker: a pinch starts only after several
 * consecutive pinched frames, and ends only when the fingers are clearly apart again.
 *
 * Events: start (enter adjustment), move (preview), end (release: apply once), cancel
 * (hand lost: apply nothing).
 */

const WRIST = 0
const THUMB_TIP = 4
const INDEX_TIP = 8
const MIDDLE_MCP = 9

const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y)

/** Thumb–index tip distance relative to hand size (wrist → middle knuckle), or null. */
export function pinchRatio(landmarks) {
  if (!landmarks?.[MIDDLE_MCP]) return null
  const size = dist(landmarks[WRIST], landmarks[MIDDLE_MCP])
  return size > 0 ? dist(landmarks[THUMB_TIP], landmarks[INDEX_TIP]) / size : null
}

/** At least two of middle / ring / pinky extended. */
function otherFingersOpen(fingers, minExtension) {
  if (!fingers) return false
  return ['middle', 'ring', 'pinky'].filter((name) => (fingers[name] ?? 0) >= minExtension).length >= 2
}

export function createPinchDetector({
  enterRatio = 0.3,
  exitRatio = 0.5,
  enterFrames = 4,
  exitFrames = 3,
  minFingerExtension = 0.55,
  smoothing = 0.35, // EMA weight of the newest hand position
} = {}) {
  let pinching = false
  let streak = 0 // consecutive frames that point to the other state
  let y = null
  let marginSum = 0
  let samples = 0

  const reset = () => {
    pinching = false
    streak = 0
    y = null
    marginSum = 0
    samples = 0
  }

  return {
    get pinching() {
      return pinching
    },
    /** True while a pinch is forming or held: the caller should not act on other gestures. */
    get engaged() {
      return pinching || streak > 0
    },
    /**
     * @param {{landmarks?: Array<{x:number,y:number}>|null, fingers?: Record<string, number>}} frame
     * @returns {{type: 'start'|'move'|'end'|'cancel', y: number, confidence: number}|null}
     */
    update({ landmarks, fingers } = {}) {
      const ratio = pinchRatio(landmarks)
      if (ratio === null) {
        const wasPinching = pinching
        const lastY = y
        reset()
        return wasPinching ? { type: 'cancel', y: lastY, confidence: 0 } : null
      }

      const pointY = (landmarks[THUMB_TIP].y + landmarks[INDEX_TIP].y) / 2
      y = y === null ? pointY : y + smoothing * (pointY - y)

      if (!pinching) {
        const closed = ratio < enterRatio && otherFingersOpen(fingers, minFingerExtension)
        streak = closed ? streak + 1 : 0
        if (streak >= enterFrames) {
          pinching = true
          streak = 0
          marginSum = 0
          samples = 0
          return { type: 'start', y, confidence: this.confidence(ratio) }
        }
        return null
      }

      // Pinching: confidence follows how clearly the fingers stay together.
      marginSum += Math.max(0, (enterRatio - ratio) / enterRatio)
      samples += 1
      streak = ratio > exitRatio ? streak + 1 : 0
      if (streak >= exitFrames) {
        const confidence = this.confidence()
        const lastY = y
        reset()
        return { type: 'end', y: lastY, confidence }
      }
      return { type: 'move', y, confidence: this.confidence() }
    },
    /**
     * 0.75 at the entry threshold up to 1 for fully closed fingers, averaged over the pinch:
     * a pinch only exists past the detector's threshold, so this expresses its margin.
     */
    confidence(ratio) {
      const margin = samples ? marginSum / samples : Math.max(0, (enterRatio - (ratio ?? enterRatio)) / enterRatio)
      return Math.round((0.75 + 0.25 * Math.min(1, margin)) * 1000) / 1000
    },
    reset,
  }
}
