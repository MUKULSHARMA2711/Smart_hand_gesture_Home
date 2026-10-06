/** Presentation helpers for AI agent action results. */

const VALUE_LABELS = {
  SET_BRIGHTNESS: (v) => ['brightness', `${v}%`],
  SET_SPEED: (v) => ['speed', `${v}%`],
  SET_TEMPERATURE: (v) => ['temperature', `${v} °C`],
}

const RESULT_LABELS = { TURN_ON: 'ON', TURN_OFF: 'OFF', LOCK_DOOR: 'LOCKED', UNLOCK_DOOR: 'UNLOCKED' }

const QUERY_LABELS = {
  GET_STATUS: 'status checked',
  GET_ENERGY: 'energy usage checked',
  GET_HISTORY: 'history checked',
  GET_PREDICTIONS: 'ML prediction checked',
  GET_ANOMALIES: 'energy anomalies checked',
}

export const STATUS_STYLES = {
  executed: { icon: '✓', label: 'Done', tone: 'text-emerald-700 dark:text-emerald-400' },
  answered: { icon: '✓', label: 'Answered', tone: 'text-sky-700 dark:text-sky-400' },
  rejected: { icon: '✗', label: 'Rejected', tone: 'text-red-700 dark:text-red-400' },
  failed: { icon: '✗', label: 'Failed', tone: 'text-red-700 dark:text-red-400' },
  awaiting_confirmation: { icon: '?', label: 'Waiting for confirmation', tone: 'text-amber-700 dark:text-amber-300' },
  cancelled: { icon: '–', label: 'Cancelled', tone: 'text-slate-500 dark:text-slate-400' },
}

/** Seconds left before a held unlock expires (0 when expired). The backend enforces it. */
export function confirmationSecondsLeft(confirmation, now = Date.now()) {
  if (!confirmation) return 0
  return Math.max(0, Math.ceil((new Date(confirmation.expires_at).getTime() - now) / 1000))
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

/**
 * What to show when an assistant request failed before producing a plan. AI outages are
 * reported as such, with a reminder that the rest of the home keeps working.
 */
export function describeAssistantError(turn) {
  switch (turn.errorCode) {
    case 'ai_unavailable':
      return {
        title: 'AI service is currently unavailable.',
        hint: 'Nothing was changed. Device controls, gestures and the dashboard still work.',
        reason: turn.errorReason ?? null,
      }
    case 'network_error':
      return { title: 'Cannot reach the IntelliHome backend.', hint: 'Nothing was changed.', reason: null }
    case 'timeout':
      return { title: 'The assistant did not answer in time.', hint: turn.transportError, reason: null }
    default:
      return { title: `Request failed: ${turn.transportError}`, hint: null, reason: null }
  }
}

/** "Living Room Fan → ON" → "Living Room Fan is now on", for speech. */
function spokenAction(result, deviceNames) {
  return describeAction(result, deviceNames)
    .replace(' → ', ' is now ')
    .replace(/\b(ON|OFF|LOCKED|UNLOCKED)\b/, (word) => word.toLowerCase())
}

/**
 * What the assistant says out loud. Built from the backend's actual results (executed,
 * rejected, failed, held), never from the planner's free text about device actions, so it
 * cannot claim a change that did not happen. Query answers and backend messages are spoken
 * as returned.
 */
export function spokenSummary(response, deviceNames = {}) {
  if (!response) return "Sorry, I couldn't reach the assistant. Nothing was changed."
  if (response.confirmation) return response.confirmation.prompt
  if (!response.plan_valid) return 'Sorry, I could not make a safe plan for that. Nothing was changed.'
  const actions = response.actions ?? []
  const executed = actions.filter((a) => a.status === 'executed' && a.device_id)
  const problems = actions.filter((a) => a.status === 'rejected' || a.status === 'failed')
  if (!executed.length && !problems.length) return response.reply // answers, cancellations, help
  const parts = []
  if (executed.length) parts.push(`Done. ${executed.map((a) => spokenAction(a, deviceNames)).join(', ')}.`)
  for (const action of problems.slice(0, 2)) {
    const name = deviceNames[action.device_id] ?? action.device_id ?? 'That request'
    parts.push(`${name} was not changed: ${action.reason ?? action.status}`)
  }
  return parts.join(' ')
}

const VOICE_LABELS = {
  off: 'Voice is off',
  wake: 'Listening for “Hey IntelliHome”',
  command: 'Listening for your request…',
  processing: 'Processing…',
  speaking: 'Speaking…',
  unsupported: 'Voice is not supported in this browser',
}

/** One status line for the voice panel, including the request's real progress. */
export function voiceStatusLabel(voice, lifecyclePhase) {
  if (voice.state === 'error') return voice.message ?? 'Voice stopped because of an error.'
  if (voice.state === 'processing') {
    if (lifecyclePhase === 'executing') return 'Executing…'
    if (lifecyclePhase === 'success') return 'Done'
    if (lifecyclePhase === 'error') return 'Something went wrong'
  }
  return VOICE_LABELS[voice.state] ?? voice.state
}
