/** Presentation helpers for AI agent action results. */

const VALUE_LABELS = {
  SET_BRIGHTNESS: (v) => ['brightness', `${v}%`],
  SET_SPEED: (v) => ['speed', `${v}%`],
  SET_TEMPERATURE: (v) => ['temperature', `${v} °C`],
}

const RESULT_LABELS = { TURN_ON: 'ON', TURN_OFF: 'OFF', LOCK_DOOR: 'LOCKED', UNLOCK_DOOR: 'UNLOCKED' }

const QUERY_LABELS = { GET_STATUS: 'status checked', GET_ENERGY: 'energy usage checked', GET_HISTORY: 'history checked' }

export const STATUS_STYLES = {
  executed: { icon: '✓', label: 'Done', tone: 'text-emerald-700 dark:text-emerald-400' },
  answered: { icon: '✓', label: 'Answered', tone: 'text-sky-700 dark:text-sky-400' },
  rejected: { icon: '✗', label: 'Rejected', tone: 'text-red-700 dark:text-red-400' },
  failed: { icon: '✗', label: 'Failed', tone: 'text-red-700 dark:text-red-400' },
}

/** "Living Room Fan → ON", "Living Room Fan speed → 70%", "Home status checked". */
export function describeAction(result, deviceNames = {}) {
  const name = result.device_id ? (deviceNames[result.device_id] ?? result.device_id) : null
  const intent = result.intent

  if (!intent) return 'Malformed action'
  if (QUERY_LABELS[intent]) return `${name ?? 'Home'} ${QUERY_LABELS[intent]}`
  if (VALUE_LABELS[intent]) {
    const [property, value] = VALUE_LABELS[intent](result.parameters?.value)
    return `${name ?? 'Unknown device'} ${property} → ${value}`
  }
  return `${name ?? 'Unknown device'} → ${RESULT_LABELS[intent] ?? intent}`
}

/** Final state of each device changed in an interaction, for the "Changed" line. */
export function changedDeviceStates(response) {
  const latest = {}
  for (const result of response.actions ?? []) {
    if (result.status === 'executed' && result.device_id && result.new_state) latest[result.device_id] = result.new_state
  }
  return (response.changed_devices ?? []).map((id) => ({ id, state: latest[id] }))
}
