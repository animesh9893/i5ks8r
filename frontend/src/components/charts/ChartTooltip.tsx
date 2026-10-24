import type { ReactNode } from 'react'

export interface TooltipRow {
  key: string
  label: string
  value: ReactNode
  /** Series colour shown as a short line key (or a square for bars/areas). */
  color?: string
  shape?: 'line' | 'square'
}

/** Values lead (strong), series names follow (secondary); identity via a small key, never text colour. */
export function TooltipCard({
  title,
  rows,
  footer,
}: {
  title: ReactNode
  rows: TooltipRow[]
  footer?: ReactNode
}) {
  return (
    <div className="min-w-44 rounded-lg border border-line bg-surface px-3 py-2 text-xs shadow-lg">
      <div className="mb-1.5 font-medium text-ink-2">{title}</div>
      <table className="tabular">
        <tbody>
          {rows.map((r) => (
            <tr key={r.key}>
              <td className="py-0.5 pr-2 align-middle">
                {r.color &&
                  (r.shape === 'square' ? (
                    <span className="block h-2.5 w-2.5 rounded-sm" style={{ background: r.color }} />
                  ) : (
                    <span className="block h-0.5 w-3 rounded" style={{ background: r.color }} />
                  ))}
              </td>
              <td className="py-0.5 pr-3 text-right font-semibold text-ink">{r.value}</td>
              <td className="py-0.5 text-ink-2">{r.label}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {footer && <div className="mt-1.5 border-t border-line pt-1.5 text-muted">{footer}</div>}
    </div>
  )
}

export interface LegendItem {
  label: string
  color: string
  shape: 'line' | 'square' | 'band'
}

/** Legend mirrors the mark: line key for lines, square for bars, wash for bands. */
export function ChartLegend({ items }: { items: LegendItem[] }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2">
      {items.map((i) => (
        <li key={i.label} className="flex items-center gap-1.5">
          {i.shape === 'line' && <span className="h-0.5 w-4 rounded" style={{ background: i.color }} />}
          {i.shape === 'square' && (
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: i.color }} />
          )}
          {i.shape === 'band' && (
            <span className="h-2.5 w-4 rounded-sm" style={{ background: i.color, opacity: 0.25 }} />
          )}
          {i.label}
        </li>
      ))}
    </ul>
  )
}
