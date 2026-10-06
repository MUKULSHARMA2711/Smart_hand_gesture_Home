import { commandRange } from '../../lib/format'
import { PowerSwitch } from '../controls/PowerSwitch'
import { RangeControl } from '../controls/RangeControl'
import { StateSummary } from './StateSummary'

export function LightControls({ device, busy, onCommand }) {
  const { is_on: isOn, brightness } = device.state
  const range = commandRange(device, 'set_brightness')

  return (
    <div className="space-y-4">
      <StateSummary primary={isOn ? 'On' : 'Off'} secondary={isOn ? `${brightness}% brightness` : null} active={isOn} />
      <PowerSwitch accessibleLabel={`${device.name} power`} isOn={isOn} disabled={busy} onToggle={(next) => onCommand(next ? 'turn_on' : 'turn_off')} />
      <RangeControl
        label="Brightness"
        unit="%"
        value={brightness}
        min={range.min}
        max={range.max}
        disabled={busy}
        onCommit={(value) => onCommand('set_brightness', value)}
      />
    </div>
  )
}
