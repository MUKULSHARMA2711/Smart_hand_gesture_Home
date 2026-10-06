import { formatPower } from '../../lib/format'
import { AnimatedNumber } from '../SensorStrip'

/**
 * Holographic readout of the real environment and energy values, overlaid on the 3D
 * view. Rendered as DOM (not inside the scene) so it never overlaps the house.
 */
export function SceneSensors({ environment, energy, className = '' }) {
  if (!environment || !energy) return null
  const people = environment.occupancy.occupant_count
  return (
    <dl className={`scene-sensors ${className}`} aria-label="Live sensor readings">
      <div>
        <dt>Temp</dt>
        <dd>
          <AnimatedNumber value={environment.temperature_c} format={(v) => `${v.toFixed(1)} °C`} />
        </dd>
      </div>
      <div>
        <dt>Humidity</dt>
        <dd>
          <AnimatedNumber value={environment.humidity_pct} format={(v) => `${v.toFixed(0)}%`} />
        </dd>
      </div>
      <div>
        <dt>Occupancy</dt>
        <dd>{environment.occupancy.occupied ? `${people} home` : 'Vacant'}</dd>
      </div>
      <div>
        <dt>Light</dt>
        <dd>
          <AnimatedNumber value={environment.ambient_light_lux} format={(v) => `${v.toFixed(0)} lux`} />
        </dd>
      </div>
      <div>
        <dt>Power</dt>
        <dd>
          <AnimatedNumber value={energy.total_power_w} format={formatPower} />
        </dd>
      </div>
    </dl>
  )
}
