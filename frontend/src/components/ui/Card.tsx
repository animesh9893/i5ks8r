import type { ReactNode } from 'react'

interface CardProps {
  title?: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
  children: ReactNode
  className?: string
  /** Dim while a new filter's data loads; the previous render stays in place. */
  stale?: boolean
}

export default function Card({ title, subtitle, actions, children, className = '', stale }: CardProps) {
  return (
    <section
      className={`rounded-xl border border-line bg-surface p-4 sm:p-5 transition-opacity ${
        stale ? 'opacity-60' : ''
      } ${className}`}
    >
      {(title || actions) && (
        <header className="mb-3 flex flex-wrap items-start justify-between gap-2">
          <div>
            {title && <h2 className="text-sm font-semibold text-ink">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-ink-2">{subtitle}</p>}
          </div>
          {actions}
        </header>
      )}
      {children}
    </section>
  )
}
