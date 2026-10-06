import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { startPolling } from '../state/polling'

const POLL_INTERVAL_MS = 5000
const EVENT_LIMIT = 15

/**
 * Loads home state + recent events, polls for sensor updates, and executes commands.
 * After every command the state is re-fetched so the backend stays the source of truth.
 */
export function useHomeDashboard() {
  const [home, setHome] = useState(null)
  const [events, setEvents] = useState([])
  const [connectionError, setConnectionError] = useState(null)
  const [commandError, setCommandError] = useState(null)
  const [pendingDeviceId, setPendingDeviceId] = useState(null)
  const latestRequest = useRef(0)

  const refresh = useCallback(async () => {
    // Ignore responses from older requests (e.g. a poll that resolves after a command's refresh).
    const requestId = ++latestRequest.current
    try {
      const [state, recentEvents] = await Promise.all([api.getHomeState(), api.getEvents(EVENT_LIMIT)])
      if (requestId !== latestRequest.current) return
      setHome(state)
      setEvents(recentEvents)
      setConnectionError(null)
    } catch (error) {
      if (requestId === latestRequest.current) setConnectionError(error.message)
    }
  }, [])

  // Polls never overlap, and stop when the provider unmounts.
  useEffect(() => startPolling(refresh, POLL_INTERVAL_MS), [refresh])

  const sendCommand = useCallback(
    async (deviceId, action, value) => {
      setPendingDeviceId(deviceId)
      setCommandError(null)
      try {
        return await api.sendCommand(deviceId, action, value) // the backend's response on success
      } catch (error) {
        setCommandError(error.message)
        return null
      } finally {
        await refresh()
        setPendingDeviceId(null)
      }
    },
    [refresh],
  )

  const clearCommandError = useCallback(() => setCommandError(null), [])

  // Connected = the latest refresh succeeded. While disconnected, `home` is the last known state.
  const connected = Boolean(home) && !connectionError

  return { home, events, connected, connectionError, commandError, clearCommandError, pendingDeviceId, sendCommand, refresh }
}
