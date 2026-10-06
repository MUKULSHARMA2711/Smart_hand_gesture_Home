import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import { EventConsole } from '../components/console/EventConsole'
import { EventLog } from '../components/EventLog'
import { buildActivityFeed } from '../state/activityFeed'
import { useHomeData } from '../state/HomeDataContext'

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'device', label: 'Device events' },
  { id: 'gesture', label: 'Gestures' },
  { id: 'ai', label: 'AI agent' },
  { id: 'ml', label: 'ML anomalies' },
]

/** Full history from the three real activity sources, refreshed with the home poll. */
export function ActivityPage() {
  const { events: polledEvents, deviceNames } = useHomeData()
  const [history, setHistory] = useState({ deviceEvents: [], gestureEvents: [], aiInteractions: [] })
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    let cancelled = false
    Promise.allSettled([api.getEvents(100), api.getGestureEvents(100), api.getAIHistory(50)]).then(([d, g, a]) => {
      if (cancelled) return
      setHistory({
        deviceEvents: d.status === 'fulfilled' ? d.value : [],
        gestureEvents: g.status === 'fulfilled' ? g.value : [],
        aiInteractions: a.status === 'fulfilled' ? a.value : [],
      })
    })
    return () => {
      cancelled = true
    }
  }, [polledEvents])

  const feed = useMemo(() => buildActivityFeed({ ...history, deviceNames }), [history, deviceNames])
  const visible = filter === 'all' ? feed : feed.filter((entry) => entry.kind === filter)
  const counts = Object.fromEntries(FILTERS.map(({ id }) => [id, id === 'all' ? feed.length : feed.filter((e) => e.kind === id).length]))

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter activity">
        {FILTERS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            aria-pressed={filter === id}
            onClick={() => setFilter(id)}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
              filter === id
                ? 'border-cyan-400/60 bg-cyan-400/10 text-cyan-200'
                : 'border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
          >
            {label} <span className="text-slate-500">{counts[id]}</span>
          </button>
        ))}
      </div>
      <EventConsole entries={visible} limit={100} title="Activity stream" emptyText="No activity of this kind yet." />
      <EventLog events={history.deviceEvents.slice(0, 30)} deviceNames={deviceNames} />
    </div>
  )
}
