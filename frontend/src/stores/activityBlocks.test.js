// Tests voor de activityBlocks store — pure logica en state-mutaties.
// Geen API-aanroepen worden geverifieerd; zie activityBlocks.api.test.js daarvoor.
// De API wordt wel gemockt zodat acties die intern de API aanroepen (bijv.
// assignToProject) niet crashen; de nadruk ligt op de optimistische state-updates.
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { makeLocalISO, parseLocalDate, toLocalDateStr } from '@/utils/date'

vi.mock('@/api/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

import { useActivityBlocksStore } from './activityBlocks'

const ISO = '2024-01-15'

// ── Factories ────────────────────────────────────────────────────────────────

// Eenvoudig blok (handmatig aangemaakt, geen unique_activities).
const makeBlock = (id, iso, startHour, startMin, durationMin, project = null) => ({
  id,
  started_at:        makeLocalISO(iso, startHour, startMin),
  total_seconds:     durationMin * 60,
  dominant_title:    `Block ${id}`,
  project,
  unique_activities: [],
})

// Aggregator-blok: geen project, heeft unique_activities (AHK-import).
const makeAggregatorBlock = (id, startHour, startMin, activities) => ({
  id,
  started_at:        makeLocalISO(ISO, startHour, startMin),
  ended_at:          makeLocalISO(ISO, startHour, startMin + 15),
  total_seconds:     300,
  block_minutes:     15,
  dominant_title:    `Block ${id}`,
  project:           null,
  unique_activities: activities.map((ua, i) => ({
    id:            id * 100 + i,
    raw_title:     ua.title,
    app_name:      'Test',
    total_seconds: ua.seconds,
  })),
})

// Toegewezen blok: heeft project (en optioneel unique_activities).
const makeProjectBlock = (id, startHour, startMin, project, activities = []) => ({
  id,
  started_at:        makeLocalISO(ISO, startHour, startMin),
  ended_at:          makeLocalISO(ISO, startHour, startMin + 15),
  total_seconds:     900,
  block_minutes:     15,
  dominant_title:    project.name,
  project,
  unique_activities: activities.map((ua, i) => ({
    id:            id * 100 + i,
    raw_title:     ua.title,
    app_name:      'Test',
    total_seconds: ua.seconds,
  })),
})

const localMin = (started_at) => {
  const d = parseLocalDate(started_at)
  return d.getHours() * 60 + d.getMinutes()
}

const proj1 = { id: 1, name: 'Alpha', color: '#aaa' }
const proj2 = { id: 2, name: 'Beta',  color: '#bbb' }

let store

beforeEach(() => {
  setActivePinia(createPinia())
  store = useActivityBlocksStore()
})

// ══════════════════════════════════════════════════════════════
// mergedBlocksByDay
// ══════════════════════════════════════════════════════════════
describe('activityBlocks store — mergedBlocksByDay', () => {
  // ── Samenvoeglogica ──────────────────────────────────────────
  it('aaneengesloten blokken van hetzelfde project worden samengevoegd', () => {
    store.blocks = [
      makeBlock(1, ISO, 9,  0, 60, proj1), // 9:00–10:00
      makeBlock(2, ISO, 10, 0, 60, proj1), // 10:00–11:00, aansluitend
    ]
    const day = store.mergedBlocksByDay[ISO]
    expect(day).toHaveLength(1)
    expect(day[0].blocks).toHaveLength(2)
  })

  it('blokken van verschillende projecten worden niet samengevoegd', () => {
    store.blocks = [
      makeBlock(1, ISO, 9,  0, 60, proj1),
      makeBlock(2, ISO, 10, 0, 60, proj2),
    ]
    expect(store.mergedBlocksByDay[ISO]).toHaveLength(2)
  })

  it('zelfde project met een gat ertussen wordt niet samengevoegd', () => {
    store.blocks = [
      makeBlock(1, ISO, 9,  0, 30, proj1), // eindigt 9:30
      makeBlock(2, ISO, 10, 0, 30, proj1), // start 10:00 — gat
    ]
    expect(store.mergedBlocksByDay[ISO]).toHaveLength(2)
  })

  it('twee niet-toegewezen blokken worden niet met elkaar samengevoegd', () => {
    store.blocks = [
      makeBlock(1, ISO, 9,  0, 60, null),
      makeBlock(2, ISO, 10, 0, 60, null),
    ]
    expect(store.mergedBlocksByDay[ISO]).toHaveLength(2)
  })

  it('blokken op verschillende dagen worden per dag teruggegeven', () => {
    store.blocks = [
      makeBlock(1, '2024-01-15', 9, 0, 60, proj1),
      makeBlock(2, '2024-01-16', 9, 0, 60, proj1),
    ]
    expect(store.mergedBlocksByDay['2024-01-15']).toHaveLength(1)
    expect(store.mergedBlocksByDay['2024-01-16']).toHaveLength(1)
  })

  // ── Aggregator-filtering ─────────────────────────────────────
  it('aggregator-blokken zonder project worden uitgesloten', () => {
    store.blocks = [makeAggregatorBlock(1, 9, 0, [{ title: 'VS Code', seconds: 300 }])]
    expect(store.mergedBlocksByDay[ISO] ?? []).toHaveLength(0)
  })

  it('aggregator-blokken met een project worden opgenomen', () => {
    store.blocks = [{
      ...makeAggregatorBlock(1, 9, 0, [{ title: 'VS Code', seconds: 300 }]),
      project: proj1,
    }]
    expect(store.mergedBlocksByDay[ISO]).toHaveLength(1)
  })

  it('handmatig aangemaakte blokken zonder project worden opgenomen', () => {
    store.blocks = [makeBlock(1, ISO, 9, 0, 60, null)]
    expect(store.mergedBlocksByDay[ISO]).toHaveLength(1)
  })
})

// ══════════════════════════════════════════════════════════════
// moveBlocks
// ══════════════════════════════════════════════════════════════
describe('activityBlocks store — moveBlocks', () => {
  it('verschuift een blok met de opgegeven delta in minuten', () => {
    store.blocks = [makeBlock(1, ISO, 9, 0, 60)]
    store.moveBlocks([1], ISO, 30)
    expect(localMin(store.blocks[0].started_at)).toBe(9 * 60 + 30)
  })

  it('snapt niet-uitgelijnde delta naar het dichtstbijzijnde 15-minutenslot', () => {
    store.blocks = [makeBlock(1, ISO, 9, 0, 60)]
    store.moveBlocks([1], ISO, 10) // 9:00 + 10 → snapt naar 9:15
    expect(localMin(store.blocks[0].started_at)).toBe(9 * 60 + 15)
  })

  it('klampt zodat blok niet later dan 23:45 kan starten', () => {
    store.blocks = [makeBlock(1, ISO, 23, 45, 15)]
    store.moveBlocks([1], ISO, 60)
    expect(localMin(store.blocks[0].started_at)).toBe(23 * 60 + 45)
  })

  it('klampt zodat blok niet vóór 00:00 kan starten', () => {
    store.blocks = [makeBlock(1, ISO, 0, 0, 30)]
    store.moveBlocks([1], ISO, -30)
    expect(localMin(store.blocks[0].started_at)).toBe(0)
  })

  it('verplaatst blok naar een andere dag', () => {
    store.blocks = [makeBlock(1, '2024-01-15', 9, 0, 60)]
    store.moveBlocks([1], '2024-01-16', 0)
    expect(toLocalDateStr(store.blocks[0].started_at)).toBe('2024-01-16')
    expect(localMin(store.blocks[0].started_at)).toBe(9 * 60)
  })

  it('negeert onbekende block-IDs zonder fout', () => {
    store.blocks = [makeBlock(1, ISO, 9, 0, 60)]
    expect(() => store.moveBlocks([999], ISO, 30)).not.toThrow()
    expect(localMin(store.blocks[0].started_at)).toBe(9 * 60)
  })
})

// ══════════════════════════════════════════════════════════════
// resizeRange
// ══════════════════════════════════════════════════════════════
describe('activityBlocks store — resizeRange', () => {
  it('onderrand verkleinen: blok wordt afgekapt naar de nieuwe eindtijd', () => {
    // Blok 9:00–10:30 (540–630). Onderrand verkleinen naar 10:00 (600).
    store.blocks = [makeBlock(1, ISO, 9, 0, 90, null)]
    store.resizeRange(ISO, 540, 630, 540, 600, null)
    const b = store.blocks.find(x => x.id === 1)
    expect(b).toBeTruthy()
    expect(b.total_seconds).toBe((600 - 540) * 60)
  })

  it('bovenrand verkleinen: starttijd schuift op, duur neemt af', () => {
    // Blok 9:00–10:30 (540–630). Bovenrand verkleinen naar 9:30 (570).
    store.blocks = [makeBlock(1, ISO, 9, 0, 90, null)]
    store.resizeRange(ISO, 540, 630, 570, 630, null)
    const b = store.blocks.find(x => x.id === 1)
    expect(b).toBeTruthy()
    expect(localMin(b.started_at)).toBe(570)
    expect(b.total_seconds).toBe((630 - 570) * 60)
  })

  it('verwijdert een blok dat volledig buiten het nieuwe bereik valt', () => {
    store.blocks = [
      makeBlock(1, ISO, 9,  0, 15, null), // 9:00–9:15 (540–555) — binnen
      makeBlock(2, ISO, 10, 0, 60, null), // 10:00–11:00 (600–660) — buiten
    ]
    store.resizeRange(ISO, 540, 660, 540, 555, null)
    expect(store.blocks.find(b => b.id === 2)).toBeUndefined()
  })

  it('onderrand uitbreiden: vult het vrijgekomen gat met 15-min blokken', () => {
    // Blok 9:00–10:00 (540–600). Uitbreiden naar 11:00 (660).
    store.blocks = [makeBlock(1, ISO, 9, 0, 60, null)]
    store.resizeRange(ISO, 540, 600, 540, 660, null)
    expect(store.blocks.length).toBe(5) // origineel + 4 nieuwe
    store.blocks.filter(b => b.id !== 1).forEach(b => {
      expect(b.total_seconds).toBe(15 * 60)
    })
  })

  it('bovenrand uitbreiden: vult het vrijgekomen gat met 15-min blokken', () => {
    // Blok 10:00–11:00 (600–660). Uitbreiden naar 9:00 (540).
    store.blocks = [makeBlock(1, ISO, 10, 0, 60, null)]
    store.resizeRange(ISO, 600, 660, 540, 660, null)
    expect(store.blocks.length).toBe(5)
    store.blocks.filter(b => b.id !== 1).forEach(b => {
      expect(b.total_seconds).toBe(15 * 60)
    })
  })

  it('nieuwe blokken bij uitbreiding krijgen het project toegewezen', () => {
    store.blocks   = [makeBlock(1, ISO, 9, 0, 60, proj1)]
    store.projects = [proj1]
    store.resizeRange(ISO, 540, 600, 540, 630, proj1.id)
    const newBlocks = store.blocks.filter(b => b.id !== 1)
    expect(newBlocks.length).toBeGreaterThan(0)
    newBlocks.forEach(b => expect(b.project?.id).toBe(proj1.id))
  })

  it('maakt geen dubbele blokken aan voor al-gedekte slots', () => {
    store.blocks = [
      makeBlock(1, ISO, 9,  0, 15, null),
      makeBlock(2, ISO, 9, 15, 15, null),
    ]
    store.resizeRange(ISO, 540, 570, 540, 570, null)
    expect(store.blocks.length).toBe(2)
  })
})

// ══════════════════════════════════════════════════════════════
// selectOrCreateRange
// ══════════════════════════════════════════════════════════════
describe('activityBlocks store — selectOrCreateRange', () => {
  beforeEach(() => { store.currentDate = ISO })

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
      makeProjectBlock(2, 9, 15, proj1),
    ]
    store.selectOrCreateRange(ISO, 540, 570)
    expect(store.selectedBlocks).toContain(1)
    expect(store.selectedBlocks).not.toContain(2)
  })

  it('maakt een nieuw blok aan voor een leeg slot', () => {
    store.blocks = []
    store.selectOrCreateRange(ISO, 540, 555)
    expect(store.blocks).toHaveLength(1)
    expect(store.selectedBlocks).toHaveLength(1)
  })

  it('selecteert aggregator-blok naast nieuw blok bij leeg aangrenzend slot', () => {
    store.blocks = [makeAggregatorBlock(1, 9, 0, [{ title: 'VS Code', seconds: 300 }])]
    store.selectOrCreateRange(ISO, 540, 570)
    expect(store.selectedBlocks).toContain(1)
    expect(store.blocks).toHaveLength(2)         // nieuw blok voor 9:15
    expect(store.selectedBlocks).toHaveLength(2)
  })
})

