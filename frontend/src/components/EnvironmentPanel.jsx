import { formatEnergy, formatNumber, formatPower } from '../lib/format'

function StatTile({ label, value, unit, hint }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1 flex items-baseline gap-1">
        <span className="text-2xl font-semibold">{value}</span>
        {unit && <span className="text-sm text-slate-500 dark:text-slate-400">{unit}</span>}
      </p>
      {hint && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
    </div>
  )
}

export function EnvironmentPanel({ environment, energy }) {
  const { temperature_c, humidity_pct, occupancy, ambient_light_lux } = environment
  const people = occupancy.occupant_count

  return (
    <section aria-labelledby="environment-heading">
      <h2 id="environment-heading" className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase dark:text-slate-400">
        Environment &amp; energy
      </h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <StatTile label="Temperature" value={formatNumber(temperature_c, 1)} unit="°C" />
        <StatTile label="Humidity" value={formatNumber(humidity_pct, 1)} unit="%" />
        <StatTile
          label="Occupancy"
          value={occupancy.occupied ? 'Occupied' : 'Vacant'}
          hint={`${people} ${people === 1 ? 'person' : 'people'} detected`}
        />
        <StatTile label="Ambient light" value={formatNumber(ambient_light_lux)} unit="lux" />
        <StatTile label="Power now" value={formatPower(energy.total_power_w)} hint="All monitored devices" />
        <StatTile label="Energy used" value={formatEnergy(energy.energy_kwh)} hint="Since backend start" />
      </div>
    </section>
  )
}
