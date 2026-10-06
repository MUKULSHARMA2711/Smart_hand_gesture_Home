export function SectionHeading({ id, children }) {
  return (
    <h2 id={id} className="text-[11px] font-semibold tracking-[0.2em] text-slate-400 uppercase">
      {children}
    </h2>
  )
}

/** Titled glass card used across the command center. */
export function Panel({ title, action, children, className = '' }) {
  return (
    <section className={`glass-panel ${className}`}>
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
