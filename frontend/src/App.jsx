import { Suspense, lazy, useEffect, useState } from 'react'
import { API_BASE_URL } from './api/client'
import { useHomeDashboard } from './hooks/useHomeDashboard'
import { formatTime } from './lib/format'
import { AssistantPage } from './pages/AssistantPage'
import { DashboardPage } from './pages/DashboardPage'

const COMMAND_ERROR_TIMEOUT_MS = 6000

// Loaded on demand so the dashboard never downloads MediaPipe.
const GesturePage = lazy(() => import('./pages/GesturePage').then((module) => ({ default: module.GesturePage })))

const ROUTES = [
  { id: 'dashboard', hash: '#/', label: 'Dashboard', subtitle: 'Virtual IoT dashboard · simulated devices' },
  { id: 'gestures', hash: '#/gestures', label: 'Gesture control', subtitle: 'Hand gesture control · runs in your browser' },
  { id: 'assistant', hash: '#/assistant', label: 'AI assistant', subtitle: 'Natural-language control · validated actions' },
]

function useHashRoute() {
  const read = () => ROUTES.find((route) => route.hash === window.location.hash) ?? ROUTES[0]
  const [route, setRoute] = useState(read)
  useEffect(() => {
    const onHashChange = () => setRoute(read())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])
  return route
}

function ConnectionIndicator({ connected, updatedAt }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
      <span className={`h-2 w-2 rounded-full ${connected ? 'bg-emerald-500' : 'bg-red-500'}`} aria-hidden="true" />
      <span>{connected ? 'Live' : 'Disconnected'}</span>
      {updatedAt && <span className="hidden sm:inline">· updated {formatTime(updatedAt)}</span>}
    </div>
  )
}

function Navigation({ current }) {
  return (
    <nav aria-label="Main" className="mx-auto flex max-w-6xl gap-1 px-4">
      {ROUTES.map((route) => {
        const active = route.id === current.id
        return (
          <a
            key={route.id}
            href={route.hash}
            aria-current={active ? 'page' : undefined}
            className={`border-b-2 px-3 pt-1 pb-2.5 text-sm font-medium transition-colors ${
              active
                ? 'border-indigo-600 text-slate-900 dark:border-indigo-400 dark:text-white'
                : 'border-transparent text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
            }`}
          >
            {route.label}
          </a>
        )
      })}
    </nav>
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
  const route = useHashRoute()
  const dashboard = useHomeDashboard()
  const { home, connectionError, commandError, clearCommandError } = dashboard

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 pt-4 pb-3">
          <div>
            <h1 className="text-lg font-semibold">IntelliHome</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">{route.subtitle}</p>
          </div>
          <ConnectionIndicator connected={!connectionError && !!home} updatedAt={home?.timestamp} />
        </div>
        <Navigation current={route} />
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

        {home && route.id === 'dashboard' && (
          <DashboardPage
            home={home}
            events={dashboard.events}
            pendingDeviceId={dashboard.pendingDeviceId}
            sendCommand={dashboard.sendCommand}
          />
        )}
        {home && route.id === 'assistant' && (
          <AssistantPage home={home} events={dashboard.events} refreshHome={dashboard.refresh} />
        )}
        {home && route.id === 'gestures' && (
          <Suspense fallback={<p className="text-slate-500">Loading gesture control…</p>}>
            <GesturePage home={home} refreshHome={dashboard.refresh} />
          </Suspense>
        )}
      </main>

      {commandError && <CommandErrorToast message={commandError} onDismiss={clearCommandError} />}
    </div>
  )
}
