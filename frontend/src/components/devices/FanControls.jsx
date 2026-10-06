import { commandRange } from '../../lib/format'
import { PowerSwitch } from '../controls/PowerSwitch'
import { RangeControl } from '../controls/RangeControl'
import { StateSummary } from './StateSummary'

export function FanControls({ device, busy, onCommand }) {
  const { is_on: isOn, speed } = device.state
  const range = commandRange(device, 'set_speed')

  return (
    <div className="space-y-4">
      <StateSummary primary={isOn ? 'On' : 'Off'} secondary={isOn ? `${speed}% speed` : null} active={isOn} />
      <PowerSwitch accessibleLabel={`${device.name} power`} isOn={isOn} disabled={busy} onToggle={(next) => onCommand(next ? 'turn_on' : 'turn_off')} />
      <RangeControl
        label="Speed"
        unit="%"
        value={speed}
        min={range.min}
        max={range.max}
        disabled={busy}
        onCommit={(value) => onCommand('set_speed', value)}
      />
    </div>
  )
}
