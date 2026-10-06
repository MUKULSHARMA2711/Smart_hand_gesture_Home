import { homeHealth } from '../state/homeHealth'
import { Panel } from './Panel'

const STATUS = {
  ok: { icon: '✓', className: 'text-emerald-400' },
  warning: { icon: '!', className: 'text-amber-400' },
}

/** Verifiable checks only; no invented score (see state/homeHealth.js). */
export function HomeHealthPanel({ home, anomalies = null }) {
  const health = homeHealth(home, Date.now(), anomalies)
  const fraction = health.total ? health.passed / health.total : 0
  const circumference = 2 * Math.PI * 22

  return (
    <Panel title="Home status">
      <div className="flex items-center gap-4">
        <svg viewBox="0 0 56 56" className="h-16 w-16 shrink-0" aria-hidden="true">
          <circle cx="28" cy="28" r="22" fill="none" stroke="rgba(148,163,184,0.15)" strokeWidth="5" />
          <circle
            cx="28"
            cy="28"
            r="22"
            fill="none"
            stroke={fraction === 1 ? '#34d399' : '#fbbf24'}
            strokeWidth="5"
            strokeLinecap="round"
            strokeDasharray={`${circumference * fraction} ${circumference}`}
            transform="rotate(-90 28 28)"
            style={{ transition: 'stroke-dasharray 0.6s ease' }}
          />
        </svg>
        <div>
          <p className="text-2xl font-semibold text-white">
            {health.passed}/{health.total}
          </p>
          <p className="text-xs text-slate-400">checks passing</p>
        </div>
      </div>
      <ul className="mt-4 space-y-2 text-sm">
        {health.checks.map((check) => (
          <li key={check.id} className="flex items-start justify-between gap-3">
            <span className="text-slate-300">
              <span className={`mr-2 inline-block w-3 font-bold ${STATUS[check.status].className}`} aria-hidden="true">
                {STATUS[check.status].icon}
              </span>
              {check.label}
            </span>
            <span className="text-right text-xs text-slate-400">{check.detail}</span>
          </li>
        ))}
        {health.info.map((item) => (
          <li key={item.id} className="flex items-start justify-between gap-3 border-t border-white/5 pt-2">
            <span className="pl-5 text-slate-400">{item.label}</span>
            <span className="text-right text-xs text-slate-500">{item.detail}</span>
          </li>
        ))}
      </ul>
    </Panel>
  )
}
