const STYLES = {
  idle: 'border-sky-400/20 text-sky-300',
  listening: 'border-sky-400/40 text-sky-200',
  thinking: 'border-cyan-300/50 text-cyan-200',
  planning: 'border-cyan-300/50 text-cyan-200',
  executing: 'border-cyan-200/70 text-cyan-100',
  success: 'border-emerald-400/50 text-emerald-300',
  error: 'border-red-400/50 text-red-300',
}

/** Text twin of the 3D AI core state, for screen readers and at-a-glance status. */
export function OrbStatus({ state, className = '' }) {
  return (
    <div
      role="status"
      className={`flex items-center gap-2 rounded-full border bg-slate-950/70 px-3 py-1 text-[11px] font-semibold tracking-[0.2em] uppercase backdrop-blur ${STYLES[state] ?? STYLES.idle} ${className}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full bg-current ${state !== 'idle' ? 'animate-pulse' : ''}`} aria-hidden="true" />
      AI core · {state}
    </div>
  )
}
