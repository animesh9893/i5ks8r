import { ApiError } from '../../api/client'

export function LoadingBlock({ height = 320, label = 'Loading…' }: { height?: number; label?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex animate-pulse items-center justify-center rounded-lg bg-surface-2 text-xs text-muted"
      style={{ height }}
    >
      {label}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message =
    error instanceof ApiError
      ? error.status === 503
        ? 'The data service is still loading January data.'
        : error.message
      : 'Could not reach the data service.'
  return (
    <div role="alert" className="rounded-lg border border-line bg-surface-2 p-6 text-center">
      <p className="text-sm text-ink">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-md border border-line bg-surface px-3 py-1.5 text-xs font-medium text-ink hover:bg-surface-2"
        >
          Retry
        </button>
      )}
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-line p-6 text-center text-sm text-muted">
      {message}
    </div>
  )
}