// ══════════════════════════════════════════════════════════════
// blockEndMin — fallback en merge na toewijzing
// Controleert of ended_at / block_minutes correct worden gebruikt als fallback
// voor blockEndMin, zodat aangrenzende toewijzingen correct fuseren.
// ══════════════════════════════════════════════════════════════
describe('activityBlocks store — blockEndMin fallback', () => {
  beforeEach(() => {
    store.currentDate = ISO
    store.projects    = [proj1]
  })

  it('temp-blok uit selectOrCreateRange heeft ended_at gelijk aan het slot-einde', () => {
    store.blocks = []
    store.selectOrCreateRange(ISO, 540, 555)
    const tempBlock = store.blocks[0]
    expect(tempBlock.ended_at).toBeDefined()
    const e = parseLocalDate(tempBlock.ended_at)
    expect(e.getHours() * 60 + e.getMinutes()).toBe(555)
  })

  it('aggregator-blok zonder ended_at maar met block_minutes=15 fuseert correct na toewijzing', async () => {
    // Zonder fallback op block_minutes zou blockEndMin = started_at + total_seconds/60
    // = 540 + 300/60 = 545 (fout). Met fallback: 540 + 15 = 555 (correct).
    store.blocks = [
      {
        id: 1, started_at: makeLocalISO(ISO, 9, 0), total_seconds: 300, block_minutes: 15,
        dominant_title: 'VS Code', project: null,
        unique_activities: [{ id: 1, raw_title: 'VS Code', total_seconds: 300 }],
        // ended_at bewust weggelaten
      },
      {
        id: 2, started_at: makeLocalISO(ISO, 9, 15), total_seconds: 300, block_minutes: 15,
        dominant_title: 'Chrome', project: null,
        unique_activities: [{ id: 2, raw_title: 'Chrome', total_seconds: 200 }],
      },
    ]
    store.selectOrCreateRange(ISO, 540, 555)
    await store.assignToProject(proj1.id)
    store.selectOrCreateRange(ISO, 555, 570)
    await store.assignToProject(proj1.id)

    const day = store.mergedBlocksByDay[ISO]
    expect(day).toHaveLength(1)
    expect(day[0].blocks).toHaveLength(2)
  })
})

