import { useHealth, useMeta } from '../../api/hooks'
import { fmtDateTimeUK } from '../../lib/format'

function SourceBadge() {
  const health = useHealth()
  const meta = useMeta(!!health.data?.data_loaded)
  const [label, dot, title] = health.isError
    ? ['Data service offline', 'bg-critical', 'The API could not be reached']
    : !health.data?.data_loaded
      ? ['Loading data…', 'bg-muted', 'The API is fetching January data from Elexon']
      : meta.data?.source === 'live'
        ? ['Live Elexon data', 'bg-good', `Loaded ${fmtDateTimeUK(meta.data.loaded_at)} from Elexon BMRS`]
        : ['Offline snapshot', 'bg-muted', 'Elexon was unreachable; showing the bundled January snapshot']
  return (
    <span
      title={title}
      className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1 text-xs font-medium text-ink-2"
    >
      <span aria-hidden className={`h-2 w-2 rounded-full ${dot}`} />
      {label}
    </span>
  )
}

export default function Header() {
  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-ink">GB Wind Forecast Monitor</h1>
          <p className="text-xs text-ink-2">
            National wind generation for day-ahead purchasing · January 2026 · Source: Elexon BMRS
          </p>
        </div>
        <SourceBadge />
      </div>
    </header>
  )
}
