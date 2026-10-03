export function SectionHeading({ id, children }) {
  return (
    <h2 id={id} className="text-sm font-semibold tracking-wide text-slate-500 uppercase dark:text-slate-400">
      {children}
    </h2>
  )
}

/** Titled card used across the gesture page. */
export function Panel({ title, action, children, className = '' }) {
  return (
    <section
      className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 ${className}`}
    >
      {(title || action) && (
        <header className="mb-4 flex items-center justify-between gap-3">
          {title && <SectionHeading>{title}</SectionHeading>}
          {action}
        </header>
      )}
      {children}
    </section>
  )
}
