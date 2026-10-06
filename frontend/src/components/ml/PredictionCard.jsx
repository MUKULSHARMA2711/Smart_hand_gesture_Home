import { formatProbability, predictionHeadline, predictionReasons } from '../../lib/ml'
import { Panel } from '../Panel'

/**
 * Random Forest prediction from the backend. It is a recommendation: the card says so
 * and never presents it as an executed action.
 */
export function PredictionCard({ prediction, onAskAI, title = 'AI prediction' }) {
  if (!prediction) {
    return (
      <Panel title={title}>
        <p className="text-sm text-slate-400">Prediction unavailable.</p>
      </Panel>
    )
  }
  const reasons = predictionReasons(prediction)
  const likely = prediction.prediction === 'ON'
  return (
    <Panel title={title} action={<span className="font-mono text-[10px] text-slate-500">{prediction.model}</span>}>
      <p className="text-sm text-slate-300">{prediction.device_name}</p>
      <p className={`mt-1 text-2xl font-semibold ${likely ? 'text-cyan-200' : 'text-slate-300'}`}>
        {formatProbability(prediction.probability)}
        <span className="ml-2 text-sm font-normal text-slate-400">
          {likely ? 'likely' : 'unlikely'} to be needed in {prediction.horizon_minutes} min
        </span>
      </p>
      <div className="relative mt-2 h-1.5 rounded-full bg-slate-800" aria-hidden="true">
        <div
          className={`h-1.5 rounded-full ${likely ? 'bg-cyan-400' : 'bg-slate-500'}`}
          style={{ width: formatProbability(prediction.probability) }}
        />
        <div className="absolute -top-1 h-3.5 w-0.5 bg-white/70" style={{ left: `${prediction.threshold * 100}%` }} />
      </div>
      <p className="sr-only">{predictionHeadline(prediction)}</p>
      {reasons.length > 0 && (
        <div className="mt-3">
          <p className="text-[11px] font-semibold tracking-[0.18em] text-slate-500 uppercase">Main factors</p>
          <ul className="mt-1 space-y-0.5 text-xs text-slate-300">
            {reasons.map((reason) => (
              <li key={reason}>· {reason}</li>
            ))}
          </ul>
        </div>
      )}
      <p className="mt-3 text-[11px] text-slate-500">
        Recommendation only; nothing has been switched on. Random Forest trained on simulated history.
      </p>
      {onAskAI && (
        <button type="button" onClick={onAskAI} className="command-button mt-3 w-full py-2 text-xs">
          Ask AI why
        </button>
      )}
    </Panel>
  )
}
