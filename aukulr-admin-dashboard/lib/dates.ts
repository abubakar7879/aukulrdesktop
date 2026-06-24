// Returns today's date as YYYY-MM-DD in *local* time.
// new Date().toISOString() is UTC — slicing it gives the wrong date in UTC+ zones.
function localISO(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function todayISO(): string {
  return localISO(new Date())
}

export function soonISO(days = 7): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return localISO(d)
}

// All comparisons are pure YYYY-MM-DD string comparisons — lexicographic order
// matches chronological order for ISO date strings, and avoids any Date object
// timezone offset ambiguity.
export function isExpired(expiryDate: string): boolean {
  return expiryDate < todayISO()
}

export function isExpiringSoon(expiryDate: string): boolean {
  const today = todayISO()
  return expiryDate >= today && expiryDate <= soonISO()
}
