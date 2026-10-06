import { Suspense, lazy, useEffect, useState } from 'react'
import { AnimatePresence, MotionConfig, motion } from 'motion/react'
import { API_BASE_URL } from './api/client'
import { formatTime } from './lib/format'
import { ActivityPage } from './pages/ActivityPage'
import { AssistantPage } from './pages/AssistantPage'
import { EnergyPage } from './pages/EnergyPage'
import { HomePage } from './pages/HomePage'
import { AssistantProvider } from './state/AssistantContext'
import { CommandFxProvider } from './state/CommandFxContext'
import { HomeDataProvider, useHomeData } from './state/HomeDataContext'

const COMMAND_ERROR_TIMEOUT_MS = 6000

// Loaded on demand so other pages never download MediaPipe.
const GesturePage = lazy(() => import('./pages/GesturePage').then((module) => ({ default: module.GesturePage })))

const ROUTES = [
  { id: 'home', hash: '#/', label: 'Home', subtitle: 'Command center · live digital twin', Page: HomePage },
  { id: 'gestures', hash: '#/gestures', label: 'Gesture', subtitle: 'Hand gesture control · runs in your browser', Page: GesturePage },
  { id: 'assistant', hash: '#/assistant', label: 'AI assistant', subtitle: 'Natural-language control · validated actions', Page: AssistantPage },
  { id: 'energy', hash: '#/energy', label: 'Energy', subtitle: 'Power draw · sampled live', Page: EnergyPage },
  { id: 'activity', hash: '#/activity', label: 'Activity', subtitle: 'Device, gesture and AI activity', Page: ActivityPage },
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
    <div className="flex items-center gap-2 text-xs text-slate-400">
      <span className={`h-2 w-2 rounded-full ${connected ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-red-500'}`} aria-hidden="true" />
      <span className="font-semibold tracking-widest uppercase">{connected ? 'Live' : 'Offline'}</span>
      {updatedAt && <span className="hidden tabular-nums sm:inline">· {formatTime(updatedAt)}</span>}
    </div>
  )
}

function Navigation({ current }) {
  return (
    <nav aria-label="Main" className="flex flex-wrap gap-1 rounded-full border border-white/5 bg-slate-900/60 p-1 backdrop-blur">
      {ROUTES.map((route) => {
        const active = route.id === current.id
        return (
          <a
            key={route.id}
            href={route.hash}
            aria-current={active ? 'page' : undefined}
            className={`relative rounded-full px-4 py-1.5 text-[11px] font-semibold tracking-[0.18em] uppercase transition-colors ${
              active ? 'text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {active && (
              <motion.span
                layoutId="nav-active"
                className="absolute inset-0 rounded-full border border-cyan-400/40 bg-cyan-400/10 shadow-[0_0_18px_-4px_rgba(34,211,238,0.6)]"
                transition={{ type: 'spring', stiffness: 380, damping: 32 }}
              />
            )}
            <span className="relative">{route.label}</span>
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
    <div role="alert" className="fixed inset-x-4 bottom-4 z-30 mx-auto flex max-w-lg items-start gap-3 rounded-xl border border-red-900 bg-slate-950/95 p-4 text-sm shadow-lg backdrop-blur">
      <span className="font-semibold text-red-400">Command failed</span>
      <span className="flex-1 text-slate-300">{message}</span>
      <button type="button" onClick={onDismiss} className="text-slate-400 hover:text-white" aria-label="Dismiss">
        ✕
      </button>
    </div>
  )
}

function Shell() {
  const route = useHashRoute()
  const { home, connectionError, commandError, clearCommandError } = useHomeData()
  const { Page } = route

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-white/5 bg-slate-950/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-3 px-6 py-3">
          <div className="flex items-center gap-3">
            <span className="brand-mark" aria-hidden="true" />
            <div>
              <h1 className="text-base font-semibold tracking-wide text-white">IntelliHome</h1>
              <p className="text-[11px] text-slate-400">{route.subtitle}</p>
            </div>
          </div>
          <Navigation current={route} />
          <ConnectionIndicator connected={!connectionError && Boolean(home)} updatedAt={home?.timestamp} />
        </div>
      </header>

      <main className="mx-auto max-w-[1440px] px-6 py-6">
        {connectionError && (
          <div role="alert" className="mb-6 rounded-xl border border-red-900 bg-red-950/60 p-4 text-sm text-red-200">
            <p className="font-semibold">{home ? 'Connection to the backend lost.' : connectionError}</p>
            {home ? (
              <p className="mt-1">
                {connectionError} Showing the last known state from {formatTime(home.timestamp)}; it is not live and
                commands will fail until the backend is back. Reconnecting automatically.
              </p>
            ) : (
              <p className="mt-1">
                Start the backend with <code className="font-mono">uvicorn app.main:app --reload</code> in{' '}
                <code className="font-mono">backend/</code>. Expected API at <code className="font-mono">{API_BASE_URL}</code>.
                Retrying automatically.
              </p>
            )}
          </div>
        )}

        {!home && !connectionError && <p className="text-slate-500">Loading home state…</p>}

        {home && (
          <AnimatePresence mode="wait">
            <motion.div
              key={route.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
            >
              <Suspense fallback={<p className="text-slate-500">Loading…</p>}>
                <Page />
              </Suspense>
            </motion.div>
          </AnimatePresence>
        )}
      </main>

      {commandError && <CommandErrorToast message={commandError} onDismiss={clearCommandError} />}
    </div>
  )
}

export default function App() {
  return (
    <MotionConfig reducedMotion="user">
      <CommandFxProvider>
        <HomeDataProvider>
          <AssistantProvider>
            <Shell />
          </AssistantProvider>
        </HomeDataProvider>
      </CommandFxProvider>
    </MotionConfig>
  )
}
