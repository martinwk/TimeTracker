// Tests for pure logic functions in the activityBlocks store.
// These test store computeds and actions without hitting the API.
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { makeLocalISO, parseLocalDate } from '@/utils/date'

vi.mock('@/api/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

import { useActivityBlocksStore } from './activityBlocks'

const ISO = '2024-01-15'

// Aggregator-blok: geen project, heeft unique_activities (AHK-import)
// block_minutes=15 en ended_at zijn altijd aanwezig op blokken van de API.
const makeAggregatorBlock = (id, startHour, startMin, activities) => ({
  id,
  started_at:    makeLocalISO(ISO, startHour, startMin),
  ended_at:      makeLocalISO(ISO, startHour, startMin + 15),
  total_seconds: 300, // overlap-tijd, niet 15 min
  block_minutes: 15,
  dominant_title: `Block ${id}`,
  project:       null,
  unique_activities: activities.map((ua, i) => ({
    id:           id * 100 + i,
    raw_title:    ua.title,
    app_name:     'Test',
    total_seconds: ua.seconds,
  })),
})

// Leeg blok: geen project, geen unique_activities (handmatig aangemaakt)
const makeEmptyBlock = (id, startHour, startMin) => ({
  id,
  started_at:     makeLocalISO(ISO, startHour, startMin),
  total_seconds:  900,
  dominant_title: 'Nieuw blok',
  project:        null,
  unique_activities: [],
})

// Toegewezen blok: heeft project
const makeProjectBlock = (id, startHour, startMin, project, activities = []) => ({
  id,
  started_at:     makeLocalISO(ISO, startHour, startMin),
  ended_at:       makeLocalISO(ISO, startHour, startMin + 15),
  total_seconds:  900,
  block_minutes:  15,
  dominant_title: project.name,
  project,
  unique_activities: activities.map((ua, i) => ({
    id:            id * 100 + i,
    raw_title:     ua.title,
    app_name:      'Test',
    total_seconds: ua.seconds,
  })),
})

// ── getTopActivities ──────────────────────────────────────────────────────────
describe('activityBlocks store — getTopActivities', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useActivityBlocksStore()
    store.currentDate = ISO
  })

  it('geeft [] terug bij lege store', () => {
    expect(store.getTopActivities(ISO, 540, 555)).toEqual([])
  })

  it('sluit blokken met een project uit', () => {
    const block = makeProjectBlock(1, 9, 0, { id: 1, name: 'Test', color: '#abc' })
    block.unique_activities = [{ id: 1, raw_title: 'VS Code', app_name: 'VS Code', total_seconds: 600 }]
    store.blocks = [block]
    expect(store.getTopActivities(ISO, 540, 555)).toEqual([])
  })

  it('sluit blokken zonder unique_activities uit', () => {
    store.blocks = [makeEmptyBlock(1, 9, 0)]
    expect(store.getTopActivities(ISO, 540, 555)).toEqual([])
  })

  it('sluit blokken van een andere dag uit', () => {
    store.blocks = [{
      ...makeAggregatorBlock(1, 9, 0, [{ title: 'VS Code', seconds: 600 }]),
      started_at: makeLocalISO('2024-01-16', 9, 0),
    }]
    expect(store.getTopActivities(ISO, 540, 555)).toEqual([])
  })

  it('sluit blokken buiten het tijdsvenster uit (10:00 is buiten 9:00-9:15)', () => {
    store.blocks = [makeAggregatorBlock(1, 10, 0, [{ title: 'VS Code', seconds: 600 }])]
    expect(store.getTopActivities(ISO, 540, 555)).toEqual([])
  })

  it('includeert blok waarvan startMin in het venster valt', () => {
    store.blocks = [makeAggregatorBlock(1, 9, 0, [{ title: 'VS Code', seconds: 600 }])]
    const result = store.getTopActivities(ISO, 540, 555)
    expect(result).toHaveLength(1)
    expect(result[0].title).toBe('VS Code')
    expect(result[0].seconds).toBe(600)
  })

  it('aggregeert dezelfde raw_title over meerdere blokken', () => {
    store.blocks = [
      makeAggregatorBlock(1, 9, 0,  [{ title: 'VS Code', seconds: 300 }]),
      makeAggregatorBlock(2, 9, 15, [{ title: 'VS Code', seconds: 400 }]),
    ]
    const result = store.getTopActivities(ISO, 540, 570)
    expect(result).toHaveLength(1)
    expect(result[0].seconds).toBe(700)
  })

  it('sorteert op seconden aflopend', () => {
    store.blocks = [makeAggregatorBlock(1, 9, 0, [
      { title: 'Chrome', seconds: 200 },
      { title: 'VS Code', seconds: 600 },
      { title: 'Slack',  seconds: 100 },
    ])]
    const result = store.getTopActivities(ISO, 540, 555)
    expect(result[0].title).toBe('VS Code')
    expect(result[1].title).toBe('Chrome')
    expect(result[2].title).toBe('Slack')
  })

  it('beperkt het resultaat tot n items (standaard 3)', () => {
    store.blocks = [makeAggregatorBlock(1, 9, 0, [
      { title: 'A', seconds: 400 },
      { title: 'B', seconds: 300 },
      { title: 'C', seconds: 200 },
      { title: 'D', seconds: 100 },
    ])]
    expect(store.getTopActivities(ISO, 540, 555)).toHaveLength(3)
    expect(store.getTopActivities(ISO, 540, 555, 2)).toHaveLength(2)
  })

  it('blok op de grens (bStart = endMin - 15) valt binnen het venster', () => {
    store.blocks = [
      makeAggregatorBlock(1, 9, 0,  [{ title: 'A', seconds: 300 }]), // bStart=540
      makeAggregatorBlock(2, 9, 15, [{ title: 'B', seconds: 300 }]), // bStart=555
    ]
    // venster 540-570: beide vallen erin (540 < 570 en 555 < 570)
    const result = store.getTopActivities(ISO, 540, 570)
    expect(result).toHaveLength(2)
  })

  it('toont per-slot overlap-seconden voor dezelfde titel die twee slots overspant', () => {
    // Simuleert: activiteit 12:29–12:34 → slot 12:15 krijgt 60 sec, slot 12:30 krijgt 240 sec
    store.blocks = [
      makeAggregatorBlock(1, 12, 15, [{ title: 'Inbox - Firefox', seconds: 60 }]),
      makeAggregatorBlock(2, 12, 30, [{ title: 'Inbox - Firefox', seconds: 240 }]),
    ]
    const result1215 = store.getTopActivities(ISO, 735, 750)
    expect(result1215).toHaveLength(1)
    expect(result1215[0].seconds).toBe(60)

    const result1230 = store.getTopActivities(ISO, 750, 765)
    expect(result1230).toHaveLength(1)
    expect(result1230[0].seconds).toBe(240)
  })
})

