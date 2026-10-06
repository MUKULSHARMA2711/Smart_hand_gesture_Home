import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'

/**
 * Short-lived visual effects for commands that *actually happened*.
 *
 * Effects are only emitted from real API responses (AI results, gesture results,
 * dashboard commands). An effect never changes device state; it is decoration.
 */

export const FX_LIFETIME_MS = 2600

const CommandFxContext = createContext({ effects: [], emit: () => {} })

export function CommandFxProvider({ children }) {
  const [effects, setEffects] = useState([])
  const timers = useRef(new Set())

  const emit = useCallback(({ delayMs = 0, ...fx }) => {
    const id = `${performance.now().toFixed(3)}-${Math.random().toString(36).slice(2, 8)}`
    const effect = { id, startAt: performance.now() + delayMs, ...fx }
    setEffects((list) => [...list, effect])
    const timer = setTimeout(() => {
      timers.current.delete(timer)
      setEffects((list) => list.filter((e) => e.id !== id))
    }, delayMs + FX_LIFETIME_MS)
    timers.current.add(timer)
  }, [])

  useEffect(() => {
    const pending = timers.current
    return () => pending.forEach(clearTimeout)
  }, [])

  const value = useMemo(() => ({ effects, emit }), [effects, emit])
  return <CommandFxContext.Provider value={value}>{children}</CommandFxContext.Provider>
}

export function useCommandFx() {
  return useContext(CommandFxContext)
}
