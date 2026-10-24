import { useId } from 'react'

/** Small ⓘ with a hover/focus popover. Keyboard reachable; text is plain (no HTML). */
export default function InfoTip({ text }: { text: string }) {
  const id = useId()
  return (
    <span className="group relative inline-flex align-middle">
      <button
        type="button"
        aria-describedby={id}
        aria-label="More information"
        className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full border border-line text-[10px] leading-none text-muted hover:text-ink focus:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        i
      </button>
      <span
        id={id}
        role="tooltip"
        className="pointer-events-none invisible absolute bottom-full left-1/2 z-20 mb-2 w-64 -translate-x-1/2 rounded-lg border border-line bg-surface p-2.5 text-xs font-normal leading-snug text-ink-2 opacity-0 shadow-lg transition group-focus-within:visible group-focus-within:opacity-100 group-hover:visible group-hover:opacity-100"
      >
        {text}
      </span>
    </span>
  )
}
