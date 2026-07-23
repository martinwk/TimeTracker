import { describe, it, expect } from 'vitest'
import { parseLocalDate, makeLocalISO, toLocalDateStr, getWeekNumber, formatDuration } from './date'

describe('parseLocalDate', () => {
  it('parses a date-only string as local midnight', () => {
    const d = parseLocalDate('2024-01-15')
    expect(d.getFullYear()).toBe(2024)
    expect(d.getMonth()).toBe(0)
    expect(d.getDate()).toBe(15)
  })

  it('parses an ISO datetime string directly', () => {
    const d = parseLocalDate('2024-01-15T09:30:00Z')
    expect(d instanceof Date).toBe(true)
  })
})

describe('toLocalDateStr', () => {
  it('formats a date as YYYY-MM-DD', () => {
    expect(toLocalDateStr('2024-01-15T00:00:00')).toBe('2024-01-15')
  })

  it('zero-pads month and day', () => {
    expect(toLocalDateStr('2024-03-05T00:00:00')).toBe('2024-03-05')
  })
})

describe('makeLocalISO', () => {
  it('sets the given hour and minute on the iso date', () => {
    const result = makeLocalISO('2024-01-15', 9, 30)
    const d = new Date(result)
    expect(d.getHours()).toBe(9)
    expect(d.getMinutes()).toBe(30)
  })
})

describe('getWeekNumber', () => {
  it('week 3: 2024-01-15 (monday)', () => {
    expect(getWeekNumber(new Date('2024-01-15'))).toBe(3)
  })

  it('week 3: 2024-01-21 (sunday, last day of same week)', () => {
    expect(getWeekNumber(new Date('2024-01-21'))).toBe(3)
  })

  it('week 1: 2024-01-01', () => {
    expect(getWeekNumber(new Date('2024-01-01'))).toBe(1)
  })

  it('week 20: 2026-05-11 (the week that was wrongly reported as 19)', () => {
    expect(getWeekNumber(new Date('2026-05-11'))).toBe(20)
  })

  it('week 1: 2026-01-01', () => {
    expect(getWeekNumber(new Date('2026-01-01'))).toBe(1)
  })

  it('week 53: 2020-12-31 (year with 53 weeks)', () => {
    expect(getWeekNumber(new Date('2020-12-31'))).toBe(53)
  })

  it('accepts a Date object', () => {
    expect(typeof getWeekNumber(new Date('2024-06-10'))).toBe('number')
  })
})

describe('formatDuration', () => {
  it('toont seconden voor waarden onder een minuut', () => {
    expect(formatDuration(0)).toBe('0s')
    expect(formatDuration(1)).toBe('1s')
    expect(formatDuration(45)).toBe('45s')
    expect(formatDuration(59)).toBe('59s')
  })

  it('rondt af naar minuten voor 60 seconden en meer', () => {
    expect(formatDuration(60)).toBe('1m')
    expect(formatDuration(89)).toBe('1m')
    expect(formatDuration(90)).toBe('2m')
    expect(formatDuration(120)).toBe('2m')
    expect(formatDuration(870)).toBe('15m')
    expect(formatDuration(900)).toBe('15m')
  })

  it('toont uren voor waarden van een uur en meer', () => {
    expect(formatDuration(3600)).toBe('1u')
    expect(formatDuration(3660)).toBe('1u1m')
    expect(formatDuration(5400)).toBe('1u30m')
    expect(formatDuration(7200)).toBe('2u')
  })
})
