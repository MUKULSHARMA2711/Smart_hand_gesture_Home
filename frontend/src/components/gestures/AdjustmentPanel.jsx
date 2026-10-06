import { formatAdjustment } from '../../gestures/adjustment'
import { Panel } from '../Panel'

const STATUS = {
  adjusting: { text: 'Adjusting · release the pinch to apply', tone: 'text-cyan-200' },
  sending: { text: 'Sending one command…', tone: 'text-cyan-200' },
  success: { text: '✓ Applied by the device', tone: 'text-emerald-300' },
  failure: { text: '✗ Not applied', tone: 'text-red-300' },
  unchanged: { text: 'Value unchanged · nothing was sent', tone: 'text-slate-400' },
  cancelled: { text: 'Hand lost · nothing was sent', tone: 'text-slate-400' },
}

/** Live preview of a pinch adjustment. The device itself changes only when the backend confirms. */
export function AdjustmentPanel({ adjustment }) {
  if (!adjustment) {
    return (
      <Panel title="Adjust">
        <p className="text-sm text-slate-400">
          Select the fan or the AC, then pinch (thumb + index, other fingers open) and move your hand up or down. Release
          to apply.
        </p>
      </Panel>
    )
  }
  if (adjustment.status === 'unsupported') {
    return (
      <Panel title="Adjust">
        <p role="status" className="text-sm text-amber-200">
          {adjustment.deviceName ?? 'This device'} has no adjustable value. Select the fan or the AC.
        </p>
      </Panel>
    )
  }
  const { range, value, startValue } = adjustment
  const status = STATUS[adjustment.status] ?? STATUS.adjusting
  const direction = value > startValue ? range.direction > 0 ? range.up : range.down : value < startValue ? range.direction > 0 ? range.down : range.up : null
  return (
    <Panel title="Adjust" action={<span className="font-mono text-[10px] text-slate-500">{adjustment.deviceName}</span>}>
      <div aria-live="polite">
        <p className="text-[11px] font-semibold tracking-[0.18em] text-slate-400 uppercase">{range.title}</p>
        <p className="mt-1 text-4xl font-semibold text-white tabular-nums">{formatAdjustment(range, value)}</p>
        <p className="mt-1 text-xs text-slate-400">
          from {formatAdjustment(range, startValue)}
          {direction && <span> · {direction}</span>} · range {formatAdjustment(range, range.min)}–{formatAdjustment(range, range.max)}
        </p>
        <p className="mt-2 text-xs text-slate-400">
          Hand up: {range.up} · hand down: {range.down}
        </p>
        <p role="status" className={`mt-3 text-sm ${status.tone}`}>
          {status.text}
          {adjustment.message && <span className="block text-xs text-slate-400">{adjustment.message}</span>}
        </p>
      </div>
    </Panel>
  )
}
