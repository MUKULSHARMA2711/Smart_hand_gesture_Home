import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { createAdjustmentController } from '../gestures/adjustment'
import { createDoorUnlockController } from '../gestures/doorUnlock'
import { routePinch } from '../gestures/pinchRouting'
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
export function useGestureControl({ devices, onDevicesChanged, connected = true }) {
  const [config, setConfig] = useState(DEFAULT_CONFIG)
  const [configError, setConfigError] = useState(null)
  const [events, setEvents] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [lastAction, setLastAction] = useState(null)
  const [adjustment, setAdjustment] = useState(null)
  const [doorUnlock, setDoorUnlock] = useState(null)

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

  // Load the backend's mapping and threshold; retry after a reconnect if it failed.
  const [configLoaded, setConfigLoaded] = useState(false)
  useEffect(() => {
    if (!connected || configLoaded) return undefined
    let cancelled = false
    api
      .getGestureConfig()
      .then((response) => {
        if (cancelled) return
        setConfig({
          confidenceThreshold: response.confidence_threshold,
          intents: Object.fromEntries(response.gestures.map(({ gesture, intent }) => [gesture, intent])),
          blockedActions: response.blocked_actions,
        })
        setConfigLoaded(true)
        setConfigError(null)
      })
      .catch((error) => !cancelled && setConfigError(error.message))
    refreshEvents()
    return () => {
      cancelled = true
    }
  }, [connected, configLoaded, refreshEvents])

  // Secure door unlock by double pinch: the first pinch on the door asks the backend to hold
  // an unlock; the second confirms it through the existing confirmation API.
  const unlock = useRef(null)
  if (unlock.current === null) {
    unlock.current = createDoorUnlockController({
      isDoorSelected: () =>
        devicesRef.current.find((device) => device.id === selectedIdRef.current)?.device_type === 'door_lock',
      requestUnlock: (confidence) =>
        api.sendGesture({ gesture: 'PINCH', intent: 'UNLOCK_DOOR', confidence, targetDeviceId: selectedIdRef.current }),
      decide: (confirmationId, decision) => api.decideConfirmation(confirmationId, decision),
      onChange: setDoorUnlock,
      onSettled: () => Promise.all([refreshEvents(), onDevicesChanged?.()]),
    })
  }

  const execute = useCallback(
    async ({ gesture, confidence }) => {
      if (unlock.current.gesture(gesture)) return
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

  // Pinch adjustment: previews on every move, one PINCH/ADJUST command on release.
  const adjuster = useRef(null)
  if (adjuster.current === null) {
    adjuster.current = createAdjustmentController({
      getDevice: () => devicesRef.current.find((device) => device.id === selectedIdRef.current) ?? null,
      onChange: (update) =>
        setAdjustment((current) =>
          update.status === 'adjusting' && current?.status === 'adjusting' && current.value === update.value
            ? current // unchanged preview: no re-render
            : { ...(update.deviceName === undefined ? current : {}), ...update },
        ),
      send: async ({ gesture, intent, value, confidence, targetDeviceId }) => {
        if (inFlight.current) {
          setAdjustment((current) => ({ ...current, status: 'failure', message: 'Another gesture command is still running.' }))
          return
        }
        inFlight.current = true
        const attempt = { gesture, intent, confidence, targetId: targetDeviceId, value, at: new Date().toISOString() }
        setLastAction({ ...attempt, status: 'pending' })
        try {
          const response = await api.sendGesture({ gesture, intent, confidence, targetDeviceId, value })
          setLastAction({ ...attempt, status: 'success', action: response.gesture_event.action })
          setAdjustment((current) => ({ ...current, status: 'success', value }))
        } catch (error) {
          setLastAction({ ...attempt, status: 'failure', action: null, message: error.message })
          setAdjustment((current) => ({ ...current, status: 'failure', message: error.message }))
        } finally {
          inFlight.current = false
          await Promise.all([refreshEvents(), onDevicesChanged?.()])
        }
      },
    })
  }
  // The selected device decides first: the door (or a pending unlock) gets the pinch, and only
  // the fan / AC go to the adjustment.
  const onPinch = useCallback((event) => {
    const device = devicesRef.current.find((d) => d.id === selectedIdRef.current) ?? null
    routePinch(event, { device, unlock: unlock.current, adjuster: adjuster.current })
  }, [])
  const cancelUnlock = useCallback((reason) => unlock.current.cancel(reason), [])

  // Expiry display, and fail closed when the page is left.
  useEffect(() => {
    if (doorUnlock?.status !== 'pending') return undefined
    const timer = setInterval(() => unlock.current.tick(), 1000)
    return () => clearInterval(timer)
  }, [doorUnlock?.status])
  useEffect(() => () => unlock.current.cancel('Cancelled: left the gesture page.'), [])

  return {
    config,
    configError,
    events,
    selectedId,
    setSelectedId: (id) => {
      if (id !== selectedIdRef.current) unlock.current.cancel('Cancelled: another device was selected.')
      setSelectedId(id)
    },
    lastAction,
    execute,
    adjustment,
    onPinch,
    doorUnlock,
    cancelUnlock,
  }
}