// ── activityIndicatorsByDay ───────────────────────────────────────────────────
describe('activityBlocks store — activityIndicatorsByDay', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useActivityBlocksStore()
    store.currentDate = ISO
  })

  it('groepeert aggregator-blokken per dag', () => {
    store.blocks = [
      makeAggregatorBlock(1, 9, 0,  [{ title: 'VS Code', seconds: 300 }]),
      makeAggregatorBlock(2, 9, 15, [{ title: 'Chrome',  seconds: 200 }]),
    ]
    expect(store.activityIndicatorsByDay[ISO]).toHaveLength(2)
  })

  it('sluit blokken met een project uit', () => {
    store.blocks = [
      makeAggregatorBlock(1, 9, 0,  [{ title: 'VS Code', seconds: 300 }]),
      makeProjectBlock(2, 9, 15, { id: 1, name: 'Test', color: '#abc' }),
    ]
    expect(store.activityIndicatorsByDay[ISO]).toHaveLength(1)
  })

  it('sluit blokken zonder unique_activities uit', () => {
    store.blocks = [makeEmptyBlock(1, 9, 0)]
    expect(store.activityIndicatorsByDay[ISO]).toBeUndefined()
  })
})

// ── mergedBlocksByDay (aggregator filtering) ──────────────────────────────────
describe('activityBlocks store — mergedBlocksByDay met aggregator filtering', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useActivityBlocksStore()
    store.currentDate = ISO
  })

  it('sluit aggregator-blokken zonder project uit van de interactieve blokken', () => {
    store.blocks = [makeAggregatorBlock(1, 9, 0, [{ title: 'VS Code', seconds: 300 }])]
    expect(store.mergedBlocksByDay[ISO] ?? []).toHaveLength(0)
  })

  it('includeert aggregator-blokken die wel een project hebben', () => {
    store.blocks = [{
      ...makeAggregatorBlock(1, 9, 0, [{ title: 'VS Code', seconds: 300 }]),
      project: { id: 1, name: 'Test', color: '#abc' },
    }]
    expect(store.mergedBlocksByDay[ISO]).toHaveLength(1)
  })

  it('includeert handmatig aangemaakte blokken zonder project', () => {
    store.blocks = [makeEmptyBlock(1, 9, 0)]
    expect(store.mergedBlocksByDay[ISO]).toHaveLength(1)
  })
})

