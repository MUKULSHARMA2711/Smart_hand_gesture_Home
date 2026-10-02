function StepButton({ children, ...props }) {
  return (
    <button
      type="button"
      className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-300 text-lg font-medium transition-colors hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:hover:bg-slate-800"
      {...props}
    >
      {children}
    </button>
  )
}

export function Stepper({ label, value, min, max, unit = '', disabled, onChange }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-sm text-slate-600 dark:text-slate-300">{label}</span>
      <div className="flex items-center gap-2">
        <StepButton aria-label={`Decrease ${label}`} disabled={disabled || value <= min} onClick={() => onChange(value - 1)}>
          −
        </StepButton>
        <span className="w-16 text-center text-lg font-semibold tabular-nums" aria-live="polite">
          {value}
          {unit}
        </span>
        <StepButton aria-label={`Increase ${label}`} disabled={disabled || value >= max} onClick={() => onChange(value + 1)}>
          +
        </StepButton>
      </div>
    </div>
  )
}
