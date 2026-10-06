import { formatPower, humanize } from '../lib/format'
import { AcControls } from './devices/AcControls'
import { DoorControls } from './devices/DoorControls'
import { FanControls } from './devices/FanControls'
import { LightControls } from './devices/LightControls'

const CONTROLS_BY_TYPE = {
  light: LightControls,
  fan: FanControls,
  ac: AcControls,
  door_lock: DoorControls,
}

const STATUS_STYLES = {
  online: { dot: 'bg-emerald-500', label: 'Online' },
  offline: { dot: 'bg-slate-400', label: 'Offline' },
  error: { dot: 'bg-red-500', label: 'Error' },
}

function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.error
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 px-2 py-0.5 text-xs text-slate-600 dark:border-slate-700 dark:text-slate-300">
      <span className={`h-2 w-2 rounded-full ${style.dot}`} aria-hidden="true" />
      {style.label}
    </span>
  )
}

export function DeviceCard({ device, busy, onCommand }) {
  const Controls = CONTROLS_BY_TYPE[device.device_type]

  return (
    <article
      aria-busy={busy}
      className="glass-panel flex flex-col gap-5 transition duration-200 hover:-translate-y-0.5 hover:border-cyan-400/25"
    >
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold">{device.name}</h3>
          <p className="truncate text-sm text-slate-500 dark:text-slate-400">{humanize(device.room)}</p>
        </div>
        <StatusBadge status={device.status} />
      </header>

      {Controls ? (
        <Controls device={device} busy={busy} onCommand={onCommand} />
      ) : (
        <pre className="overflow-x-auto text-xs">{JSON.stringify(device.state, null, 2)}</pre>
      )}

      <footer className="mt-auto flex items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
        <span>Power draw</span>
        <span className="tabular-nums">{formatPower(device.power_w)}</span>
      </footer>
    </article>
  )
}
