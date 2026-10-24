import type { ReactNode } from 'react'
import InfoTip from './InfoTip'

interface KpiCardProps {
  label: string
  value: ReactNode
  sub?: ReactNode
  info?: string
  stale?: boolean
}

/** Stat tile: label · value · optional context line. */
export default function KpiCard({ label, value, sub, info, stale }: KpiCardProps) {
  return (
    <div
      className={`rounded-xl border border-line bg-surface px-4 py-3 transition-opacity ${stale ? 'opacity-60' : ''}`}
    >
      <div className="flex items-center text-xs text-ink-2">
        {label}
        {info && <InfoTip text={info} />}
      </div>
      <div className="mt-1 text-2xl font-semibold tracking-tight text-ink">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-muted">{sub}</div>}
    </div>
  )
}

export function KpiRow({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">{children}</div>
}
