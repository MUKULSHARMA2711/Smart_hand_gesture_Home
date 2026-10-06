import { useEffect, useState } from 'react'
import {
  changedDeviceStates,
  confirmationSecondsLeft,
  describeAction,
  describeAssistantError,
  STATUS_STYLES,
} from '../../lib/assistant'
import { summarizeDeviceState } from '../../lib/format'

function ActionList({ actions, deviceNames }) {
  if (!actions.length) return null
  return (
    <ul className="mt-3 space-y-1.5 border-t border-slate-200 pt-3 dark:border-slate-700">
      {actions.map((result) => {
        const style = STATUS_STYLES[result.status] ?? STATUS_STYLES.failed
        return (
          <li key={result.index} className="text-sm">
            <span className={`font-medium ${style.tone}`}>
              <span aria-hidden="true">{style.icon} </span>
              <span className="sr-only">{style.label}: </span>
              {describeAction(result, deviceNames)}
            </span>
            {result.reason && <p className="ml-5 text-xs text-slate-500 dark:text-slate-400">{result.reason}</p>}
          </li>
        )
      })}
    </ul>
  )
}

function ChangedDevices({ response, devicesById }) {
  const changed = changedDeviceStates(response)
  if (!changed.length) return null
  return (
    <p className="mt-2 text-xs text-slate-600 dark:text-slate-300">
      <span className="font-semibold">Changed: </span>
      {changed
        .map(({ id, state }) => {
          const device = devicesById[id]
          if (!device) return id
          return state ? `${device.name} (${summarizeDeviceState({ ...device, state })})` : device.name
        })
        .join(', ')}
    </p>
  )
}

function AssistantBubble({ turn, devicesById, deviceNames }) {
  if (turn.pending) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400" aria-live="polite">
        IntelliHome is thinking<span className="animate-pulse">…</span>
      </p>
    )
  }
  if (turn.transportError) {
    const error = describeAssistantError(turn)
    return (
      <div role="alert" className="text-sm">
        <p className="font-medium text-red-700 dark:text-red-400">
          <span aria-hidden="true">⚠ </span>
          {error.title}
        </p>
        {error.hint && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{error.hint}</p>}
        {error.reason && <p className="mt-1 font-mono text-[11px] text-slate-500">{error.reason}</p>}
      </div>
    )
  }
  return (
    <>
      <p className="text-sm whitespace-pre-line">{turn.reply}</p>
      <ActionList actions={turn.actions ?? []} deviceNames={deviceNames} />
      <ChangedDevices response={turn} devicesById={devicesById} />
      {turn.errors?.length > 0 && (
        <ul className="mt-2 space-y-0.5 text-xs text-red-700 dark:text-red-400">
          {turn.errors.map((error) => (
            <li key={error}>{error}</li>
          ))}
        </ul>
      )}
      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{turn.outcome}</p>
    </>
  )
}

/**
 * A held door unlock: waiting for confirmation (with the time left) until the user confirms,
 * cancels, or it expires. Buttons call the backend; nothing unlocks from the browser.
 */
export function ConfirmationCard({ confirmation, active, busy, onDecide }) {
  const [now, setNow] = useState(() => Date.now())
  const secondsLeft = confirmationSecondsLeft(confirmation, now)
  useEffect(() => {
    if (!active || secondsLeft === 0) return undefined
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [active, secondsLeft])

  if (!active) return null
  if (secondsLeft === 0) {
    return <p className="mt-3 text-xs text-slate-500">Confirmation expired. The door stays locked.</p>
  }
  return (
    <div role="group" aria-label="Confirm door unlock" className="mt-3 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3">
      <p className="text-xs font-semibold text-amber-200">
        <span aria-hidden="true">🔒 </span>Waiting for confirmation · {secondsLeft} s
      </p>
      <p className="mt-1 text-xs text-slate-300">Say “yes, unlock it”, or use the buttons.</p>
      <div className="mt-2 flex gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => onDecide?.(confirmation, 'confirm')}
          className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-50"
        >
          Confirm unlock
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => onDecide?.(confirmation, 'cancel')}
          className="rounded-lg border border-slate-500 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-800 disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

export function ChatTurn({ turn, devicesById, deviceNames, isLatest = false, busy = false, onDecide }) {
  return (
    <li className="space-y-2">
      <div className="flex justify-end">
        <p className="max-w-[85%] rounded-2xl rounded-br-md bg-indigo-600 px-4 py-2 text-sm text-white dark:bg-indigo-500">
          {turn.request}
        </p>
      </div>
      <div className="flex justify-start">
        <div className="max-w-[85%] rounded-2xl rounded-bl-md border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/60">
          <AssistantBubble turn={turn} devicesById={devicesById} deviceNames={deviceNames} />
          {turn.confirmation && (
            <ConfirmationCard confirmation={turn.confirmation} active={isLatest} busy={busy} onDecide={onDecide} />
          )}
        </div>
      </div>
    </li>
  )
}
