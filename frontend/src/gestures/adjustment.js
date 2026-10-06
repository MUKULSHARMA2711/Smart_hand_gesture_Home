/**
 * Pinch-to-adjust (the five existing gestures and the 0.6 s stabilizer are unchanged).
 *
 * ONE_FINGER selects a device → PINCH enters adjustment → moving the hand up/down only
 * *previews* the value → releasing the pinch sends ONE command (gesture PINCH, intent
 * ADJUST, which the backend resolves to SET_SPEED for a fan, SET_TEMPERATURE for an AC,
 * SET_BRIGHTNESS for a light, and never to the door). Nothing is sent per frame.
 */

const ADJUSTABLE = {
  set_speed: { direction: 1, label: 'speed', unit: '%', title: 'Fan Speed', up: 'faster', down: 'slower' },
  set_temperature: { direction: -1, label: 'target', unit: ' °C', title: 'AC Temperature', up: 'cooler', down: 'warmer' },
  set_brightness: { direction: 1, label: 'brightness', unit: '%', title: 'Brightness', up: 'brighter', down: 'dimmer' },
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

/**
 * Turns pinch events into adjustment state for the UI and at most ONE command per pinch.
 * `send(command)` is only ever called on release, with the final value; every `move` just
 * updates the preview. The device comes from backend state (`getDevice`), so the start
 * value is the confirmed one, and the door (no adjustable value) never enters adjustment.
 */
export function createAdjustmentController({ getDevice, send, onChange = () => {} }) {
  let active = null // { adjustment, device, confidence }

  const emit = (state) => onChange(state)

  return {
    get active() {
      return active !== null
    },
    handle(event) {
      if (event.type === 'start') {
        const device = getDevice()
        const adjustment = device ? createAdjustment(device, event.y) : null
        if (!adjustment) {
          active = null
          emit({ status: 'unsupported', deviceName: device?.name ?? null })
          return
        }
        active = { adjustment, device, confidence: event.confidence }
        const value = adjustment.update(event.y)
        emit({ status: 'adjusting', deviceId: device.id, deviceName: device.name, range: adjustment.range, startValue: value, value })
        return
      }
      if (!active) return
      if (event.type === 'move') {
        const value = active.adjustment.update(event.y)
        emit({ status: 'adjusting', value })
        return
      }
      const { adjustment, device } = active
      active = null
      if (event.type === 'cancel') {
        adjustment.cancel()
        emit({ status: 'cancelled' })
        return
      }
      // end: release → exactly one command, or none if the value did not change
      const command = adjustment.release()
      if (!command) {
        emit({ status: 'unchanged' })
        return
      }
      emit({ status: 'sending', value: command.value })
      send({ ...command, gesture: 'PINCH', confidence: event.confidence, deviceName: device.name })
    },
    cancel() {
      if (active) {
        active.adjustment.cancel()
        active = null
      }
    },
  }
}

/** "60%", "22 °C". */
export function formatAdjustment(range, value) {
  return value == null || !range ? '—' : `${value}${range.unit}`
}