// ── selectOrCreateRange (aggregator blokken) ──────────────────────────────────
describe('activityBlocks store — selectOrCreateRange met aggregator blokken', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useActivityBlocksStore()
    store.currentDate = ISO
  })

  it('selecteert een aggregator-blok in het bereik in plaats van te breken', () => {
    store.blocks = [makeAggregatorBlock(1, 9, 0, [{ title: 'VS Code', seconds: 300 }])]
    store.selectOrCreateRange(ISO, 540, 555)
    expect(store.selectedBlocks).toContain(1)
  })

  it('selecteert meerdere aggregator-blokken in een bereik', () => {
    store.blocks = [
      makeAggregatorBlock(1, 9, 0,  [{ title: 'VS Code', seconds: 300 }]),
      makeAggregatorBlock(2, 9, 15, [{ title: 'Chrome',  seconds: 300 }]),
    ]
    store.selectOrCreateRange(ISO, 540, 570)
    expect(store.selectedBlocks).toContain(1)
    expect(store.selectedBlocks).toContain(2)
  })

  it('stopt bij een toegewezen blok (selecteert het niet)', () => {
    store.blocks = [
      makeAggregatorBlock(1, 9, 0,  [{ title: 'VS Code', seconds: 300 }]),
      makeProjectBlock(2, 9, 15, { id: 1, name: 'Test', color: '#abc' }),
    ]
    store.selectOrCreateRange(ISO, 540, 570)
    expect(store.selectedBlocks).toContain(1)
    expect(store.selectedBlocks).not.toContain(2)
  })

  it('maakt een nieuw blok aan voor een lege slot', () => {
    store.blocks = []
    store.selectOrCreateRange(ISO, 540, 555)
    expect(store.blocks).toHaveLength(1)
    expect(store.selectedBlocks).toHaveLength(1)
  })

  it('selecteert aggregator-blok naast nieuw blok voor lege aangrenzende slot', () => {
    store.blocks = [
      makeAggregatorBlock(1, 9, 0, [{ title: 'VS Code', seconds: 300 }]),
      // 9:15 is leeg
    ]
    store.selectOrCreateRange(ISO, 540, 570)
    expect(store.selectedBlocks).toContain(1)       // aggregator geselecteerd
    expect(store.blocks).toHaveLength(2)             // nieuw blok aangemaakt voor 9:15
    expect(store.selectedBlocks).toHaveLength(2)
  })
})

