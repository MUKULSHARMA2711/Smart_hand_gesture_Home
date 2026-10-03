import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { DEFAULT_CONFIDENCE_THRESHOLD, DEFAULT_GESTURE_INTENTS } from '../gestures/types'

const HISTORY_LIMIT = 15

const DEFAULT_CONFIG = {
  confidenceThreshold: DEFAULT_CONFIDENCE_THRESHOLD,
  intents: DEFAULT_GESTURE_INTENTS,
  blockedActions: [],
}

function nextDeviceId(devices, currentId) {
  if (!devices.length) return null
  const index = devices.findIndex((device) => device.id === currentId)
  return devices[(index + 1) % devices.length].id
}

/**
 * Gesture → intent → backend. Owns the explicitly selected target device (a stand-in
 * for future AI targeting), the last action result and the gesture history.
 * The backend decides which device action an intent becomes.
 */
export function useGestureControl({ devices, onDevicesChanged }) {
  const [config, setConfig] = useState(DEFAULT_CONFIG)
  const [configError, setConfigError] = useState(null)
  const [events, setEvents] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [lastAction, setLastAction] = useState(null)

  const selectedIdRef = useRef(selectedId)
  const devicesRef = useRef(devices)
  const inFlight = useRef(false)
  useEffect(() => {
    selectedIdRef.current = selectedId
    devicesRef.current = devices
  }, [selectedId, devices])

  // Default to the first device once devices have loaded.
  useEffect(() => {
    if (!selectedId && devices.length) setSelectedId(devices[0].id)
  }, [devices, selectedId])

  const refreshEvents = useCallback(async () => {
    try {
      setEvents(await api.getGestureEvents(HISTORY_LIMIT))
    } catch {
      // Connection problems are surfaced by the dashboard's connection banner.
    }
  }, [])

  useEffect(() => {
    api
      .getGestureConfig()
      .then((response) =>
        setConfig({
          confidenceThreshold: response.confidence_threshold,
          intents: Object.fromEntries(response.gestures.map(({ gesture, intent }) => [gesture, intent])),
          blockedActions: response.blocked_actions,
        }),
      )
      .catch((error) => setConfigError(error.message))
    refreshEvents()
  }, [refreshEvents])

  const execute = useCallback(
    async ({ gesture, confidence }) => {
      const intent = config.intents[gesture]
      if (!intent || intent === 'NONE' || inFlight.current) return

      let targetId = selectedIdRef.current
      if (intent === 'SELECT') {
        targetId = nextDeviceId(devicesRef.current, targetId)
        selectedIdRef.current = targetId
        setSelectedId(targetId)
      }
      if (!targetId) return

      inFlight.current = true
      const attempt = { gesture, intent, confidence, targetId, at: new Date().toISOString() }
      setLastAction({ ...attempt, status: 'pending' })
      try {
        const response = await api.sendGesture({ gesture, intent, confidence, targetDeviceId: targetId })
        setLastAction({ ...attempt, status: 'success', action: response.gesture_event.action })
      } catch (error) {
        setLastAction({ ...attempt, status: 'failure', action: null, message: error.message })
      } finally {
        inFlight.current = false
        await Promise.all([refreshEvents(), onDevicesChanged?.()])
      }
    },
    [config.intents, refreshEvents, onDevicesChanged],
  )

  return { config, configError, events, selectedId, setSelectedId, lastAction, execute }
}
