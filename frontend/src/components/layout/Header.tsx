import { useHealth } from '../../api/hooks'

function ApiStatusBadge() {
  const { data, isError, isPending } = useHealth()
  const [label, cls] = isPending
    ? ['Connecting…', 'bg-slate-100 text-slate-600']
    : isError
      ? ['API offline', 'bg-red-100 text-red-700']
      : data.data_loaded
        ? ['Data loaded', 'bg-emerald-100 text-emerald-700']
        : ['API up · data loading', 'bg-amber-100 text-amber-700']
  return <span className={`rounded-full px-3 py-1 text-xs font-medium ${cls}`}>{label}</span>
}

export default function Header() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">GB Wind Forecast Monitor</h1>
          <p className="text-xs text-slate-500">National wind generation · Data: Elexon BMRS</p>
        </div>
        <ApiStatusBadge />
      </div>
    </header>
  )
}