// ── blockEndMin fallback-keten ────────────────────────────────────────────────
// Deze tests raken aan hoe selectOrCreateRange en mergedBlocksByDay de
// eindminuut van een blok bepalen. Ze zijn relevant voor de merge-logica.
describe('activityBlocks store — blockEndMin fallback via selectOrCreateRange / mergedBlocksByDay', () => {
  let store
  const P = { id: 1, name: 'Test', color: '#abc' }

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useActivityBlocksStore()
    store.currentDate = ISO
    store.projects = [P]
  })

  it('temp-blok uit selectOrCreateRange heeft ended_at gelijk aan slot-einde', () => {
    store.blocks = []
    store.selectOrCreateRange(ISO, 540, 555)
    const tempBlock = store.blocks[0]
    expect(tempBlock.ended_at).toBeDefined()
    // ended_at moet op 9:15 staan (15 min na 9:00)
    const e = parseLocalDate(tempBlock.ended_at)
    expect(e.getHours() * 60 + e.getMinutes()).toBe(555)
  })

  it('aggregator-blok zonder ended_at maar met block_minutes=15 fust correct in mergedBlocksByDay', async () => {
    // Simuleer blok dat alleen block_minutes heeft (geen ended_at) — valt terug op fallback
    store.blocks = [
      {
        id: 1,
        started_at:    makeLocalISO(ISO, 9,  0),
        total_seconds: 300,       // overlap-tijd: zonder fallback geeft dit bEnd=545 (fout)
        block_minutes: 15,        // fallback geeft bEnd=555 (correct)
        dominant_title: 'VS Code',
        project: null,
        unique_activities: [{ id: 1, raw_title: 'VS Code', total_seconds: 300 }],
        // ended_at bewust weggelaten
      },
      {
        id: 2,
        started_at:    makeLocalISO(ISO, 9, 15),
        total_seconds: 300,
        block_minutes: 15,
        dominant_title: 'Chrome',
        project: null,
        unique_activities: [{ id: 2, raw_title: 'Chrome', total_seconds: 200 }],
      },
    ]
    store.selectOrCreateRange(ISO, 540, 555)
    await store.assignToProject(P.id)
    store.selectOrCreateRange(ISO, 555, 570)
    await store.assignToProject(P.id)

    const day = store.mergedBlocksByDay[ISO]
    expect(day).toHaveLength(1)
    expect(day[0].blocks).toHaveLength(2)
  })
})

// ── merge na opeenvolgende toewijzing ─────────────────────────────────────────
describe('activityBlocks store — merge na opeenvolgende project-toewijzing', () => {
  let store
  const P = { id: 1, name: 'Test', color: '#abc' }

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useActivityBlocksStore()
    store.currentDate = ISO
    store.projects = [P]
  })

  it('twee aangrenzende aggregator-blokken fuseren na opeenvolgende toewijzing', async () => {
    store.blocks = [
      makeAggregatorBlock(1, 9,  0, [{ title: 'VS Code', seconds: 300 }]),
      makeAggregatorBlock(2, 9, 15, [{ title: 'Chrome',  seconds: 200 }]),
    ]
    store.selectOrCreateRange(ISO, 540, 555)
    await store.assignToProject(P.id)
    store.selectOrCreateRange(ISO, 555, 570)
    await store.assignToProject(P.id)

    const day = store.mergedBlocksByDay[ISO]
    expect(day).toHaveLength(1)
    expect(day[0].blocks).toHaveLength(2)
  })

  it('aggregator-blok gevolgd door leeg blok fuseren na opeenvolgende toewijzing', async () => {
    store.blocks = [
      makeAggregatorBlock(1, 9, 0, [{ title: 'VS Code', seconds: 300 }]),
      // 9:15 is leeg
    ]
    store.selectOrCreateRange(ISO, 540, 555)
    await store.assignToProject(P.id)
    store.selectOrCreateRange(ISO, 555, 570) // maakt temp-blok aan
    await store.assignToProject(P.id)

    const day = store.mergedBlocksByDay[ISO]
    expect(day).toHaveLength(1)
    expect(day[0].blocks).toHaveLength(2)
  })
})

