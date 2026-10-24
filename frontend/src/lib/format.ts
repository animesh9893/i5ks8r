import { formatInTimeZone, fromZonedTime } from 'date-fns-tz'

export const UK_TZ = 'Europe/London'

const int = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 })
const one = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1, minimumFractionDigits: 1 })

const missing = '—'

export const fmtMW = (v: number | null | undefined) => (v == null ? missing : `${int.format(v)} MW`)
export const fmtGW = (v: number | null | undefined) => (v == null ? missing : `${one.format(v / 1000)} GW`)
export const fmtGWh = (mwh: number | null | undefined) =>
  mwh == null ? missing : `${int.format(mwh / 1000)} GWh`
export const fmtPct = (v: number | null | undefined) => (v == null ? missing : `${one.format(v * 100)} %`)
export const fmtSignedGW = (v: number | null | undefined) =>
  v == null ? missing : `${v > 0 ? '+' : v < 0 ? '−' : ''}${one.format(Math.abs(v) / 1000)} GW`

const upToOne = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1 })

/** Compact axis tick: 12000 → "12 GW", 2500 → "2.5 GW", −4000 → "−4 GW". */
export const tickGW = (v: number) => `${v < 0 ? '−' : ''}${upToOne.format(Math.abs(v) / 1000)} GW`

/** "15 Jan 14:00" in UK time. */
export const fmtDateTimeUK = (iso: string | null | undefined) =>
  iso ? formatInTimeZone(iso, UK_TZ, 'd MMM HH:mm') : missing
export const fmtHourUK = (iso: string) => formatInTimeZone(iso, UK_TZ, 'HH:mm')
export const fmtDayUK = (iso: string) => formatInTimeZone(iso, UK_TZ, 'd MMM')
/** "Thu 15 Jan 2026" for a YYYY-MM-DD date string. */
export const fmtLongDate = (ymd: string) => formatInTimeZone(`${ymd}T12:00:00Z`, UK_TZ, 'EEE d MMM yyyy')

/** UK-local calendar day (YYYY-MM-DD) → UTC ISO of its local midnight. */
export const ukDayStartUtc = (ymd: string) => fromZonedTime(`${ymd}T00:00:00`, UK_TZ).toISOString()
/** UTC ISO → UK-local calendar day (YYYY-MM-DD). */
export const ukDay = (iso: string) => formatInTimeZone(iso, UK_TZ, 'yyyy-MM-dd')

/** Shift a YYYY-MM-DD date by n days. */
export function addDays(ymd: string, n: number): string {
  const d = new Date(`${ymd}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}

/** Round MW axis: ticks on a clean GW step covering [min, max] (min ≤ 0 ≤ max assumed). */
export function mwAxis(values: (number | null | undefined)[], target = 5) {
  const nums = values.filter((v): v is number => v != null && Number.isFinite(v))
  const lo = Math.min(0, ...nums)
  const hi = Math.max(0, ...nums)
  const span = hi - lo || 1000
  const step = [500, 1000, 2000, 2500, 4000, 5000, 10000].find((s) => span / s <= target) ?? 20000
  const min = Math.floor(lo / step) * step
  const max = Math.ceil(hi / step) * step
  const ticks: number[] = []
  for (let v = min; v <= max + 1e-9; v += step) ticks.push(v)
  return { domain: [min, max] as [number, number], ticks }
}
