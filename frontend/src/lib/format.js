export function formatNumber(value, digits = 0) {
  return value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

export function formatPower(watts) {
  return watts >= 1000 ? `${formatNumber(watts / 1000, 2)} kW` : `${formatNumber(watts, 1)} W`
}

export function formatEnergy(kwh) {
  return kwh >= 1 ? `${formatNumber(kwh, 2)} kWh` : `${formatNumber(kwh * 1000, 1)} Wh`
}

export function formatTime(isoTimestamp) {
  return new Date(isoTimestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

/** "living_room" -> "Living room" */
export function humanize(snakeCase) {
  const words = snakeCase.replaceAll('_', ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

/** Valid value range for a command, as advertised by the backend's supported_commands. */
export function commandRange(device, action, fallback = { min: 0, max: 100 }) {
  const descriptor = device.supported_commands.find((command) => command.action === action)
  return {
    min: descriptor?.value?.minimum ?? fallback.min,
    max: descriptor?.value?.maximum ?? fallback.max,
  }
}

const STATE_FIELDS = {
  is_on: { label: 'power', format: (on) => (on ? 'on' : 'off') },
  is_locked: { label: 'lock', format: (locked) => (locked ? 'locked' : 'unlocked') },
  brightness: { label: 'brightness', format: (v) => `${v}%` },
  speed: { label: 'speed', format: (v) => `${v}%` },
  target_temperature_c: { label: 'target', format: (v) => `${v} °C` },
}

/** Human-readable diff between two device states, e.g. "brightness 100% → 70%". */
export function describeStateChange(previous, next) {
  const changes = Object.keys(next)
    .filter((key) => previous[key] !== next[key])
    .map((key) => {
      const field = STATE_FIELDS[key] ?? { label: key, format: String }
      return `${field.label} ${field.format(previous[key])} → ${field.format(next[key])}`
    })
  return changes.length ? changes.join(', ') : 'no change'
}
