import { useEffect } from 'react'
import { API_BASE_URL } from './api/client'
import { DeviceCard } from './components/DeviceCard'
import { EnvironmentPanel } from './components/EnvironmentPanel'
import { EventLog } from './components/EventLog'
import { useHomeDashboard } from './hooks/useHomeDashboard'
import { formatTime } from './lib/format'

const COMMAND_ERROR_TIMEOUT_MS = 6000

function ConnectionIndicator({ connected, updatedAt }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
      <span className={`h-2 w-2 rounded-full ${connected ? 'bg-emerald-500' : 'bg-red-500'}`} aria-hidden="true" />
      <span>{connected ? 'Live' : 'Disconnected'}</span>
      {updatedAt && <span className="hidden sm:inline">· updated {formatTime(updatedAt)}</span>}
    </div>
  )
}

function CommandErrorToast({ message, onDismiss }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, COMMAND_ERROR_TIMEOUT_MS)
    return () => clearTimeout(timer)
  }, [message, onDismiss])

  return (
    <div
      role="alert"
      className="fixed inset-x-4 bottom-4 z-10 mx-auto flex max-w-lg items-start gap-3 rounded-xl border border-red-200 bg-white p-4 text-sm shadow-lg dark:border-red-900 dark:bg-slate-900"
    >
      <span className="font-semibold text-red-700 dark:text-red-400">Command failed</span>
      <span className="flex-1 text-slate-700 dark:text-slate-300">{message}</span>
      <button type="button" onClick={onDismiss} className="text-slate-500 hover:text-slate-900 dark:hover:text-white" aria-label="Dismiss">
        ✕
      </button>
    </div>
  )
}

export default function App() {
  const { home, events, connectionError, commandError, clearCommandError, pendingDeviceId, sendCommand } =
    useHomeDashboard()
  const deviceNames = Object.fromEntries((home?.devices ?? []).map((device) => [device.id, device.name]))

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-4">
          <div>
            <h1 className="text-lg font-semibold">IntelliHome</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Virtual IoT dashboard · simulated devices</p>
          </div>
          <ConnectionIndicator connected={!connectionError && !!home} updatedAt={home?.timestamp} />
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-8 px-4 py-6">
        {connectionError && (
          <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
            <p className="font-semibold">{connectionError}</p>
            <p className="mt-1">
              Start the backend with <code className="font-mono">uvicorn app.main:app --reload</code> in{' '}
              <code className="font-mono">backend/</code>. Expected API at <code className="font-mono">{API_BASE_URL}</code>.
            </p>
          </div>
        )}

        {!home && !connectionError && <p className="text-slate-500">Loading home state…</p>}

        {home && (
          <>
            <EnvironmentPanel environment={home.environment} energy={home.energy} />

            <section aria-labelledby="devices-heading">
              <h2 id="devices-heading" className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase dark:text-slate-400">
                Devices
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {home.devices.map((device) => (
                  <DeviceCard
                    key={device.id}
                    device={device}
                    busy={pendingDeviceId === device.id}
                    onCommand={(action, value) => sendCommand(device.id, action, value)}
                  />
                ))}
              </div>
            </section>

            <EventLog events={events} deviceNames={deviceNames} />
          </>
        )}
      </main>

      {commandError && <CommandErrorToast message={commandError} onDismiss={clearCommandError} />}
    </div>
  )
}
