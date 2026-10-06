import { changedDeviceStates, describeAction, describeAssistantError, STATUS_STYLES } from '../../lib/assistant'
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

export function ChatTurn({ turn, devicesById, deviceNames }) {
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
        </div>
      </div>
    </li>
  )
}
