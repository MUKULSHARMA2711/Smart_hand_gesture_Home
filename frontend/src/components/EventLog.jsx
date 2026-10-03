import { describeStateChange, formatTime } from '../lib/format'

const SOURCE_STYLES = {
  frontend: { label: 'Dashboard', className: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300' },
  gesture: { label: 'Gesture', className: 'bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300' },
  ai_agent: { label: 'AI agent', className: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-950 dark:text-cyan-300' },
  automation: { label: 'Automation', className: 'bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-300' },
  mqtt: { label: 'MQTT', className: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300' },
}

function SourceBadge({ source }) {
  const style = SOURCE_STYLES[source] ?? { label: source, className: SOURCE_STYLES.frontend.className }
  return (
    <span title={source} className={`rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ${style.className}`}>
      {style.label}
    </span>
  )
}

export function EventLog({ events, deviceNames }) {
  return (
    <section aria-labelledby="events-heading">
      <h2 id="events-heading" className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase dark:text-slate-400">
        Recent events
      </h2>
      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        {events.length === 0 ? (
          <p className="p-5 text-sm text-slate-500 dark:text-slate-400">No device actions yet. Use a control above.</p>
        ) : (
          <table className="w-full min-w-[36rem] text-left text-sm">
            <thead className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <tr>
                <th className="px-4 py-2.5 font-medium">Time</th>
                <th className="px-4 py-2.5 font-medium">Device</th>
                <th className="px-4 py-2.5 font-medium">Action</th>
                <th className="px-4 py-2.5 font-medium">Change</th>
                <th className="px-4 py-2.5 font-medium">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {events.map((event) => (
                <tr key={event.event_id}>
                  <td className="px-4 py-2.5 whitespace-nowrap text-slate-500 tabular-nums dark:text-slate-400">
                    {formatTime(event.timestamp)}
                  </td>
                  <td className="px-4 py-2.5 whitespace-nowrap">{deviceNames[event.device_id] ?? event.device_id}</td>
                  <td className="px-4 py-2.5 font-mono text-xs whitespace-nowrap">
                    {event.action}
                    {event.value !== null && event.value !== undefined && `(${event.value})`}
                  </td>
                  <td className="px-4 py-2.5 text-slate-600 dark:text-slate-300">
                    {describeStateChange(event.previous_state, event.new_state)}
                  </td>
                  <td className="px-4 py-2.5">
                    <SourceBadge source={event.source} />
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
