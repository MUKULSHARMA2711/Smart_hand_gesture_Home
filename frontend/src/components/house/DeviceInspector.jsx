import { useHomeData } from '../../state/HomeDataContext'
import { humanize, formatPower } from '../../lib/format'
import { AcControls } from '../devices/AcControls'
import { DoorControls } from '../devices/DoorControls'
import { FanControls } from '../devices/FanControls'
import { LightControls } from '../devices/LightControls'
import { Panel } from '../Panel'

const CONTROLS = { light: LightControls, fan: FanControls, ac: AcControls, door_lock: DoorControls }

/**
 * Details and controls for the device selected in the 3D view. Controls call the
 * existing command API; the scene only changes when the backend reports new state.
 */
export function DeviceInspector({ deviceId, onClose }) {
  const { home, sendCommand, pendingDeviceId } = useHomeData()
  const device = home?.devices.find((d) => d.id === deviceId)

  if (!device) {
    return (
      <Panel title="Device">
        <p className="text-sm text-slate-400">Select a device in the house to inspect and control it.</p>
      </Panel>
    )
  }

  const Controls = CONTROLS[device.device_type]
  return (
    <Panel
      title={device.name}
      action={
        <button type="button" onClick={onClose} className="text-xs text-slate-400 hover:text-white" aria-label="Close device panel">
          Close ✕
        </button>
      }
    >
      <p className="-mt-2 mb-4 text-xs text-slate-400">
        {humanize(device.room)} · <span className="text-emerald-400">{device.status}</span> · {formatPower(device.power_w)}
      </p>
      {Controls && (
        <Controls
          device={device}
          busy={pendingDeviceId === device.id}
          onCommand={(action, value) => sendCommand(device.id, action, value)}
        />
      )}
      <div className="mt-4 border-t border-slate-800 pt-3">
        <p className="mb-2 text-[11px] font-semibold tracking-widest text-slate-500 uppercase">Capabilities</p>
        <div className="flex flex-wrap gap-1.5">
          {device.capabilities.map((capability) => (
            <span key={capability} className="rounded-md border border-cyan-500/20 bg-cyan-500/5 px-2 py-0.5 font-mono text-[11px] text-cyan-300">
              {capability}
            </span>
          ))}
        </div>
      </div>
    </Panel>
  )
}
