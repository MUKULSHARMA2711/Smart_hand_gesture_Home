/**
 * Builds MediaPipe-shaped hand landmarks from a simple kinematic hand model, so the
 * classifier can be tested without a camera. World coordinates are metres with the
 * wrist at the origin, y pointing down (as in image space) and fingers pointing up.
 */

const FINGER_MCPS = {
  index: { x: 0.025, y: -0.085 },
  middle: { x: 0.003, y: -0.09 },
  ring: { x: -0.018, y: -0.083 },
  pinky: { x: -0.036, y: -0.07 },
}
const FINGER_ORDER = ['index', 'middle', 'ring', 'pinky']
const SEGMENTS = { index: [0.04, 0.025, 0.02], middle: [0.045, 0.028, 0.02], ring: [0.042, 0.026, 0.02], pinky: [0.032, 0.02, 0.018] }

// Flexion (degrees) at MCP, PIP and DIP joints.
const FINGER_POSES = {
  extended: [5, 5, 5],
  curled: [70, 100, 60],
  half: [35, 50, 30],
}

const THUMB_CMC = { x: 0.035, y: -0.025, z: 0 }
const THUMB_SEGMENTS = [0.045, 0.03, 0.025]
const THUMB_POSES = {
  out: { x: 0.55, y: -0.83, z: 0 }, // spread sideways, as in an open palm
  up: { x: 0.05, y: -1, z: 0 },
  down: { x: 0.05, y: 1, z: 0 },
}
// Thumb folded over the curled fingers, as in a fist.
const TUCKED_THUMB = [
  THUMB_CMC,
  { x: 0.04, y: -0.05, z: -0.015 },
  { x: 0.03, y: -0.072, z: -0.04 },
  { x: 0.012, y: -0.088, z: -0.052 },
]

const add = (a, b, scale = 1) => ({ x: a.x + b.x * scale, y: a.y + b.y * scale, z: a.z + b.z * scale })
const unit = (v) => {
  const length = Math.hypot(v.x, v.y, v.z)
  return { x: v.x / length, y: v.y / length, z: v.z / length }
}

function fingerJoints(name, pose) {
  const mcp = { ...FINGER_MCPS[name], z: 0 }
  const joints = [mcp]
  let flexion = 0
  let point = mcp
  FINGER_POSES[pose].forEach((angle, i) => {
    flexion += angle
    const radians = (flexion * Math.PI) / 180
    point = add(point, { x: 0, y: -Math.cos(radians), z: -Math.sin(radians) }, SEGMENTS[name][i])
    joints.push(point)
  })
  return joints
}

// Thumb folded across the palm towards the ring finger, as when showing four fingers.
const FOLDED_THUMB = [
  THUMB_CMC,
  { x: 0.03, y: -0.045, z: -0.018 },
  { x: 0.01, y: -0.058, z: -0.03 },
  { x: -0.01, y: -0.07, z: -0.02 },
]

function thumbJoints(pose) {
  if (pose === 'tucked') return TUCKED_THUMB
  if (pose === 'folded') return FOLDED_THUMB
  const direction = unit(THUMB_POSES[pose])
  const joints = [THUMB_CMC]
  THUMB_SEGMENTS.forEach((length) => joints.push(add(joints.at(-1), direction, length)))
  return joints
}

/** Rotation about the z axis (in the image plane) then the y axis (turning the hand). */
function rotate(point, { roll = 0, yaw = 0 }) {
  const r = (roll * Math.PI) / 180
  const y = (yaw * Math.PI) / 180
  const rolled = { x: point.x * Math.cos(r) - point.y * Math.sin(r), y: point.x * Math.sin(r) + point.y * Math.cos(r), z: point.z }
  return { x: rolled.x * Math.cos(y) + rolled.z * Math.sin(y), y: rolled.y, z: -rolled.x * Math.sin(y) + rolled.z * Math.cos(y) }
}

/**
 * @param {{thumb: 'out'|'up'|'down'|'tucked'|'folded', index: string, middle: string, ring: string, pinky: string}} pose
 * @param {{roll?: number, yaw?: number}} [rotation]
 */
export function makeHand(pose, rotation = {}) {
  const world = [{ x: 0, y: 0, z: 0 }, ...thumbJoints(pose.thumb)]
  FINGER_ORDER.forEach((name) => world.push(...fingerJoints(name, pose[name])))
  const worldLandmarks = world.map((point) => rotate(point, rotation))
  const landmarks = worldLandmarks.map((p) => ({ x: 0.5 + p.x * 2.5, y: 0.6 + p.y * 2.5, z: p.z }))
  return { landmarks, worldLandmarks, aspectRatio: 1 }
}

export const POSES = {
  openPalm: { thumb: 'out', index: 'extended', middle: 'extended', ring: 'extended', pinky: 'extended' },
  fist: { thumb: 'tucked', index: 'curled', middle: 'curled', ring: 'curled', pinky: 'curled' },
  thumbsUp: { thumb: 'up', index: 'curled', middle: 'curled', ring: 'curled', pinky: 'curled' },
  thumbsDown: { thumb: 'down', index: 'curled', middle: 'curled', ring: 'curled', pinky: 'curled' },
  oneFinger: { thumb: 'tucked', index: 'extended', middle: 'curled', ring: 'curled', pinky: 'curled' },
  twoFingers: { thumb: 'tucked', index: 'extended', middle: 'extended', ring: 'curled', pinky: 'curled' },
  halfClosed: { thumb: 'tucked', index: 'half', middle: 'half', ring: 'half', pinky: 'half' },
  fourFingers: { thumb: 'folded', index: 'extended', middle: 'extended', ring: 'extended', pinky: 'extended' },
}
