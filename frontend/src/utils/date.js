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