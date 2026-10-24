import { useSyncExternalStore } from 'react'

/**
 * Chart colours by role. Validated (dataviz validate_palette) in both modes:
 *  - actual (slot 1 blue) vs forecast (slot 2 orange): CVD ΔE ≥ 24.7, ≥ 3:1 contrast.
 *  - error polarity (diverging): under-forecast blue vs over-forecast red: CVD ΔE ≥ 19.2.
 */
const LIGHT = {
  actual: '#2a78d6',
  forecast: '#eb6834',
  over: '#e34948',
  under: '#2a78d6',
  grid: '#e2e1dc',
  axis: '#75746f',
  ink: '#0b0b0b',
  ink2: '#52514e',
  surface: '#fcfcfb',
  highlight: '#f0efec',
}

const DARK: typeof LIGHT = {
  actual: '#3987e5',
  forecast: '#d95926',
  over: '#e66767',
  under: '#3987e5',
  grid: '#383835',
  axis: '#9a998f',
  ink: '#f0efec',
  ink2: '#c3c2b7',
  surface: '#1a1a19',
  highlight: '#2b2b29',
}

export type ChartColors = typeof LIGHT

const query = '(prefers-color-scheme: dark)'

function subscribe(cb: () => void) {
  const mql = window.matchMedia(query)
  mql.addEventListener('change', cb)
  return () => mql.removeEventListener('change', cb)
}

export function useChartColors(): ChartColors {
  const dark = useSyncExternalStore(
    subscribe,
    () => window.matchMedia(query).matches,
    () => false,
  )
  return dark ? DARK : LIGHT
}
