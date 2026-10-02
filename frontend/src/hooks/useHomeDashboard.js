import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'

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

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, POLL_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [refresh])

  const sendCommand = useCallback(
    async (deviceId, action, value) => {
      setPendingDeviceId(deviceId)
      setCommandError(null)
      try {
        await api.sendCommand(deviceId, action, value)
      } catch (error) {
        setCommandError(error.message)
      } finally {
        await refresh()
        setPendingDeviceId(null)
      }
    },
    [refresh],
  )

  const clearCommandError = useCallback(() => setCommandError(null), [])

  return { home, events, connectionError, commandError, clearCommandError, pendingDeviceId, sendCommand }
}
