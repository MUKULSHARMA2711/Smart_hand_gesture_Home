/**
 * Floor plan of the miniature house (scene units ≈ metres). The house spans
 * x ∈ [-5, 5] and z ∈ [-3.5, 3.5]; the front (+z) and right (+x) walls are cut away.
 */
export const HOUSE = { minX: -5, maxX: 5, minZ: -3.5, maxZ: 3.5, wallHeight: 2.1, lowWall: 0.4, thickness: 0.12 }

export const ROOMS = [
  { id: 'living_room', label: 'Living Room', x: [-5, 1], z: [-3.5, 3.5], floor: '#0f1a2f', labelAt: [-4.7, 3.15] },
  { id: 'bedroom', label: 'Bedroom', x: [1, 5], z: [-3.5, 0.9], floor: '#121b33', labelAt: [1.9, -0.75] },
  { id: 'entrance', label: 'Entrance', x: [1, 5], z: [0.9, 3.5], floor: '#0d1628', labelAt: [3.4, 2.75] },
]

export const DOOR = { hingeX: 2.35, width: 1.15, height: 1.95, z: 3.5 }

/**
 * Where each device type lives. `target` is where command beams land, `ring` the
 * radius of the selection ring. Devices are placed by type (one per type in this home).
 */
export const ANCHORS = {
  light: { base: [-0.35, 0, 2.55], target: [-0.35, 1.72, 2.55], ring: 0.5, label: [-0.35, 2.35, 2.55] },
  fan: { base: [-4.15, 0, -2.7], target: [-4.15, 1.3, -2.7], ring: 0.6, label: [-4.15, 2.15, -2.7] },
  ac: { base: [3.0, 0, -2.9], target: [3.0, 1.62, -3.2], ring: 0.85, label: [3.0, 2.25, -3.2] },
  door_lock: { base: [2.92, 0, 3.5], target: [2.92, 1.0, 3.55], ring: 0.8, label: [2.92, 2.45, 3.5] },
}

export const ORB_POSITION = [-0.5, 4.5, -1.4]
export const GESTURE_ORIGIN = [6.8, 2.8, 4.8]

export function anchorFor(device) {
  return device ? ANCHORS[device.device_type] : undefined
}