describe('activityBlocks store — merge na opeenvolgende project-toewijzing', () => {
  beforeEach(() => {
    store.currentDate = ISO
    store.projects    = [proj1]
  })

  it('twee aaneengesloten aggregator-blokken fuseren na opeenvolgende toewijzing', async () => {
    store.blocks = [
      makeAggregatorBlock(1, 9,  0, [{ title: 'VS Code', seconds: 300 }]),
      makeAggregatorBlock(2, 9, 15, [{ title: 'Chrome',  seconds: 200 }]),
    ]
    store.selectOrCreateRange(ISO, 540, 555)
    await store.assignToProject(proj1.id)
    store.selectOrCreateRange(ISO, 555, 570)
    await store.assignToProject(proj1.id)

    const day = store.mergedBlocksByDay[ISO]
    expect(day).toHaveLength(1)
    expect(day[0].blocks).toHaveLength(2)
  })

  it('aggregator-blok gevolgd door leeg blok fuseren na opeenvolgende toewijzing', async () => {
    store.blocks = [makeAggregatorBlock(1, 9, 0, [{ title: 'VS Code', seconds: 300 }])]
    store.selectOrCreateRange(ISO, 540, 555)
    await store.assignToProject(proj1.id)
    store.selectOrCreateRange(ISO, 555, 570) // maakt temp-blok aan voor 9:15
    await store.assignToProject(proj1.id)

    const day = store.mergedBlocksByDay[ISO]
    expect(day).toHaveLength(1)
    expect(day[0].blocks).toHaveLength(2)
  })
})

