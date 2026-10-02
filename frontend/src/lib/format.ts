const compact = new Intl.NumberFormat('es', { notation: 'compact', maximumFractionDigits: 1 })
const fullDate = new Intl.DateTimeFormat('es', { day: 'numeric', month: 'long', year: 'numeric' })
const shortDate = new Intl.DateTimeFormat('es', { day: 'numeric', month: 'short', year: 'numeric' })
const relative = new Intl.RelativeTimeFormat('es', { numeric: 'auto' })

export function formatViews(n: number): string {
  return `${compact.format(n)} ${n === 1 ? 'vista' : 'vistas'}`
}

/** Fecha corta: "1 oct 2026" (usada en las tarjetas como fecha de publicación). */
export function formatShortDate(iso: string): string {
  return shortDate.format(new Date(iso))
}

export function formatDate(iso: string): string {
  return fullDate.format(new Date(iso))
}

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['year', 60 * 60 * 24 * 365],
  ['month', 60 * 60 * 24 * 30],
  ['week', 60 * 60 * 24 * 7],
  ['day', 60 * 60 * 24],
  ['hour', 60 * 60],
  ['minute', 60],
]

export function timeAgo(iso: string): string {
  const seconds = (new Date(iso).getTime() - Date.now()) / 1000
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) return relative.format(Math.round(seconds / size), unit)
  }
  return 'hace un momento'
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join('')
}
