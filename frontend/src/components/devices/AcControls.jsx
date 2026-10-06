import { commandRange } from '../../lib/format'
import { PowerSwitch } from '../controls/PowerSwitch'
import { Stepper } from '../controls/Stepper'
import { StateSummary } from './StateSummary'

export function AcControls({ device, busy, onCommand }) {
  const { is_on: isOn, target_temperature_c: target } = device.state
  const range = commandRange(device, 'set_temperature', { min: 16, max: 30 })

  return (
    <div className="space-y-4">
      <StateSummary primary={isOn ? 'Cooling' : 'Off'} secondary={`set to ${target} °C`} active={isOn} />
      <PowerSwitch accessibleLabel={`${device.name} power`} isOn={isOn} disabled={busy} onToggle={(next) => onCommand(next ? 'turn_on' : 'turn_off')} />
      <Stepper
        label="Target temperature"
        unit="°C"
        value={target}
        min={range.min}
        max={range.max}
        disabled={busy}
        onChange={(value) => onCommand('set_temperature', value)}
      />
    </div>
  )
}
