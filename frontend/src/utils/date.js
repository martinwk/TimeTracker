export const parseLocalDate = (dateStr) => {
  if (/T\d\d:/.test(dateStr)) return new Date(dateStr)
  return new Date(dateStr + 'T00:00:00')
}

export const makeLocalISO = (iso, hours, minutes) => {
  const d = parseLocalDate(iso)
  d.setHours(hours, minutes, 0, 0)
  return d.toISOString()
}

export const toLocalDateStr = (dateStr) => {
  const d = parseLocalDate(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
}

export const formatDuration = (seconds) => {
  if (seconds < 60) return `${seconds}s`
  const m = Math.round(seconds / 60)
  if (m < 60) return `${m}m`
  const h   = Math.floor(m / 60)
  const rem = m % 60
  return rem > 0 ? `${h}u${rem}m` : `${h}u`
}

export const getWeekNumber = (date) => {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() + 3 - ((d.getDay() + 6) % 7))
  const yearStart = new Date(d.getFullYear(), 0, 1)
  return Math.ceil((((d - yearStart) / 86400000) + 1) / 7)
}