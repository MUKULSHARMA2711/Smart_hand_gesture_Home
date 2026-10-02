export function PowerSwitch({ label = 'Power', isOn, disabled, onToggle }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-sm text-slate-600 dark:text-slate-300">{label}</span>
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium">{isOn ? 'On' : 'Off'}</span>
        <button
          type="button"
          role="switch"
          aria-checked={isOn}
          aria-label={label}
          disabled={disabled}
          onClick={() => onToggle(!isOn)}
          className={`relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-50 ${
            isOn ? 'bg-indigo-600 dark:bg-indigo-500' : 'bg-slate-300 dark:bg-slate-700'
          }`}
        >
          <span
            className={`inline-block h-5 w-5 rounded-full bg-white shadow transition-transform ${
              isOn ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>
    </div>
  )
}