// ── getTopActivitiesForIds ────────────────────────────────────────────────────
describe('activityBlocks store — getTopActivitiesForIds', () => {
  let store
  const P = { id: 1, name: 'Alpha', color: '#aaa' }

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useActivityBlocksStore()
  })

  it('geeft activiteiten terug voor een toegewezen blok', () => {
    store.blocks = [
      makeProjectBlock(1, 9, 0, P, [
        { title: 'VS Code', seconds: 600 },
        { title: 'Chrome',  seconds: 300 },
      ]),
    ]
    const result = store.getTopActivitiesForIds([1])
    expect(result).toHaveLength(2)
    expect(result[0].title).toBe('VS Code')
    expect(result[0].seconds).toBe(600)
  })

  it('sorteert op seconden aflopend en beperkt tot n=3', () => {
    store.blocks = [
      makeProjectBlock(1, 9, 0, P, [
        { title: 'A', seconds: 100 },
        { title: 'B', seconds: 400 },
        { title: 'C', seconds: 200 },
        { title: 'D', seconds: 300 },
      ]),
    ]
    const result = store.getTopActivitiesForIds([1])
    expect(result).toHaveLength(3)
    expect(result.map(r => r.title)).toEqual(['B', 'D', 'C'])
  })

  it('combineert activiteiten over meerdere blokken', () => {
    store.blocks = [
      makeProjectBlock(1, 9,  0, P, [{ title: 'VS Code', seconds: 300 }]),
      makeProjectBlock(2, 9, 15, P, [{ title: 'VS Code', seconds: 200 }, { title: 'Chrome', seconds: 100 }]),
    ]
    const result = store.getTopActivitiesForIds([1, 2])
    expect(result[0]).toEqual({ title: 'VS Code', seconds: 500 })
    expect(result[1]).toEqual({ title: 'Chrome',  seconds: 100 })
  })

  it('negeert blokken die niet in de ids-lijst staan', () => {
    store.blocks = [
      makeProjectBlock(1, 9,  0, P, [{ title: 'VS Code', seconds: 600 }]),
      makeProjectBlock(2, 9, 15, P, [{ title: 'Chrome',  seconds: 400 }]),
    ]
    const result = store.getTopActivitiesForIds([1])
    expect(result).toHaveLength(1)
    expect(result[0].title).toBe('VS Code')
  })

  it('geeft [] terug voor blokken zonder unique_activities', () => {
    store.blocks = [makeProjectBlock(1, 9, 0, P)]
    expect(store.getTopActivitiesForIds([1])).toEqual([])
  })
})

// ── declaredSecondsByDay ──────────────────────────────────────────────────────
describe('activityBlocks store — declaredSecondsByDay', () => {
  let store
  const P = { id: 1, name: 'Alpha', color: '#aaa' }

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useActivityBlocksStore()
    store.currentDate = ISO
  })

  it('telt wandkloktijd (ended_at − started_at) per dag voor toegewezen blokken', () => {
    store.blocks = [
      makeProjectBlock(1, 9,  0, P),  // ended_at = 9:15, total_seconds = 900
      makeProjectBlock(2, 9, 15, P),  // ended_at = 9:30, total_seconds = 900
    ]
    expect(store.declaredSecondsByDay[ISO]).toBe(1800)
  })

  it('gebruikt ended_at − started_at ook als total_seconds kleiner is (aggregator-overlap)', () => {
    store.blocks = [
      { ...makeProjectBlock(1, 9, 0, P), total_seconds: 60 }, // overlap 60s, slot 900s
    ]
    expect(store.declaredSecondsByDay[ISO]).toBe(900)
  })

  it('valt terug op total_seconds als ended_at ontbreekt', () => {
    const block = { ...makeProjectBlock(1, 9, 0, P), ended_at: undefined, total_seconds: 450 }
    store.blocks = [block]
    expect(store.declaredSecondsByDay[ISO]).toBe(450)
  })

  it('telt alleen toegewezen blokken mee', () => {
    store.blocks = [
      makeProjectBlock(1, 9,  0, P),
      makeAggregatorBlock(2, 9, 15, [{ title: 'VS Code', seconds: 300 }]),  // geen project
    ]
    expect(store.declaredSecondsByDay[ISO]).toBe(900)
  })

  it('groepeert per dag', () => {
    store.blocks = [
      makeProjectBlock(1, 9, 0, P),
      { ...makeProjectBlock(2, 9, 0, P), started_at: makeLocalISO('2024-01-16', 9, 0), ended_at: makeLocalISO('2024-01-16', 9, 15) },
    ]
    expect(store.declaredSecondsByDay[ISO]).toBe(900)
    expect(store.declaredSecondsByDay['2024-01-16']).toBe(900)
  })
})
