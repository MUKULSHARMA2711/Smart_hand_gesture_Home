import { formatTime, humanizeConstant } from '../../lib/format'
import { SectionHeading } from '../Panel'

const OUTCOME_LABELS = {
  executed: 'Executed',
  acknowledged: 'Selected',
  rejected: 'Rejected',
  failed: 'Failed',
}

function Outcome({ event }) {
  return (
    <span className={event.success ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-700 dark:text-red-400'}>
      <span aria-hidden="true">{event.success ? '✓ ' : '✗ '}</span>
      {OUTCOME_LABELS[event.outcome] ?? event.outcome}
    </span>
  )
}

export function GestureHistory({ events, deviceNames }) {
  return (
    <section aria-labelledby="gesture-history-heading">
      <div className="mb-3">
        <SectionHeading id="gesture-history-heading">Recent gesture events</SectionHeading>
      </div>
      <div className="glass-panel overflow-x-auto p-0">
        {events.length === 0 ? (
          <p className="p-5 text-sm text-slate-500 dark:text-slate-400">No gestures yet.</p>
        ) : (
          <table className="w-full min-w-[44rem] text-left text-sm">
            <thead className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <tr>
                {['Time', 'Gesture', 'Confidence', 'Intent', 'Target', 'Action', 'Result'].map((heading) => (
                  <th key={heading} className="px-4 py-2.5 font-medium">
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {events.map((event) => (
                <tr key={event.event_id} className="align-top">
                  <td className="px-4 py-2.5 whitespace-nowrap text-slate-500 tabular-nums dark:text-slate-400">
                    {formatTime(event.timestamp)}
                  </td>
                  <td className="px-4 py-2.5 whitespace-nowrap">{humanizeConstant(event.gesture)}</td>
                  <td className="px-4 py-2.5 tabular-nums">{Math.round(event.confidence * 100)}%</td>
                  <td className="px-4 py-2.5 font-mono text-xs">{event.intent}</td>
                  <td className="px-4 py-2.5 whitespace-nowrap">{deviceNames[event.target_device_id] ?? event.target_device_id}</td>
                  <td className="px-4 py-2.5 font-mono text-xs">{event.action ?? '—'}</td>
                  <td className="px-4 py-2.5">
                    <Outcome event={event} />
                    {!event.success && event.detail && (
                      <p className="mt-0.5 max-w-xs text-xs text-slate-500 dark:text-slate-400">{event.detail}</p>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  )
}
