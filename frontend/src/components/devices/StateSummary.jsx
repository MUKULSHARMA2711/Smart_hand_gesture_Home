/** Large, at-a-glance current state of a device, e.g. "On · 70% brightness". */
export function StateSummary({ primary, secondary, active }) {
  return (
    <p className="flex items-baseline gap-2">
      <span
        className={`text-2xl font-semibold ${active ? 'text-slate-900 dark:text-white' : 'text-slate-500 dark:text-slate-400'}`}
      >
        {primary}
      </span>
      {secondary && <span className="text-sm text-slate-500 dark:text-slate-400">{secondary}</span>}
    </p>
  )
}
