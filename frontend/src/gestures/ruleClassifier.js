/**
 * Rule-based gesture classifier over MediaPipe's 21 hand landmarks.
 *
 * Pure functions with no MediaPipe dependency, so the classifier can be unit tested
 * and later replaced by a trained model without touching the camera or UI code.
 *
 * Each finger gets an extension score in [0, 1] from joint angles and distances in
 * metric 3D world landmarks (rotation-invariant). Each gesture is a fuzzy AND of
 * finger conditions; the best-scoring gesture wins and its score is the confidence.
 */
import { GESTURES } from './types'

// MediaPipe hand landmark indices.
const WRIST = 0
const THUMB = { cmc: 1, mcp: 2, ip: 3, tip: 4 }
const FINGERS = {
  index: { mcp: 5, pip: 6, dip: 7, tip: 8 },
  middle: { mcp: 9, pip: 10, dip: 11, tip: 12 },
  ring: { mcp: 13, pip: 14, dip: 15, tip: 16 },
  pinky: { mcp: 17, pip: 18, dip: 19, tip: 20 },
}

// Below this score the hand is reported as UNKNOWN rather than a weak guess.
const MIN_GESTURE_SCORE = 0.5
// Four fingers up is an open palm with the thumb folded. Below this thumb extension the hand
// is FOUR_FINGERS; at or above it, OPEN_PALM exactly as before (a spread thumb scores ~1).
const THUMB_FOLDED = 0.4

const sub = (a, b) => ({ x: a.x - b.x, y: a.y - b.y, z: (a.z ?? 0) - (b.z ?? 0) })
const norm = (v) => Math.hypot(v.x, v.y, v.z)
const dist = (a, b) => norm(sub(a, b))
const clamp01 = (v) => Math.min(1, Math.max(0, v))
/** Linear ramp: 0 at `zero`, 1 at `one` (either direction). */
const ramp = (value, zero, one) => clamp01((value - zero) / (one - zero))

/** Angle in degrees between two direction vectors (0 = same direction). */
function angleBetween(u, v) {
  const denominator = norm(u) * norm(v)
  if (denominator === 0) return 0
  const cos = (u.x * v.x + u.y * v.y + u.z * v.z) / denominator
  return (Math.acos(Math.min(1, Math.max(-1, cos))) * 180) / Math.PI
}

/** Total bend along a chain of joints, e.g. [mcp, pip, dip, tip]. */
function chainBend(points) {
  let total = 0
  for (let i = 0; i < points.length - 2; i++) {
    total += angleBetween(sub(points[i + 1], points[i]), sub(points[i + 2], points[i + 1]))
  }
  return total
}

/** Fuzzy AND that is mostly the weakest condition, softened by the average. */
function fuzzyAnd(...scores) {
  const min = Math.min(...scores)
  const mean = scores.reduce((sum, s) => sum + s, 0) / scores.length
  return 0.6 * min + 0.4 * mean
}

function fingerExtension(world, finger) {
  const joints = [finger.mcp, finger.pip, finger.dip, finger.tip].map((i) => world[i])
  const straightness = ramp(chainBend(joints), 100, 50) // straight finger bends < 50° in total
  const reach = ramp(dist(world[WRIST], world[finger.tip]) / dist(world[WRIST], world[finger.pip]), 0.95, 1.2)
  return (straightness + reach) / 2
}

// Knuckles a tucked thumb rests against (index, middle and ring MCP + PIP joints).
const THUMB_REST_POINTS = [5, 6, 9, 10, 13, 14]

function thumbExtension(world, palmSize) {
  const joints = [THUMB.cmc, THUMB.mcp, THUMB.ip, THUMB.tip].map((i) => world[i])
  const straightness = ramp(chainBend(joints), 70, 30)
  // A tucked thumb touches the nearest finger knuckle; an extended one sticks out from all of them.
  const clearance = Math.min(...THUMB_REST_POINTS.map((i) => dist(world[THUMB.tip], world[i])))
  const spread = ramp(clearance / palmSize, 0.3, 0.45)
  return (straightness + spread) / 2
}

/** How vertically "up" the thumb points in the image (y grows downwards). */
function thumbPointsUp(image, aspectRatio) {
  const dx = (image[THUMB.tip].x - image[THUMB.mcp].x) * aspectRatio
  const dy = image[THUMB.tip].y - image[THUMB.mcp].y
  const length = Math.hypot(dx, dy)
  return length === 0 ? 0 : ramp(-dy / length, 0.5, 0.85)
}

/** Per-finger extension scores: 0 = fully curled, 1 = fully extended. */
export function measureFingers(worldLandmarks) {
  const palmSize = dist(worldLandmarks[WRIST], worldLandmarks[FINGERS.middle.mcp])
  return {
    thumb: thumbExtension(worldLandmarks, palmSize),
    index: fingerExtension(worldLandmarks, FINGERS.index),
    middle: fingerExtension(worldLandmarks, FINGERS.middle),
    ring: fingerExtension(worldLandmarks, FINGERS.ring),
    pinky: fingerExtension(worldLandmarks, FINGERS.pinky),
  }
}

/** Score every gesture for one hand. */
export function scoreGestures(fingers, thumbUp) {
  const curled = (name) => 1 - fingers[name]
  return {
    [GESTURES.OPEN_PALM]: fuzzyAnd(fingers.index, fingers.middle, fingers.ring, fingers.pinky),
    [GESTURES.FIST]: fuzzyAnd(curled('index'), curled('middle'), curled('ring'), curled('pinky'), curled('thumb')),
    [GESTURES.THUMBS_UP]: fuzzyAnd(
      curled('index'), curled('middle'), curled('ring'), curled('pinky'), fingers.thumb, thumbUp,
    ),
    [GESTURES.ONE_FINGER]: fuzzyAnd(fingers.index, curled('middle'), curled('ring'), curled('pinky')),
    [GESTURES.TWO_FINGERS]: fuzzyAnd(fingers.index, fingers.middle, curled('ring'), curled('pinky')),
    [GESTURES.FOUR_FINGERS]: fuzzyAnd(fingers.index, fingers.middle, fingers.ring, fingers.pinky, curled('thumb')),
  }
}

/**
 * Classify one hand.
 * @param {{landmarks: Array, worldLandmarks: Array, aspectRatio?: number}} hand
 *   `landmarks` are normalized image coordinates, `worldLandmarks` metric 3D coordinates.
 * @returns {{gesture: string, confidence: number, fingers: Record<string, number>}}
 */
export function classifyHand({ landmarks, worldLandmarks, aspectRatio = 4 / 3 }) {
  const fingers = measureFingers(worldLandmarks)
  const scores = scoreGestures(fingers, thumbPointsUp(landmarks, aspectRatio))
  // OPEN_PALM and FOUR_FINGERS share the four fingers; the thumb decides which one this is,
  // so they never compete (which would lower both confidences).
  delete scores[fingers.thumb < THUMB_FOLDED ? GESTURES.OPEN_PALM : GESTURES.FOUR_FINGERS]
  const [[bestGesture, best], [, runnerUp]] = Object.entries(scores).sort((a, b) => b[1] - a[1])

  if (best < MIN_GESTURE_SCORE) {
    return { gesture: GESTURES.UNKNOWN, confidence: round(1 - best), fingers }
  }
  // Penalise ambiguity: a strong runner-up lowers confidence in the winner.
  const confidence = clamp01(best - 0.5 * Math.max(0, runnerUp - 0.25))
  return { gesture: bestGesture, confidence: round(confidence), fingers }
}

const round = (value) => Math.round(value * 1000) / 1000