// ══════════════════════════════════════════════════════════════
// getTopActivities
// ══════════════════════════════════════════════════════════════
describe('activityBlocks store — getTopActivities', () => {
  beforeEach(() => { store.currentDate = ISO })

  it('geeft [] terug bij lege store', () => {
    expect(store.getTopActivities(ISO, 540, 555)).toEqual([])
  })

  it('sluit blokken met een project uit', () => {
    store.blocks = [{
      ...makeProjectBlock(1, 9, 0, proj1),
      unique_activities: [{ id: 1, raw_title: 'VS Code', app_name: 'VS Code', total_seconds: 600 }],
    }]
    expect(store.getTopActivities(ISO, 540, 555)).toEqual([])
  })

  it('sluit blokken zonder unique_activities uit', () => {
    store.blocks = [makeBlock(1, ISO, 9, 0, 60, null)]
    expect(store.getTopActivities(ISO, 540, 555)).toEqual([])
  })

  it('sluit blokken van een andere dag uit', () => {
    store.blocks = [{
      ...makeAggregatorBlock(1, 9, 0, [{ title: 'VS Code', seconds: 600 }]),
      started_at: makeLocalISO('2024-01-16', 9, 0),
    }]
    expect(store.getTopActivities(ISO, 540, 555)).toEqual([])
  })

  it('sluit blokken buiten het tijdsvenster uit', () => {
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
      { title: 'Chrome',  seconds: 200 },
      { title: 'VS Code', seconds: 600 },
      { title: 'Slack',   seconds: 100 },
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

  it('blok op de grensminuut valt binnen het venster', () => {
    store.blocks = [
      makeAggregatorBlock(1, 9, 0,  [{ title: 'A', seconds: 300 }]), // bStart=540
      makeAggregatorBlock(2, 9, 15, [{ title: 'B', seconds: 300 }]), // bStart=555
    ]
    // venster 540–570: beide vallen erin (540 < 570 en 555 < 570)
    expect(store.getTopActivities(ISO, 540, 570)).toHaveLength(2)
  })

  it('toont per-slot overlap-seconden voor dezelfde titel die twee slots overspant', () => {
    // Activiteit 12:29–12:34 → slot 12:15 krijgt 60 sec, slot 12:30 krijgt 240 sec
    store.blocks = [
      makeAggregatorBlock(1, 12, 15, [{ title: 'Inbox - Firefox', seconds: 60 }]),
      makeAggregatorBlock(2, 12, 30, [{ title: 'Inbox - Firefox', seconds: 240 }]),
    ]
    expect(store.getTopActivities(ISO, 735, 750)[0].seconds).toBe(60)
    expect(store.getTopActivities(ISO, 750, 765)[0].seconds).toBe(240)
  })
})

// ══════════════════════════════════════════════════════════════
// getTopActivitiesForIds
// ══════════════════════════════════════════════════════════════
describe('activityBlocks store — getTopActivitiesForIds', () => {
  it('geeft activiteiten terug voor een toegewezen blok', () => {
    store.blocks = [makeProjectBlock(1, 9, 0, proj1, [
      { title: 'VS Code', seconds: 600 },
      { title: 'Chrome',  seconds: 300 },
    ])]
    const result = store.getTopActivitiesForIds([1])
    expect(result).toHaveLength(2)
    expect(result[0].title).toBe('VS Code')
    expect(result[0].seconds).toBe(600)
  })

  it('sorteert op seconden aflopend en beperkt tot n=3', () => {
    store.blocks = [makeProjectBlock(1, 9, 0, proj1, [
      { title: 'A', seconds: 100 },
      { title: 'B', seconds: 400 },
      { title: 'C', seconds: 200 },
      { title: 'D', seconds: 300 },
    ])]
    const result = store.getTopActivitiesForIds([1])
    expect(result).toHaveLength(3)
    expect(result.map(r => r.title)).toEqual(['B', 'D', 'C'])
  })

  it('combineert activiteiten over meerdere blokken', () => {
    store.blocks = [
      makeProjectBlock(1, 9,  0, proj1, [{ title: 'VS Code', seconds: 300 }]),
      makeProjectBlock(2, 9, 15, proj1, [{ title: 'VS Code', seconds: 200 }, { title: 'Chrome', seconds: 100 }]),
    ]
    const result = store.getTopActivitiesForIds([1, 2])
    expect(result[0]).toEqual({ title: 'VS Code', seconds: 500 })
    expect(result[1]).toEqual({ title: 'Chrome',  seconds: 100 })
  })

  it('negeert blokken die niet in de ids-lijst staan', () => {
    store.blocks = [
      makeProjectBlock(1, 9,  0, proj1, [{ title: 'VS Code', seconds: 600 }]),
      makeProjectBlock(2, 9, 15, proj1, [{ title: 'Chrome',  seconds: 400 }]),
    ]
    const result = store.getTopActivitiesForIds([1])
    expect(result).toHaveLength(1)
    expect(result[0].title).toBe('VS Code')
  })

  it('geeft [] terug voor blokken zonder unique_activities', () => {
    store.blocks = [makeProjectBlock(1, 9, 0, proj1)]
    expect(store.getTopActivitiesForIds([1])).toEqual([])
  })
})

// ══════════════════════════════════════════════════════════════
// activityIndicatorsByDay
// ══════════════════════════════════════════════════════════════
describe('activityBlocks store — activityIndicatorsByDay', () => {
  beforeEach(() => { store.currentDate = ISO })

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
      makeProjectBlock(2, 9, 15, proj1),
    ]
    expect(store.activityIndicatorsByDay[ISO]).toHaveLength(1)
  })

  it('sluit blokken zonder unique_activities uit', () => {
    store.blocks = [makeBlock(1, ISO, 9, 0, 60, null)]
    expect(store.activityIndicatorsByDay[ISO]).toBeUndefined()
  })
})

