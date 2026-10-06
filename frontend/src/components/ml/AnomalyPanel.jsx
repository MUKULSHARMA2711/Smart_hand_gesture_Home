import { useState } from 'react'
import { formatTime } from '../../lib/format'
import { describeReading, formatScore, formatWatts } from '../../lib/ml'
import { Panel } from '../Panel'

/** One Isolation Forest result: observed value vs. learned normal range. */
export function AnomalyCard({ result }) {
  return (
    <article
      className={`rounded-xl border p-3 ${result.is_anomaly ? 'border-red-500/40 bg-red-500/[0.07]' : 'border-emerald-500/25 bg-emerald-500/[0.05]'}`}
    >
      <header className="flex items-baseline justify-between gap-2">
        <p className="font-semibold text-slate-100">
          <span className={result.is_anomaly ? 'text-red-300' : 'text-emerald-300'} aria-hidden="true">
            {result.is_anomaly ? '⚠ ' : '✓ '}
          </span>
          {result.device_name} · {result.is_anomaly ? 'Anomaly' : 'Normal'}
        </p>
        <span className="text-[11px] text-slate-500 tabular-nums">{formatTime(result.timestamp)}</span>
      </header>
      <p className="mt-1 font-mono text-xs text-slate-200">{describeReading(result)}</p>
      <p className="mt-1 text-xs text-slate-400">{result.explanation}</p>
      <p className="mt-1 text-[11px] text-slate-500">
        Score {formatScore(result.score)} (below 0 = anomalous) · {result.model} · {result.source === 'reading' ? 'reported reading' : 'live device'}
      </p>
    </article>
  )
}

/** Live device checks plus recent anomalous readings, straight from GET /ml/anomalies. */
export function AnomalyPanel({ report, onAskAI }) {
  if (!report) {
    return (
      <Panel title="Anomaly detection">
        <p className="text-sm text-slate-400">Anomaly detection unavailable.</p>
      </Panel>
    )
  }
  return (
    <Panel title="Anomaly detection" action={<span className="font-mono text-[10px] text-slate-500">{report.model}</span>}>
      {report.active.length ? (
        <div className="space-y-2">
          {report.active.map((result) => (
            <AnomalyCard key={result.event_id ?? `${result.device_id}-${result.timestamp}`} result={result} />
          ))}
          {onAskAI && (
            <button type="button" onClick={onAskAI} className="command-button w-full py-2 text-xs">
              Ask AI to explain
            </button>
          )}
        </div>
      ) : (
        <p className="text-sm text-emerald-300">
          <span aria-hidden="true">✓ </span>No anomalies: every device is within its learned normal range.
        </p>
      )}
      <table className="mt-4 w-full text-left text-xs">
        <thead className="text-slate-500">
          <tr>
            <th className="py-1 font-medium">Device (live)</th>
            <th className="py-1 font-medium">Observed</th>
            <th className="py-1 font-medium">Normal range</th>
            <th className="py-1 font-medium">Status</th>
          </tr>
        </thead>
        <tbody className="text-slate-300">
          {report.live.map((result) => (
            <tr key={result.device_id} className="border-t border-white/5">
              <td className="py-1.5">{result.device_name}</td>
              <td className="py-1.5 font-mono">{formatWatts(result.observed_power_watts)}</td>
              <td className="py-1.5 font-mono">
                {result.expected_range.min.toFixed(1)}–{result.expected_range.max.toFixed(1)} W
              </td>
              <td className={`py-1.5 ${result.is_anomaly ? 'text-red-300' : 'text-emerald-300'}`}>
                {result.is_anomaly ? '⚠ Anomaly' : '✓ Normal'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  )
}

/** Submit a reading the way a hardware power meter would, and show the model's verdict. */
export function PowerReadingTester({ devices, onCheck }) {
  const [deviceId, setDeviceId] = useState(devices[0]?.id ?? '')
  const [watts, setWatts] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      setResult(await onCheck(deviceId, Number(watts)))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Panel title="Test a power reading">
      <p className="mb-3 text-xs text-slate-400">
        No hardware power meter is connected yet. Submit a reading the way one would report it; Isolation Forest
        compares it with the device's current setting.
      </p>
      <form onSubmit={submit} className="flex flex-wrap gap-2">
        <label className="sr-only" htmlFor="reading-device">
          Device
        </label>
        <select
          id="reading-device"
          value={deviceId}
          onChange={(event) => setDeviceId(event.target.value)}
          className="command-input flex-1"
        >
          {devices.map((device) => (
            <option key={device.id} value={device.id}>
              {device.name}
            </option>
          ))}
        </select>
        <label className="sr-only" htmlFor="reading-watts">
          Power in watts
        </label>
        <input
          id="reading-watts"
          type="number"
          min="0"
          step="0.1"
          required
          placeholder="Watts"
          value={watts}
          onChange={(event) => setWatts(event.target.value)}
          className="command-input w-28"
        />
        <button type="submit" disabled={busy || watts === ''} className="command-button">
          {busy ? 'Checking…' : 'Check'}
        </button>
      </form>
      {error && <p className="mt-2 text-xs text-red-300">{error}</p>}
      {result && (
        <div className="mt-3">
          <AnomalyCard result={result} />
        </div>
      )}
    </Panel>
  )
}
