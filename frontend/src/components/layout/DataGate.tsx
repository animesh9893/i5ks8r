import type { ReactNode } from 'react'
import { useHealth, useMeta } from '../../api/hooks'
import type { MetaResponse } from '../../api/types'
import { ErrorState, LoadingBlock } from '../ui/States'

/** Renders children only once the API is up and its data is loaded. */
export default function DataGate({ children }: { children: (meta: MetaResponse) => ReactNode }) {
  const health = useHealth()
  const ready = !!health.data?.data_loaded
  const meta = useMeta(ready)

  if (health.isError) return <ErrorState error={health.error} onRetry={() => health.refetch()} />
  if (meta.isError) return <ErrorState error={meta.error} onRetry={() => meta.refetch()} />
  if (!ready || !meta.data) {
    return <LoadingBlock height={420} label="Loading January 2026 wind data from Elexon…" />
  }
  return <>{children(meta.data)}</>
}