// ══════════════════════════════════════════════════════════════
// declaredSecondsByDay
// ══════════════════════════════════════════════════════════════
describe('activityBlocks store — declaredSecondsByDay', () => {
  beforeEach(() => { store.currentDate = ISO })

  it('telt wandkloktijd (ended_at − started_at) per dag voor toegewezen blokken', () => {
    store.blocks = [
      makeProjectBlock(1, 9,  0, proj1), // ended_at = 9:15, wandkloktijd = 900s
      makeProjectBlock(2, 9, 15, proj1), // ended_at = 9:30, wandkloktijd = 900s
    ]
    expect(store.declaredSecondsByDay[ISO]).toBe(1800)
  })

  it('gebruikt ended_at − started_at ook als total_seconds kleiner is (aggregator-overlap)', () => {
    store.blocks = [{ ...makeProjectBlock(1, 9, 0, proj1), total_seconds: 60 }]
    expect(store.declaredSecondsByDay[ISO]).toBe(900)
  })

  it('valt terug op total_seconds als ended_at ontbreekt', () => {
    store.blocks = [{ ...makeProjectBlock(1, 9, 0, proj1), ended_at: undefined, total_seconds: 450 }]
    expect(store.declaredSecondsByDay[ISO]).toBe(450)
  })

  it('telt alleen toegewezen blokken mee', () => {
    store.blocks = [
      makeProjectBlock(1, 9,  0, proj1),
      makeAggregatorBlock(2, 9, 15, [{ title: 'VS Code', seconds: 300 }]), // geen project
    ]
    expect(store.declaredSecondsByDay[ISO]).toBe(900)
  })

  it('groepeert per dag', () => {
    store.blocks = [
      makeProjectBlock(1, 9, 0, proj1),
      { ...makeProjectBlock(2, 9, 0, proj1),
        started_at: makeLocalISO('2024-01-16', 9, 0),
        ended_at:   makeLocalISO('2024-01-16', 9, 15) },
    ]
    expect(store.declaredSecondsByDay[ISO]).toBe(900)
    expect(store.declaredSecondsByDay['2024-01-16']).toBe(900)
  })
})

