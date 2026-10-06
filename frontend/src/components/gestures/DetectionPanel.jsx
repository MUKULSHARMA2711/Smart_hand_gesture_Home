import { isActionable } from '../../gestures/types'
import { humanizeConstant } from '../../lib/format'
import { Panel } from '../Panel'

const FINGER_ORDER = ['thumb', 'index', 'middle', 'ring', 'pinky']

function ConfidenceMeter({ confidence, threshold }) {
  const passes = confidence >= threshold
  return (
    <div className="relative mt-2 h-2 rounded-full bg-slate-200 dark:bg-slate-800">
      <div
        className={`h-2 rounded-full transition-[width] duration-100 ${passes ? 'bg-indigo-600 dark:bg-indigo-400' : 'bg-slate-400 dark:bg-slate-500'}`}
        style={{ width: `${Math.round(confidence * 100)}%` }}
      />
      {/* Threshold marker */}
      <div
        className="absolute -top-1 h-4 w-0.5 rounded bg-slate-900 dark:bg-white"
        style={{ left: `${threshold * 100}%` }}
        aria-hidden="true"
      />
    </div>
  )
}

function StatusLine({ live, threshold }) {
  const thresholdPct = `${Math.round(threshold * 100)}%`
  if (live.gesture === 'NEUTRAL') return <p>No hand detected. Show your hand to the camera.</p>
  if (!isActionable(live.gesture)) return <p>Hand visible, but no known gesture. Nothing will be sent.</p>
  if (live.confidence < threshold) {
    return (
      <p className="text-amber-700 dark:text-amber-400">
        <span aria-hidden="true">⚠ </span>Gesture ignored — confidence too low (below the {thresholdPct} threshold).
      </p>
    )
  }
  if (live.awaitingRelease) return <p>Executed. Lower your hand or change gesture to send again.</p>
  return (
    <div>
      <p>Hold steady to confirm…</p>
      <div className="mt-1.5 h-1 rounded-full bg-slate-200 dark:bg-slate-800">
        <div className="h-1 rounded-full bg-indigo-600 dark:bg-indigo-400" style={{ width: `${live.progress * 100}%` }} />
      </div>
    </div>
  )
}

export function DetectionPanel({ live, threshold, intents, running }) {
  const noHand = live.gesture === 'NEUTRAL'
  const intent = intents[live.gesture]

  return (
    <Panel title="Detection">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-4">
        <div className="col-span-2">
          <dt className="text-sm text-slate-500 dark:text-slate-400">Detected</dt>
          <dd className="mt-0.5 text-2xl font-semibold">{!running ? '—' : noHand ? 'No hand' : humanizeConstant(live.gesture)}</dd>
          {running && !noHand && <dd className="font-mono text-xs text-slate-500 dark:text-slate-400">{live.gesture}</dd>}
        </div>
        <div>
          <dt className="text-sm text-slate-500 dark:text-slate-400">Confidence</dt>
          <dd className="mt-0.5 text-xl font-semibold">{running && !noHand ? `${Math.round(live.confidence * 100)}%` : '—'}</dd>
        </div>
        <div>
          <dt className="text-sm text-slate-500 dark:text-slate-400">Intent</dt>
          <dd className="mt-0.5 font-mono text-lg font-semibold">{running && intent && intent !== 'NONE' ? intent : '—'}</dd>
        </div>
        <div className="col-span-2">
          <ConfidenceMeter confidence={running ? live.confidence : 0} threshold={threshold} />
          <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
            Threshold {Math.round(threshold * 100)}% (marker)
          </p>
        </div>
      </dl>

      {running && (
        <div className="mt-4 border-t border-slate-100 pt-3 text-sm text-slate-600 dark:border-slate-800 dark:text-slate-300">
          <StatusLine live={live} threshold={threshold} />
        </div>
      )}

      {running && live.fingers && (
        <details className="mt-3 text-xs text-slate-500 dark:text-slate-400">
          <summary className="cursor-pointer select-none">Finger extension (for tuning)</summary>
          <ul className="mt-2 space-y-1">
            {FINGER_ORDER.map((finger) => (
              <li key={finger} className="flex items-center gap-2">
                <span className="w-12 capitalize">{finger}</span>
                <span className="h-1.5 flex-1 rounded-full bg-slate-200 dark:bg-slate-800">
                  <span
                    className="block h-1.5 rounded-full bg-slate-500 dark:bg-slate-400"
                    style={{ width: `${live.fingers[finger] * 100}%` }}
                  />
                </span>
                <span className="w-8 text-right tabular-nums">{Math.round(live.fingers[finger] * 100)}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </Panel>
  )
}
