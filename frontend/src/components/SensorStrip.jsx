import { useEffect, useRef, useState } from 'react'
import { animate, useReducedMotion } from 'motion/react'
import { formatEnergy, formatPower } from '../lib/format'

/** Number that eases to each new backend value. */
export function AnimatedNumber({ value, format = (v) => v.toFixed(0) }) {
  const [display, setDisplay] = useState(value)
  const previous = useRef(value)
  const reduced = useReducedMotion()
  useEffect(() => {
    if (reduced) {
      setDisplay(value)
    } else {
      const controls = animate(previous.current, value, { duration: 0.8, ease: 'easeOut', onUpdate: setDisplay })
      previous.current = value
      return () => controls.stop()
    }
    previous.current = value
    return undefined
  }, [value, reduced])
  return <>{format(display)}</>
}

function Readout({ label, children, hint }) {
  return (
    <div className="glass-tile">
      <p className="text-[11px] font-semibold tracking-[0.18em] text-slate-400 uppercase">{label}</p>
      <p className="mt-1.5 text-2xl font-semibold text-white">{children}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

function SensorsUnavailable({ energy, reason }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
      <div role="status" className="glass-tile col-span-2 sm:col-span-2 xl:col-span-4">
        <p className="text-[11px] font-semibold tracking-[0.18em] text-amber-300 uppercase">
          <span aria-hidden="true">⚠ </span>Sensors unavailable
        </p>
        <p className="mt-1.5 text-sm text-slate-300">
          No valid temperature, humidity, occupancy or light reading. Values are not estimated.
        </p>
        {reason && <p className="mt-1 text-xs text-slate-500">{reason}</p>}
      </div>
      <Readout label="Power now" hint={`${formatEnergy(energy.energy_kwh)} since backend start`}>
        <AnimatedNumber value={energy.total_power_w} format={formatPower} />
      </Readout>
    </div>
  )
}

/** Live environment and energy readings from the real HomeState. */
export function SensorStrip({ home }) {
  if (!home) return null
  const { environment, energy } = home
  if (!environment) return <SensorsUnavailable energy={energy} reason={home.sensor_error} />
  const people = environment.occupancy.occupant_count
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
      <Readout label="Temperature">
        <AnimatedNumber value={environment.temperature_c} format={(v) => `${v.toFixed(1)} °C`} />
      </Readout>
      <Readout label="Humidity">
        <AnimatedNumber value={environment.humidity_pct} format={(v) => `${v.toFixed(0)}%`} />
      </Readout>
      <Readout label="Occupancy" hint={`${people} ${people === 1 ? 'person' : 'people'} detected`}>
        {environment.occupancy.occupied ? 'Occupied' : 'Vacant'}
      </Readout>
      <Readout label="Ambient light">
        <AnimatedNumber value={environment.ambient_light_lux} format={(v) => `${v.toFixed(0)} lux`} />
      </Readout>
      <Readout label="Power now" hint={`${formatEnergy(energy.energy_kwh)} since backend start`}>
        <AnimatedNumber value={energy.total_power_w} format={formatPower} />
      </Readout>
    </div>
  )
}
