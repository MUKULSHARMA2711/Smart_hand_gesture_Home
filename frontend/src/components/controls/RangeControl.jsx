import { useEffect, useId, useRef, useState } from 'react'

/**
 * Slider that sends a command only when the user releases it (pointer up / key up),
 * not on every intermediate value while dragging.
 */
export function RangeControl({ label, value, min, max, step = 1, unit = '', disabled, onCommit }) {
  const id = useId()
  const [draft, setDraft] = useState(value)
  const lastSent = useRef(null)

  // Re-sync with the backend's value whenever it changes or a command finishes.
  useEffect(() => {
    if (!disabled) {
      setDraft(value)
      lastSent.current = null
    }
  }, [value, disabled])

  const commit = () => {
    if (draft === value || draft === lastSent.current) return
    lastSent.current = draft
    onCommit(draft)
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <label htmlFor={id} className="text-slate-600 dark:text-slate-300">
          {label}
        </label>
        <span className="font-medium tabular-nums">
          {draft}
          {unit}
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={draft}
        disabled={disabled}
        onChange={(event) => setDraft(Number(event.target.value))}
        onPointerUp={commit}
        onKeyUp={commit}
        onBlur={commit}
        className="w-full cursor-pointer accent-indigo-600 disabled:cursor-not-allowed disabled:opacity-50 dark:accent-indigo-400"
      />
      <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>
          {min}
          {unit}
        </span>
        <span>
          {max}
          {unit}
        </span>
      </div>
    </div>
  )
}
