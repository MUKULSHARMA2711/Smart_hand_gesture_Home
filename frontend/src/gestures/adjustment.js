/**
 * Pinch-to-adjust, prepared but not wired to the camera yet (the five existing gestures and
 * the 0.6 s stabilizer are unchanged).
 *
 * Planned interaction: ONE_FINGER selects a device → PINCH enters adjustment → moving the
 * hand up/down only *previews* the value → releasing the pinch sends ONE command
 * (intent ADJUST, which the backend resolves to SET_SPEED for a fan, SET_TEMPERATURE for an
 * AC, SET_BRIGHTNESS for a light, and never to the door). Nothing is sent per frame.
 */

const ADJUSTABLE = {
  set_speed: { direction: 1, label: 'speed', unit: '%' }, // hand up → faster
  set_temperature: { direction: -1, label: 'target', unit: ' °C' }, // hand up → cooler
  set_brightness: { direction: 1, label: 'brightness', unit: '%' },
}

/** The adjustable value of a device, from the ranges the backend publishes, or null. */
export function adjustmentRange(device) {
  for (const command of device?.supported_commands ?? []) {
    const kind = ADJUSTABLE[command.action]
    if (kind && command.value) return { action: command.action, min: command.value.minimum, max: command.value.maximum, ...kind }
  }
  return null
}

function currentValue(device, range) {
  const state = device.state ?? {}
  if (range.action === 'set_speed') return state.speed
  if (range.action === 'set_temperature') return state.target_temperature_c
  return state.brightness
}

/**
 * Value previewed for a vertical hand position. `y` is MediaPipe's normalised image
 * coordinate (0 = top, 1 = bottom); moving the full `travel` covers the whole range.
 */
export function previewValue(range, startValue, startY, y, travel = 0.5) {
  const delta = ((startY - y) / travel) * (range.max - range.min) * range.direction
  return Math.min(range.max, Math.max(range.min, Math.round(startValue + delta)))
}

/**
 * One adjustment: begin on pinch, update on every frame (preview only), release once.
 * `release()` returns the single command to send, or null if nothing changed or it was
 * cancelled (hand lost).
 */
export function createAdjustment(device, startY) {
  const range = adjustmentRange(device)
  if (!range) return null
  const startValue = currentValue(device, range)
  let value = startValue
  let open = true
  return {
    range,
    update(y) {
      if (open) value = previewValue(range, startValue, startY, y)
      return value
    },
    cancel() {
      open = false
    },
    release() {
      if (!open) return null
      open = false
      return value === startValue ? null : { intent: 'ADJUST', value, targetDeviceId: device.id }
    },
  }
}
