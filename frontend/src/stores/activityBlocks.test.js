import { setActivePinia, createPinia } from 'pinia'
import { describe, it, expect, beforeEach } from 'vitest'
import { useActivityBlocksStore } from './activityBlocks'
import { makeLocalISO, parseLocalDate, toLocalDateStr } from '@/utils/date'

// Constructs a block where startHour:startMin is in local time, so tests
// are timezone-agnostic.
const makeBlock = (id, iso, startHour, startMin, durationMin, project = null) => ({
  id,
  started_at: makeLocalISO(iso, startHour, startMin),
  total_seconds: durationMin * 60,
  dominant_title: `Block ${id}`,
  project,
})

const localMin = (started_at) => {
  const d = parseLocalDate(started_at)
  return d.getHours() * 60 + d.getMinutes()
}

const proj1 = { id: 1, name: 'Alpha', color: '#aaa' }
const proj2 = { id: 2, name: 'Beta',  color: '#bbb' }

const ISO = '2024-01-15'

describe('activityBlocks store', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useActivityBlocksStore()
  })

  // ══════════════════════════════════════════════════════════════
  // mergedBlocksByDay
  // ══════════════════════════════════════════════════════════════
  describe('mergedBlocksByDay', () => {
    it('adjacent same-project blocks are merged into one group', () => {
      store.blocks = [
        makeBlock(1, ISO, 9,  0, 60, proj1), // 9:00–10:00
        makeBlock(2, ISO, 10, 0, 60, proj1), // 10:00–11:00 — abutting
      ]
      const day = store.mergedBlocksByDay[ISO]
      expect(day).toHaveLength(1)
      expect(day[0].blocks).toHaveLength(2)
    })

    it('blocks from different projects are not merged', () => {
      store.blocks = [
        makeBlock(1, ISO, 9,  0, 60, proj1),
        makeBlock(2, ISO, 10, 0, 60, proj2),
      ]
      expect(store.mergedBlocksByDay[ISO]).toHaveLength(2)
    })

    it('unassigned (null project) blocks are never merged', () => {
      store.blocks = [
        makeBlock(1, ISO, 9,  0, 60, null),
        makeBlock(2, ISO, 10, 0, 60, null),
      ]
      expect(store.mergedBlocksByDay[ISO]).toHaveLength(2)
    })

    it('same-project blocks with a gap are not merged', () => {
      store.blocks = [
        makeBlock(1, ISO, 9,  0, 30, proj1), // ends 9:30
        makeBlock(2, ISO, 10, 0, 30, proj1), // starts 10:00 — gap
      ]
      expect(store.mergedBlocksByDay[ISO]).toHaveLength(2)
    })

    it('blocks on different days are returned separately', () => {
      store.blocks = [
        makeBlock(1, '2024-01-15', 9, 0, 60, proj1),
        makeBlock(2, '2024-01-16', 9, 0, 60, proj1),
      ]
      expect(store.mergedBlocksByDay['2024-01-15']).toHaveLength(1)
      expect(store.mergedBlocksByDay['2024-01-16']).toHaveLength(1)
    })
  })

  // ══════════════════════════════════════════════════════════════
  // moveBlocks
  // ══════════════════════════════════════════════════════════════
  describe('moveBlocks', () => {
    it('shifts a block by the given delta in minutes', () => {
      store.blocks = [makeBlock(1, ISO, 9, 0, 60)]
      store.moveBlocks([1], ISO, 30)
      expect(localMin(store.blocks[0].started_at)).toBe(9 * 60 + 30)
    })

    it('snaps unaligned delta to the nearest 15-minute slot', () => {
      store.blocks = [makeBlock(1, ISO, 9, 0, 60)]
      store.moveBlocks([1], ISO, 10) // 9:00 + 10 → snaps to 9:15
      expect(localMin(store.blocks[0].started_at)).toBe(9 * 60 + 15)
    })

    it('clamps so block cannot start past 23:45', () => {
      store.blocks = [makeBlock(1, ISO, 23, 45, 15)]
      store.moveBlocks([1], ISO, 60)
      expect(localMin(store.blocks[0].started_at)).toBe(23 * 60 + 45)
    })

    it('clamps so block cannot start before 00:00', () => {
      store.blocks = [makeBlock(1, ISO, 0, 0, 30)]
      store.moveBlocks([1], ISO, -30)
      expect(localMin(store.blocks[0].started_at)).toBe(0)
    })

    it('moves block to a different day', () => {
      store.blocks = [makeBlock(1, '2024-01-15', 9, 0, 60)]
      store.moveBlocks([1], '2024-01-16', 0)
      expect(toLocalDateStr(store.blocks[0].started_at)).toBe('2024-01-16')
      expect(localMin(store.blocks[0].started_at)).toBe(9 * 60)
    })

    it('ignores unknown block IDs silently', () => {
      store.blocks = [makeBlock(1, ISO, 9, 0, 60)]
      expect(() => store.moveBlocks([999], ISO, 30)).not.toThrow()
      expect(localMin(store.blocks[0].started_at)).toBe(9 * 60)
    })
  })

  // ══════════════════════════════════════════════════════════════
  // resizeRange
  // ══════════════════════════════════════════════════════════════
  describe('resizeRange', () => {
    it('bottom shrink: block is trimmed to the new end', () => {
      // Block 9:00–10:30 (540–630). Shrink bottom to 10:00 (600).
      store.blocks = [makeBlock(1, ISO, 9, 0, 90, null)]
      store.resizeRange(ISO, 540, 630, 540, 600, null)
      const b = store.blocks.find(x => x.id === 1)
      expect(b).toBeTruthy()
      expect(b.total_seconds).toBe((600 - 540) * 60)
    })

    it('top shrink: block start moves forward, duration shrinks', () => {
      // Block 9:00–10:30 (540–630). Shrink top to 9:30 (570).
      store.blocks = [makeBlock(1, ISO, 9, 0, 90, null)]
      store.resizeRange(ISO, 540, 630, 570, 630, null)
      const b = store.blocks.find(x => x.id === 1)
      expect(b).toBeTruthy()
      expect(localMin(b.started_at)).toBe(570)
      expect(b.total_seconds).toBe((630 - 570) * 60)
    })

    it('removes a block that falls entirely outside the new range', () => {
      // Two blocks: one inside new range, one outside.
      store.blocks = [
        makeBlock(1, ISO, 9,  0, 15, null), // 9:00–9:15 (540–555) — inside
        makeBlock(2, ISO, 10, 0, 60, null), // 10:00–11:00 (600–660) — outside
      ]
      // Old range 9:00–11:00, new range 9:00–9:15
      store.resizeRange(ISO, 540, 660, 540, 555, null)
      expect(store.blocks.find(b => b.id === 2)).toBeUndefined()
    })

    it('bottom extend: fills the uncovered gap with 15-min blocks', () => {
      // Block 9:00–10:00 (540–600). Extend bottom to 11:00 (660).
      store.blocks = [makeBlock(1, ISO, 9, 0, 60, null)]
      store.resizeRange(ISO, 540, 600, 540, 660, null)
      // Original stays; 4 new 15-min blocks fill 600–660.
      expect(store.blocks.length).toBe(5)
      store.blocks.filter(b => b.id !== 1).forEach(b => {
        expect(b.total_seconds).toBe(15 * 60)
      })
    })

    it('top extend: fills the uncovered gap with 15-min blocks', () => {
      // Block 10:00–11:00 (600–660). Extend top to 9:00 (540).
      store.blocks = [makeBlock(1, ISO, 10, 0, 60, null)]
      store.resizeRange(ISO, 600, 660, 540, 660, null)
      expect(store.blocks.length).toBe(5)
      store.blocks.filter(b => b.id !== 1).forEach(b => {
        expect(b.total_seconds).toBe(15 * 60)
      })
    })

    it('new blocks from a project-resize get the project assigned', () => {
      store.blocks = [makeBlock(1, ISO, 9, 0, 60, proj1)]
      // Extend bottom 10:00 → 10:30 (fill 600–630 with project 1 blocks)
      store.resizeRange(ISO, 540, 600, 540, 630, proj1.id)
      const newBlocks = store.blocks.filter(b => b.id !== 1)
      expect(newBlocks.length).toBeGreaterThan(0)
      newBlocks.forEach(b => expect(b.project?.id).toBe(proj1.id))
    })

    it('does not create duplicate blocks for already-covered slots', () => {
      // Two adjacent 15-min blocks covering 9:00–9:30. Resize confirms same range.
      store.blocks = [
        makeBlock(1, ISO, 9,  0, 15, null),
        makeBlock(2, ISO, 9, 15, 15, null),
      ]
      store.resizeRange(ISO, 540, 570, 540, 570, null)
      expect(store.blocks.length).toBe(2)
    })
  })

  // ══════════════════════════════════════════════════════════════
  // toggleMany
  // ══════════════════════════════════════════════════════════════
  describe('toggleMany', () => {
    it('selects blocks that are not yet selected', () => {
      store.blocks = [makeBlock(1, ISO, 9, 0, 30), makeBlock(2, ISO, 10, 0, 30)]
      store.toggleMany([1, 2])
      expect(store.selectedBlocks).toEqual(expect.arrayContaining([1, 2]))
    })

    it('deselects blocks when all are already selected', () => {
      store.blocks = [makeBlock(1, ISO, 9, 0, 30), makeBlock(2, ISO, 10, 0, 30)]
      store.selectedBlocks = [1, 2]
      store.toggleMany([1, 2])
      expect(store.selectedBlocks).toHaveLength(0)
    })
  })
})
