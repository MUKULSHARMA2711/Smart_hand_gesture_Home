import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import { useHomeDashboard } from '../hooks/useHomeDashboard'
import { useCommandFx } from './CommandFxContext'
import { appendSample } from './energyHistory'

/**
 * Single source of backend data for every page and the 3D scene:
 * home state + device events (polled), gesture events and AI history (refreshed with
 * them), and a power history sampled in this browser from the same polls.
 */
const HomeDataContext = createContext(null)

export function HomeDataProvider({ children }) {
  const dashboard = useHomeDashboard()
  const { emit } = useCommandFx()
  const [gestureEvents, setGestureEvents] = useState([])
  const [aiInteractions, setAiInteractions] = useState([])
  const [energyHistory, setEnergyHistory] = useState([])

  useEffect(() => {
    if (dashboard.home) setEnergyHistory((history) => appendSample(history, dashboard.home))
  }, [dashboard.home])

  // Device events are re-fetched on every poll and after every command; follow them.
  useEffect(() => {
    let cancelled = false
    Promise.allSettled([api.getGestureEvents(30), api.getAIHistory(30)]).then(([gestures, ai]) => {
      if (cancelled) return
      if (gestures.status === 'fulfilled') setGestureEvents(gestures.value)
      if (ai.status === 'fulfilled') setAiInteractions(ai.value)
    })
    return () => {
      cancelled = true
    }
  }, [dashboard.events])

  const { sendCommand: rawSendCommand } = dashboard
  const sendCommand = useCallback(
    async (deviceId, action, value) => {
      const response = await rawSendCommand(deviceId, action, value)
      if (response) emit({ source: 'frontend', deviceId, status: 'executed' })
      return response
    },
    [rawSendCommand, emit],
  )

  const deviceNames = useMemo(
    () => Object.fromEntries((dashboard.home?.devices ?? []).map((device) => [device.id, device.name])),
    [dashboard.home],
  )

  const value = useMemo(
    () => ({ ...dashboard, sendCommand, gestureEvents, aiInteractions, energyHistory, deviceNames }),
    [dashboard, sendCommand, gestureEvents, aiInteractions, energyHistory, deviceNames],
  )
  return <HomeDataContext.Provider value={value}>{children}</HomeDataContext.Provider>
}

export function useHomeData() {
  return useContext(HomeDataContext)
}
