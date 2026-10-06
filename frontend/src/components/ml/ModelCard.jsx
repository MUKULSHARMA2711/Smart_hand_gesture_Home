import { Panel } from '../Panel'

const pct = (value) => `${Math.round(value * 1000) / 10}%`

/** Model versions and held-out evaluation, as reported by GET /ml/status. */
export function ModelCard({ status }) {
  if (!status) return null
  const { predictor, detector } = status
  return (
    <Panel title="Models">
      {predictor && (
        <section>
          <p className="font-mono text-xs text-cyan-200">{predictor.model}</p>
          <p className="text-xs text-slate-400">
            {predictor.algorithm} · target {predictor.target} · {predictor.metrics.test_samples} test samples
          </p>
          <dl className="mt-2 grid grid-cols-5 gap-2 text-center text-xs">
            {[
              ['Accuracy', predictor.metrics.accuracy],
              ['Baseline', predictor.metrics.baseline_accuracy],
              ['Precision', predictor.metrics.precision],
              ['Recall', predictor.metrics.recall],
              ['F1', predictor.metrics.f1],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg bg-white/[0.03] py-1.5">
                <dt className="text-[10px] text-slate-500 uppercase">{label}</dt>
                <dd className="font-mono text-slate-200">{pct(value)}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}
      {detector && (
        <section className="mt-4 border-t border-white/5 pt-3">
          <p className="font-mono text-xs text-cyan-200">{detector.model}</p>
          <p className="text-xs text-slate-400">{detector.algorithm} · features: setting, watts</p>
          <table className="mt-2 w-full text-left text-xs text-slate-300">
            <thead className="text-slate-500">
              <tr>
                <th className="py-1 font-medium">Device</th>
                <th className="py-1 font-medium">Precision</th>
                <th className="py-1 font-medium">Recall</th>
                <th className="py-1 font-medium">False alarms</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(detector.metrics).map(([device, m]) => (
                <tr key={device} className="border-t border-white/5">
                  <td className="py-1">{device}</td>
                  <td className="py-1 font-mono">{pct(m.precision)}</td>
                  <td className="py-1 font-mono">{pct(m.recall)}</td>
                  <td className="py-1 font-mono">{pct(m.false_positive_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      <p className="mt-3 text-[11px] text-amber-200/80">{status.data_note}</p>
    </Panel>
  )
}
