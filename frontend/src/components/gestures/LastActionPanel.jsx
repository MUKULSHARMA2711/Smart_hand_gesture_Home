import { actionLabel, humanizeConstant } from '../../lib/format'
import { Panel } from '../Panel'

export function LastActionPanel({ lastAction, deviceNames }) {
  if (!lastAction) {
    return (
      <Panel title="Last action">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Nothing executed yet. Hold a gesture steady for about half a second.
        </p>
      </Panel>
    )
  }

  const { status, gesture, intent, confidence, targetId, action, message } = lastAction
  const deviceName = deviceNames[targetId] ?? targetId

  return (
    <Panel title="Last action">
      <div aria-live="polite">
        {status === 'pending' && <p className="text-lg font-semibold">{deviceName} → …</p>}
        {status === 'success' && (
          <p className="flex flex-wrap items-baseline gap-x-2 text-lg font-semibold">
            <span>
              {deviceName} → {actionLabel(action)}
            </span>
            <span className="text-sm font-medium text-emerald-700 dark:text-emerald-400">✓ Succeeded</span>
          </p>
        )}
        {status === 'failure' && (
          <>
            <p className="flex flex-wrap items-baseline gap-x-2 text-lg font-semibold">
              <span>{deviceName}</span>
              <span className="text-sm font-medium text-red-700 dark:text-red-400">✗ Failed</span>
            </p>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{message}</p>
          </>
        )}
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
          {humanizeConstant(gesture)} · <span className="font-mono">{intent}</span> · {Math.round(confidence * 100)}%
        </p>
      </div>
    </Panel>
  )
}
