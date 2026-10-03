import { humanize, summarizeDeviceState } from '../../lib/format'
import { Panel } from '../Panel'

export function TargetSelector({ devices, selectedId, onSelect }) {
  return (
    <Panel title="Selected device">
      <fieldset>
        <legend className="sr-only">Device controlled by gestures</legend>
        <div className="grid gap-2">
          {devices.map((device) => {
            const selected = device.id === selectedId
            return (
              <label
                key={device.id}
                className={`flex cursor-pointer items-center justify-between gap-3 rounded-xl border px-3 py-2.5 transition-colors ${
                  selected
                    ? 'border-indigo-500 bg-indigo-50 dark:border-indigo-400 dark:bg-indigo-950/40'
                    : 'border-slate-200 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50'
                }`}
              >
                <span className="flex items-center gap-3">
                  <input
                    type="radio"
                    name="gesture-target"
                    value={device.id}
                    checked={selected}
                    onChange={() => onSelect(device.id)}
                    className="accent-indigo-600"
                  />
                  <span>
                    <span className="block text-sm font-medium">{device.name}</span>
                    <span className="block text-xs text-slate-500 dark:text-slate-400">{humanize(device.room)}</span>
                  </span>
                </span>
                <span className="text-sm text-slate-600 dark:text-slate-300">{summarizeDeviceState(device)}</span>
              </label>
            )
          })}
        </div>
      </fieldset>
      <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
        Show <span aria-hidden="true">☝️ </span>one finger to move to the next device.
      </p>
    </Panel>
  )
}
