/**
 * Frontend lifecycle of one AI request, used to drive the AI core and the pipeline UI.
 *
 *   idle ─focus→ listening ─send→ thinking ─response→ planning ─execute→ executing ─complete→ success | error
 *
 * "thinking" covers the real wait for the backend. "planning" and "executing" pace the
 * presentation of the *returned* plan and results; they never invent results.
 */

export const IDLE = Object.freeze({ phase: 'idle', request: null, response: null, error: null })

// Presentation pacing (ms).
export const PLANNING_MS = 700
export const ACTION_STAGGER_MS = 550
export const BEAM_TRAVEL_MS = 900
export const RESULT_HOLD_MS = 2200

export function executedCount(response) {
  return (response?.actions ?? []).filter((action) => action.status === 'executed').length
}

const NOT_SENT = new Set(['answered', 'awaiting_confirmation', 'cancelled'])

/** Animated actions: results that reached for a device (executed, rejected or failed). A held
 * or cancelled unlock sends nothing, so it gets no command beam. */
export function visualizedActions(response) {
  return (response?.actions ?? []).filter((action) => action.device_id && !NOT_SENT.has(action.status))
}

export function resultPhase(response) {
  if (!response || !response.plan_valid || (response.errors ?? []).length) return 'error'
  const actions = response.actions ?? []
  if (actions.some((a) => a.status === 'failed')) return 'error'
  const succeeded = actions.some((a) => ['executed', 'answered', 'awaiting_confirmation', 'cancelled'].includes(a.status))
  if (actions.length && !succeeded) return 'error' // everything was rejected
  return 'success'
}

export function lifecycleReducer(state, event) {
  switch (event.type) {
    case 'focus':
      return state.phase === 'idle' ? { ...state, phase: 'listening' } : state
    case 'blur':
      return state.phase === 'listening' ? IDLE : state
    case 'send':
      return { phase: 'thinking', request: event.request, response: null, error: null }
    case 'response':
      return state.phase === 'thinking' ? { ...state, phase: 'planning', response: event.response } : state
    case 'execute':
      if (state.phase !== 'planning') return state
      return { ...state, phase: visualizedActions(state.response).length ? 'executing' : resultPhase(state.response) }
    case 'complete':
      return state.phase === 'executing' ? { ...state, phase: resultPhase(state.response) } : state
    case 'transport_error':
      return { ...state, phase: 'error', error: event.message }
    case 'reset':
      return state.phase === 'success' || state.phase === 'error' ? IDLE : state
    default:
      return state
  }
}

/** How long the executing phase lasts so every action's beam can land. */
export function executionDuration(response) {
  const count = visualizedActions(response).length
  return count ? (count - 1) * ACTION_STAGGER_MS + BEAM_TRAVEL_MS + 300 : 0
}

/** The AI core's state: the assistant lifecycle wins; an active gesture camera means "listening". */
export function orbState(lifecyclePhase, { gestureActive = false } = {}) {
  if (lifecyclePhase && lifecyclePhase !== 'idle') return lifecyclePhase
  return gestureActive ? 'listening' : 'idle'
}
