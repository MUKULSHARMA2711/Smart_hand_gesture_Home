import { DevicePowerBars } from '../components/charts/DevicePowerBars'
import { PowerLineChart } from '../components/charts/PowerLineChart'
import { Panel } from '../components/Panel'
import { AnimatedNumber } from '../components/SensorStrip'
import { formatEnergy, formatPower } from '../lib/format'
import { summarize } from '../state/energyHistory'
import { useHomeData } from '../state/HomeDataContext'

function Stat({ label, children, hint }) {
  return (
    <div className="glass-tile">
      <p className="text-[11px] font-semibold tracking-[0.18em] text-slate-400 uppercase">{label}</p>
      <p className="mt-1.5 text-3xl font-semibold text-white">{children}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

function formatSpan(ms) {
  const minutes = Math.floor(ms / 60000)
  const seconds = Math.round((ms % 60000) / 1000)
  return minutes ? `${minutes} min ${seconds} s` : `${seconds} s`
}

export function EnergyPage() {
  const { home, energyHistory } = useHomeData()
  const stats = summarize(energyHistory)
  const total = home.energy.total_power_w

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Power now" hint="All monitored devices">
          <AnimatedNumber value={total} format={formatPower} />
        </Stat>
        <Stat label="Session peak" hint="Highest sampled value">
          {stats ? formatPower(stats.peak) : '—'}
        </Stat>
        <Stat label="Session average" hint={stats ? `${stats.samples} samples` : 'Collecting'}>
          {stats ? formatPower(stats.average) : '—'}
        </Stat>
        <Stat label="Energy used" hint="Since the backend started">
          {formatEnergy(home.energy.energy_kwh)}
        </Stat>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <Panel title="Total power draw">
          <PowerLineChart samples={energyHistory} />
          <p className="mt-3 text-xs text-slate-500">
            Sampled by this browser from live home state every 5 s
            {stats ? ` · ${stats.samples} samples over ${formatSpan(stats.spanMs)}` : ''}. The backend does not store
            energy history yet, so the chart starts when this page is opened.
          </p>
        </Panel>
        <div className="space-y-6">
          <Panel title="Power by device · now">
            <DevicePowerBars devices={home.devices} total={total} />
          </Panel>
          <Panel title="Anomaly detection">
            <div className="flex items-start gap-3">
              <span className="mt-1 h-3 w-3 shrink-0 rounded-full border-2 border-slate-500" aria-hidden="true" />
              <div className="text-sm">
                <p className="font-semibold text-slate-200">Not available yet</p>
                <p className="mt-1 text-xs text-slate-400">
                  IntelliHome does not run anomaly detection yet, so no anomalies are reported or shown. When the
                  backend adds it, abnormal points will be highlighted on the chart and explained by the assistant.
                </p>
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}