// ══════════════════════════════════════════════════════════════
// toggleMany
// ══════════════════════════════════════════════════════════════
describe('activityBlocks store — toggleMany', () => {
  it('selecteert blokken die nog niet geselecteerd zijn', () => {
    store.blocks = [makeBlock(1, ISO, 9, 0, 30), makeBlock(2, ISO, 10, 0, 30)]
    store.toggleMany([1, 2])
    expect(store.selectedBlocks).toEqual(expect.arrayContaining([1, 2]))
  })

  it('deselecteert blokken als alle al geselecteerd zijn', () => {
    store.blocks = [makeBlock(1, ISO, 9, 0, 30), makeBlock(2, ISO, 10, 0, 30)]
    store.selectedBlocks = [1, 2]
    store.toggleMany([1, 2])
    expect(store.selectedBlocks).toHaveLength(0)
  })
})

// ══════════════════════════════════════════════════════════════
// selectBlocks
// ══════════════════════════════════════════════════════════════
describe('activityBlocks store — selectBlocks', () => {
  it('voegt ids toe aan selectedBlocks', () => {
    store.blocks = [makeBlock(1, ISO, 9, 0, 30), makeBlock(2, ISO, 10, 0, 30)]
    store.selectBlocks([1, 2])
    expect(store.selectedBlocks).toEqual(expect.arrayContaining([1, 2]))
  })

  it('voegt geen al-geselecteerde ids nogmaals toe', () => {
    store.blocks = [makeBlock(1, ISO, 9, 0, 30), makeBlock(2, ISO, 10, 0, 30)]
    store.selectedBlocks = [1]
    store.selectBlocks([1, 2])
    expect(store.selectedBlocks).toHaveLength(2)
    expect(store.selectedBlocks.filter(id => id === 1)).toHaveLength(1)
  })

  it('behoudt de bestaande selectie intact', () => {
    store.blocks = [makeBlock(1, ISO, 9, 0, 30), makeBlock(2, ISO, 10, 0, 30), makeBlock(3, ISO, 11, 0, 30)]
    store.selectedBlocks = [3]
    store.selectBlocks([1, 2])
    expect(store.selectedBlocks).toEqual(expect.arrayContaining([1, 2, 3]))
  })
})

