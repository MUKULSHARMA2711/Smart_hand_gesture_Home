import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { useReducedMotion } from 'motion/react'
import { useAssistant } from '../hooks/useAssistant'
import {
  ACTION_STAGGER_MS,
  BEAM_TRAVEL_MS,
  executionDuration,
  IDLE,
  lifecycleReducer,
  orbState,
  PLANNING_MS,
  RESULT_HOLD_MS,
  visualizedActions,
} from './aiLifecycle'
import { useCommandFx } from './CommandFxContext'
import { useHomeData } from './HomeDataContext'

/**
 * The AI assistant conversation plus the lifecycle that drives the AI core and
 * command beams. All results shown come from the backend response.
 *
 * While beams are in flight, a targeted device is displayed with the backend's own
 * `previous_state` for that action and switches to `new_state` when its beam lands,
 * so each action visibly arrives in order. Live polled state takes over afterwards.
 */
const AssistantContext = createContext(null)

export function AssistantProvider({ children }) {
  const { refresh, home } = useHomeData()
  const { emit } = useCommandFx()
  const reducedMotion = useReducedMotion()
  const [lifecycle, dispatch] = useReducer(lifecycleReducer, IDLE)
  const [heldStates, setHeldStates] = useState({})
  const [gestureActive, setGestureActive] = useState(false)
  const [contextAtSend, setContextAtSend] = useState(null)
  const timers = useRef([])
  const homeRef = useRef(home)
  homeRef.current = home

  const schedule = useCallback((fn, ms) => {
    timers.current.push(setTimeout(fn, ms))
  }, [])
  const clearTimers = useCallback(() => {
    timers.current.forEach(clearTimeout)
    timers.current = []
  }, [])
  useEffect(() => clearTimers, [clearTimers])

  const onSend = useCallback(
    (text) => {
      clearTimers()
      setHeldStates({})
      setContextAtSend(homeRef.current)
      dispatch({ type: 'send', request: text })
    },
    [clearTimers],
  )

  const onResponse = useCallback(
    (response) => {
      dispatch({ type: 'response', response })
      const actions = visualizedActions(response)
      const executed = actions.filter((a) => a.status === 'executed' && a.previous_state && a.new_state)

      if (reducedMotion) {
        refresh()
        dispatch({ type: 'execute' })
        dispatch({ type: 'complete' })
        schedule(() => dispatch({ type: 'reset' }), RESULT_HOLD_MS)
        return
      }

      // Hold targeted devices at their real previous state until their beam lands.
      const initialHolds = {}
      for (const action of executed) if (!(action.device_id in initialHolds)) initialHolds[action.device_id] = action.previous_state
      setHeldStates(initialHolds)
      refresh()

      schedule(() => {
        dispatch({ type: 'execute' })
        actions.forEach((action, i) => {
          emit({ source: 'ai_agent', deviceId: action.device_id, status: action.status, delayMs: i * ACTION_STAGGER_MS })
          if (action.status !== 'executed') return
          const isLastForDevice = !actions.slice(i + 1).some((a) => a.device_id === action.device_id && a.status === 'executed')
          schedule(() => {
            setHeldStates((holds) => {
              const next = { ...holds }
              if (isLastForDevice) delete next[action.device_id]
              else next[action.device_id] = action.new_state
              return next
            })
          }, i * ACTION_STAGGER_MS + BEAM_TRAVEL_MS)
        })
        const duration = executionDuration(response)
        schedule(() => {
          setHeldStates({})
          dispatch({ type: 'complete' })
        }, duration)
        schedule(() => dispatch({ type: 'reset' }), duration + RESULT_HOLD_MS)
      }, PLANNING_MS)
    },
    [emit, refresh, schedule, reducedMotion],
  )

  const onError = useCallback(
    (message) => {
      dispatch({ type: 'transport_error', message })
      schedule(() => dispatch({ type: 'reset' }), RESULT_HOLD_MS)
    },
    [schedule],
  )

  const assistant = useAssistant({ onSend, onResponse, onError })
  const setTyping = useCallback((typing) => dispatch({ type: typing ? 'focus' : 'blur' }), [])

  const value = useMemo(
    () => ({
      ...assistant,
      lifecycle,
      contextAtSend,
      heldStates,
      setTyping,
      gestureActive,
      setGestureActive,
      orbState: orbState(lifecycle.phase, { gestureActive }),
    }),
    [assistant, lifecycle, contextAtSend, heldStates, setTyping, gestureActive],
  )
  return <AssistantContext.Provider value={value}>{children}</AssistantContext.Provider>
}

export function useAssistantContext() {
  return useContext(AssistantContext)
}

/** Devices as the 3D scene should show them: live backend state, except for beams in flight. */
export function useDisplayDevices() {
  const { home } = useHomeData()
  const { heldStates } = useAssistantContext()
  return useMemo(
    () => (home?.devices ?? []).map((device) => (heldStates[device.id] ? { ...device, state: heldStates[device.id] } : device)),
    [home, heldStates],
  )
}
