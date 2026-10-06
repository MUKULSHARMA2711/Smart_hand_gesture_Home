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
  const [ml, setMl] = useState({ status: null, prediction: null, anomalies: null, error: null })

  useEffect(() => {
    if (dashboard.home) setEnergyHistory((history) => appendSample(history, dashboard.home))
  }, [dashboard.home])

  // Device events are re-fetched on every poll and after every command; follow them.
  useEffect(() => {
    let cancelled = false
    Promise.allSettled([api.getGestureEvents(30), api.getAIHistory(30), api.predict(), api.getAnomalies()]).then(
      ([gestures, ai, prediction, anomalies]) => {
        if (cancelled) return
        if (gestures.status === 'fulfilled') setGestureEvents(gestures.value)
        if (ai.status === 'fulfilled') setAiInteractions(ai.value)
        // ML results are always the backend's; nothing is estimated in the browser.
        setMl((current) => ({
          ...current,
          prediction: prediction.status === 'fulfilled' ? prediction.value : null,
          anomalies: anomalies.status === 'fulfilled' ? anomalies.value : null,
          error: [prediction, anomalies].find((result) => result.status === 'rejected')?.reason.message ?? null,
        }))
      },
    )
    return () => {
      cancelled = true
    }
  }, [dashboard.events])

  // Model metadata: loaded once connected, and retried after a reconnect if it failed.
  const { connected } = dashboard
  const haveMlStatus = ml.status != null
  useEffect(() => {
    if (!connected || haveMlStatus) return undefined
    let cancelled = false
    api
      .getMLStatus()
      .then((status) => !cancelled && setMl((current) => ({ ...current, status })))
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [connected, haveMlStatus])

  const { sendCommand: rawSendCommand, refresh } = dashboard

  /** Submit a power reading for anomaly detection, then refresh so events and alerts update. */
  const checkPowerReading = useCallback(
    async (deviceId, powerW) => {
      const result = await api.checkPowerReading(deviceId, powerW)
      await refresh()
      return result
    },
    [refresh],
  )
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
    () => ({ ...dashboard, sendCommand, gestureEvents, aiInteractions, energyHistory, deviceNames, ml, checkPowerReading }),
    [dashboard, sendCommand, gestureEvents, aiInteractions, energyHistory, deviceNames, ml, checkPowerReading],
  )
  return <HomeDataContext.Provider value={value}>{children}</HomeDataContext.Provider>
}

export function useHomeData() {
  return useContext(HomeDataContext)
}
