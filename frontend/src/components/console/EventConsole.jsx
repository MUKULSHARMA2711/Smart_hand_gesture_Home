import { AnimatePresence, motion } from 'motion/react'

/** Compact 24-hour timestamp for the console, e.g. 04:09:27. */
const consoleTime = (iso) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })

const TAG_STYLES = {
  GESTURE: 'text-violet-300',
  'AI AGENT': 'text-cyan-300',
  DASHBOARD: 'text-slate-300',
  AUTOMATION: 'text-amber-300',
  MQTT: 'text-slate-400',
}
const TONE_STYLES = { ok: 'text-slate-200', warning: 'text-amber-200', error: 'text-red-300' }

/** Terminal-style stream of real activity (device events, gestures, AI requests). */
export function EventConsole({ entries, limit = 12, title = 'Live event stream', emptyText = 'Waiting for activity…', className = '' }) {
  const visible = entries.slice(0, limit)
  return (
    <section className={`console-panel ${className}`} aria-label={title}>
      <header className="flex items-center justify-between border-b border-cyan-500/10 px-4 py-2.5">
        <h2 className="flex items-center gap-2 text-[11px] font-semibold tracking-[0.2em] text-cyan-200/80 uppercase">
          <span className="console-live-dot" aria-hidden="true" />
          {title}
        </h2>
        <span className="font-mono text-[10px] text-slate-500">{entries.length} events</span>
      </header>
      {visible.length === 0 ? (
        <p className="px-4 py-6 font-mono text-xs text-slate-500">{emptyText}</p>
      ) : (
        <ol className="divide-y divide-white/[0.03] font-mono text-xs" aria-live="polite">
          <AnimatePresence initial={false}>
            {visible.map((entry) => (
              <motion.li
                key={entry.id}
                layout
                initial={{ opacity: 0, x: -10, backgroundColor: 'rgba(56,189,248,0.10)' }}
                animate={{ opacity: 1, x: 0, backgroundColor: 'rgba(56,189,248,0)' }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.4 }}
                className="grid grid-cols-[4.25rem_5.75rem_1fr] gap-x-3 px-4 py-2"
              >
                <span className="text-slate-500 tabular-nums">{consoleTime(entry.timestamp)}</span>
                <span className={`font-semibold ${TAG_STYLES[entry.tag] ?? 'text-slate-300'}`}>{entry.tag}</span>
                <span className="min-w-0">
                  <span className={`block break-words ${TONE_STYLES[entry.tone] ?? TONE_STYLES.ok}`}>
                    {entry.text}
                  </span>
                  {entry.detail && <span className="block truncate text-[11px] text-slate-500">{entry.detail}</span>}
                </span>
              </motion.li>
            ))}
          </AnimatePresence>
        </ol>
      )}
    </section>
  )
}