// ══════════════════════════════════════════════════════════════
// cancelSelection
// ══════════════════════════════════════════════════════════════
describe('activityBlocks store — cancelSelection', () => {
  it('verwijdert geselecteerde temp-ID blokken uit de store', () => {
    const tempId = Date.now() * 1000 + 1
    store.blocks = [
      makeBlock(1, ISO, 9, 0, 30),
      { id: tempId, started_at: makeLocalISO(ISO, 10, 0), total_seconds: 900, dominant_title: 'Temp', project: null, unique_activities: [] },
    ]
    store.selectedBlocks = [1, tempId]
    store.cancelSelection()
    expect(store.blocks.some(b => b.id === tempId)).toBe(false)
  })

  it('behoudt echte blokken (id < 1e12) in de store', () => {
    const tempId = Date.now() * 1000 + 1
    store.blocks = [
      makeBlock(1, ISO, 9, 0, 30),
      { id: tempId, started_at: makeLocalISO(ISO, 10, 0), total_seconds: 900, dominant_title: 'Temp', project: null, unique_activities: [] },
    ]
    store.selectedBlocks = [1, tempId]
    store.cancelSelection()
    expect(store.blocks.some(b => b.id === 1)).toBe(true)
  })

  it('leegt de selectie', () => {
    store.blocks = [makeBlock(1, ISO, 9, 0, 30)]
    store.selectedBlocks = [1]
    store.cancelSelection()
    expect(store.selectedBlocks).toHaveLength(0)
  })

  it('verwijdert alleen temp-ID blokken die ook geselecteerd zijn', () => {
    const tempId = Date.now() * 1000 + 1
    store.blocks = [
      makeBlock(1, ISO, 9, 0, 30),
      { id: tempId, started_at: makeLocalISO(ISO, 10, 0), total_seconds: 900, dominant_title: 'Temp', project: null, unique_activities: [] },
    ]
    store.selectedBlocks = [1] // tempId niet geselecteerd
    store.cancelSelection()
    expect(store.blocks.some(b => b.id === tempId)).toBe(true)
  })
})

// ══════════════════════════════════════════════════════════════
// gridStartHour
// ══════════════════════════════════════════════════════════════
describe('activityBlocks store — gridStartHour', () => {
  beforeEach(() => { localStorage.removeItem('grid_start_hour') })

  it('heeft standaard 7 als begintijd', () => {
    expect(store.gridStartHour).toBe(7)
  })

  it('setGridStartHour werkt de state bij', () => {
    store.setGridStartHour(8)
    expect(store.gridStartHour).toBe(8)
  })

  it('setGridStartHour slaat de waarde op in localStorage', () => {
    store.setGridStartHour(9)
    expect(localStorage.getItem('grid_start_hour')).toBe('9')
  })
})
