// Tests voor de API-koppeling van de activityBlocks store.
// Axios wordt gemockt zodat er geen echte backend nodig is.
//
// Dit zijn unit tests: ze verifiëren dat de store de juiste API-aanroepen doet
// met de juiste parameters, maar raken de echte backend niet aan. Ze beschermen
// dus tegen regressies in store-logica (URL's, payloads, state-mutaties), niet
// tegen contract-drift tussen frontend en backend. Voor dat laatste zijn er
// aparte backend API-tests in backend/apps/activities/tests.py die de exacte
// JSON-shape van de responses vastleggen.
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/api', () => ({
  default: {
    get:    vi.fn(),
    post:   vi.fn(),
    patch:  vi.fn(),
    delete: vi.fn(),
  },
}))

import api from '@/api/api'
import { useActivityBlocksStore } from './activityBlocks'
import { makeLocalISO } from '@/utils/date'

const MONDAY = '2024-01-15'

const apiBlock = (id, iso, startHour, durationMin, project = null) => ({
  id,
  started_at:     `${iso}T${String(startHour).padStart(2, '0')}:00:00Z`,
  total_seconds:  durationMin * 60,
  dominant_title: `Blok ${id}`,
  project:        project ? { id: project.id, name: project.name, color: project.color } : null,
})

describe('activityBlocks store — API', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useActivityBlocksStore()
    store.currentDate = MONDAY
    vi.clearAllMocks()
  })

  // ── fetchWeekBlocks ────────────────────────────────────────────────────────
  describe('fetchWeekBlocks', () => {
    it('roept /activity-blocks/ aan met date_from en date_to voor de hele week', async () => {
      api.get.mockResolvedValue({ data: { results: [] } })
      await store.fetchWeekBlocks()
      expect(api.get).toHaveBeenCalledWith('/activities/activity-blocks/', {
        params: { date_from: '2024-01-15', date_to: '2024-01-21' },
      })
    })

    it('slaat opgehaalde blokken op in store.blocks', async () => {
      const blocks = [apiBlock(1, '2024-01-15', 9, 60), apiBlock(2, '2024-01-15', 11, 30)]
      api.get.mockResolvedValue({ data: { results: blocks } })
      await store.fetchWeekBlocks()
      expect(store.blocks).toHaveLength(2)
      expect(store.blocks[0].id).toBe(1)
    })

    it('zet isLoading true tijdens fetch en false daarna', async () => {
      let resolveGet
      api.get.mockReturnValue(new Promise(r => { resolveGet = r }))
      const fetchPromise = store.fetchWeekBlocks()
      expect(store.isLoading).toBe(true)
      resolveGet({ data: { results: [] } })
      await fetchPromise
      expect(store.isLoading).toBe(false)
    })

    it('slaat foutmelding op bij mislukte fetch', async () => {
      api.get.mockRejectedValue({ response: { data: { error: 'Server fout' } } })
      await store.fetchWeekBlocks()
      expect(store.error).toBe('Server fout')
      expect(store.isLoading).toBe(false)
    })

    it('wist de selectie na een succesvolle fetch', async () => {
      store.selectedBlocks = [1, 2]
      api.get.mockResolvedValue({ data: { results: [] } })
      await store.fetchWeekBlocks()
      expect(store.selectedBlocks).toHaveLength(0)
    })

    it('accepteert ook een directe array als response (zonder results-wrapper)', async () => {
      const blocks = [apiBlock(1, '2024-01-15', 9, 60)]
      api.get.mockResolvedValue({ data: blocks })
      await store.fetchWeekBlocks()
      expect(store.blocks).toHaveLength(1)
    })
  })

  // ── assignToProject ────────────────────────────────────────────────────────
  describe('assignToProject', () => {
    it('roept bulk-assign endpoint aan met geselecteerde block_ids', async () => {
      store.blocks = [
        { id: 1, started_at: '2024-01-15T09:00:00Z', total_seconds: 3600, dominant_title: 'X', project: null },
        { id: 2, started_at: '2024-01-15T10:00:00Z', total_seconds: 1800, dominant_title: 'Y', project: null },
      ]
      store.selectedBlocks = [1, 2]
      store.projects = [{ id: 5, name: 'Test', color: '#abc' }]

      api.post.mockResolvedValue({ data: { assigned: 2 } })
      await store.assignToProject(5)

      expect(api.post).toHaveBeenCalledWith('/activities/activity-blocks/assign/', {
        block_ids: [1, 2],
        project_id: 5,
      })
    })

    it('past store.blocks lokaal bij na succesvolle assign', async () => {
      const project = { id: 5, name: 'Test', color: '#abc' }
      store.blocks = [
        { id: 1, started_at: '2024-01-15T09:00:00Z', total_seconds: 3600, dominant_title: 'X', project: null },
      ]
      store.selectedBlocks = [1]
      store.projects = [project]

      api.post.mockResolvedValue({ data: { assigned: 1 } })
      await store.assignToProject(5)

      expect(store.blocks[0].project?.id).toBe(5)
      expect(store.selectedBlocks).toHaveLength(0)
    })

    it('herlaadt blokken bij een API-fout en toont foutmelding', async () => {
      store.blocks = [
        { id: 1, started_at: '2024-01-15T09:00:00Z', total_seconds: 3600, dominant_title: 'X', project: null },
      ]
      store.selectedBlocks = [1]
      store.projects = [{ id: 5, name: 'Test', color: '#abc' }]

      api.post.mockRejectedValue({ response: { data: { error: 'Toewijzen mislukt' } } })
      // fetchWeekBlocks wordt ook aangeroepen bij rollback
      api.get.mockResolvedValue({ data: { results: [] } })
      await store.assignToProject(5)

      expect(store.error).toBe('Fout bij toewijzen project')
    })
  })

  // ── moveBlocks ─────────────────────────────────────────────────────────────
  describe('moveBlocks', () => {
    const block = {
      id: 1,
      started_at: '2024-01-15T09:00:00Z',
      total_seconds: 3600,
      dominant_title: 'Test',
      project: null,
    }

    it('stuurt PATCH naar /activity-blocks/{id}/ voor elk verplaatst blok', async () => {
      store.blocks = [{ ...block }]
      api.patch.mockResolvedValue({ data: { ...block, started_at: '2024-01-15T09:30:00Z' } })

      await store.moveBlocks([1], '2024-01-15', 30)

      expect(api.patch).toHaveBeenCalledTimes(1)
      expect(api.patch).toHaveBeenCalledWith(
        '/activities/activity-blocks/1/',
        expect.objectContaining({ started_at: expect.any(String) }),
      )
    })

    it('werkt store.blocks bij met de serverrespons', async () => {
      store.blocks = [{ ...block }]
      const updated = { ...block, started_at: '2024-01-16T09:00:00Z' }
      api.patch.mockResolvedValue({ data: updated })

      await store.moveBlocks([1], '2024-01-16', 0)

      expect(store.blocks[0].started_at).toBe('2024-01-16T09:00:00Z')
    })

    it('herlaadt blokken bij API-fout', async () => {
      store.blocks = [{ ...block }]
      api.patch.mockRejectedValue(new Error('Network error'))
      api.get.mockResolvedValue({ data: { results: [] } })

      await store.moveBlocks([1], '2024-01-15', 30)

      expect(api.get).toHaveBeenCalled() // fetchWeekBlocks aangeroepen
    })
  })

  // ── fetchProjects ──────────────────────────────────────────────────────────
  describe('fetchProjects', () => {
    it('roept /projects/ aan en slaat projecten op', async () => {
      const projects = [{ id: 10, name: 'Nieuw', color: '#abc', is_active: true, notes: '' }]
      api.get.mockResolvedValue({ data: { results: projects } })
      await store.fetchProjects()
      expect(api.get).toHaveBeenCalledWith('/projects/')
      expect(store.projects).toHaveLength(1)
      expect(store.projects[0].name).toBe('Nieuw')
    })

    it('vervangt de bestaande projectenlijst volledig', async () => {
      api.get.mockResolvedValue({
        data: { results: [{ id: 99, name: 'Enige', color: '#000' }] },
      })
      await store.fetchProjects()
      expect(store.projects).toHaveLength(1)
      expect(store.projects[0].id).toBe(99)
    })
  })

  // ── createBlock ────────────────────────────────────────────────────────────
  describe('createBlock', () => {
    it('stuurt POST naar /activity-blocks/ met de juiste velden', async () => {
      store.projects = [{ id: 3, name: 'Design', color: '#ec4899' }]
      const serverBlock = {
        id: 42,
        started_at: '2024-01-15T09:00:00Z',
        total_seconds: 900,
        dominant_title: 'Design',
        project: { id: 3, name: 'Design', color: '#ec4899' },
      }
      api.post.mockResolvedValue({ data: serverBlock })

      await store.createBlock({ iso: '2024-01-15', hour: 9, minute: 0 }, 3)

      expect(api.post).toHaveBeenCalledWith(
        '/activities/activity-blocks/',
        expect.objectContaining({
          started_at: expect.any(String),
          total_seconds: 900,
          project_id: 3,
        }),
      )
    })

    it('vervangt het tijdelijke blok met het serverblok na POST', async () => {
      store.projects = [{ id: 3, name: 'Design', color: '#ec4899' }]
      const serverBlock = {
        id: 99,
        started_at: '2024-01-15T09:00:00Z',
        total_seconds: 900,
        dominant_title: 'Design',
        project: { id: 3, name: 'Design', color: '#ec4899' },
      }
      api.post.mockResolvedValue({ data: serverBlock })

      await store.createBlock({ iso: '2024-01-15', hour: 9, minute: 0 }, 3)

      // Na POST moet het blok het server-id hebben, niet het tijdelijke Date.now()-id
      expect(store.blocks.some(b => b.id === 99)).toBe(true)
    })

    it('verwijdert het tijdelijke blok bij een POST-fout', async () => {
      store.projects = [{ id: 3, name: 'Design', color: '#ec4899' }]
      api.post.mockRejectedValue(new Error('Network error'))

      await store.createBlock({ iso: '2024-01-15', hour: 9, minute: 0 }, 3)

      // Na mislukte POST mag er geen blok in de store overblijven
      expect(store.blocks).toHaveLength(0)
    })

    it('werkt ook zonder projectId (null project)', async () => {
      const serverBlock = {
        id: 55,
        started_at: '2024-01-15T10:00:00Z',
        total_seconds: 900,
        dominant_title: 'Nieuw blok',
        project: null,
      }
      api.post.mockResolvedValue({ data: serverBlock })

      await store.createBlock({ iso: '2024-01-15', hour: 10, minute: 0 }, null)

      expect(api.post).toHaveBeenCalledWith(
        '/activities/activity-blocks/',
        expect.objectContaining({ total_seconds: 900 }),
      )
      expect(store.blocks.some(b => b.id === 55)).toBe(true)
    })
  })

  // ── applyRules ─────────────────────────────────────────────────────────────
  describe('applyRules', () => {
    it('stuurt POST naar /activities/apply-rules/', async () => {
      api.post.mockResolvedValue({ data: { blocks_assigned: 3, blocks_processed: 10 } })
      api.get.mockResolvedValue({ data: { results: [] } })

      await store.applyRules()

      expect(api.post).toHaveBeenCalledWith('/activities/apply-rules/', expect.any(Object))
    })

    it('herlaadt blokken na succesvol toepassen van regels', async () => {
      api.post.mockResolvedValue({ data: { blocks_assigned: 2, blocks_processed: 5 } })
      api.get.mockResolvedValue({ data: { results: [] } })

      await store.applyRules()

      expect(api.get).toHaveBeenCalled()
    })

    it('zet isLoading true tijdens uitvoering en false daarna', async () => {
      let resolvePost
      api.post.mockReturnValue(new Promise(r => { resolvePost = r }))

      const promise = store.applyRules()
      expect(store.isLoading).toBe(true)
      resolvePost({ data: { blocks_assigned: 0, blocks_processed: 0 } })
      api.get.mockResolvedValue({ data: { results: [] } })
      await promise
      expect(store.isLoading).toBe(false)
    })

    it('toont foutmelding bij API-fout', async () => {
      api.post.mockRejectedValue(new Error('Server fout'))

      await store.applyRules()

      expect(store.error).toBe('Fout bij auto-toewijzen')
      expect(store.isLoading).toBe(false)
    })

    it('stuurt de huidige week mee als datumbereik', async () => {
      store.currentDate = '2024-01-15'
      api.post.mockResolvedValue({ data: { blocks_assigned: 0, blocks_processed: 0 } })
      api.get.mockResolvedValue({ data: { results: [] } })

      await store.applyRules()

      expect(api.post).toHaveBeenCalledWith(
        '/activities/apply-rules/',
        expect.objectContaining({
          date_from: '2024-01-15',
          date_to:   '2024-01-21',
        }),
      )
    })
  })

  // ── resizeRange ────────────────────────────────────────────────────────────
  describe('resizeRange — API', () => {
    it('stuurt POST naar /activity-blocks/bulk/ met blocks en deleted_ids', async () => {
      store.blocks = [
        {
          id: 10,
          started_at: makeLocalISO(MONDAY, 9, 0),
          total_seconds: 3600,
          dominant_title: 'Backend',
          project: { id: 2, name: 'Backend', color: '#f59e0b' },
        },
      ]
      store.projects = [{ id: 2, name: 'Backend', color: '#f59e0b' }]
      api.post.mockResolvedValue({ data: { created: 0, updated: 1, deleted: 0, blocks: [] } })

      // Verklein het blok aan de onderkant (van 9:00-10:00 naar 9:00-9:30)
      store.resizeRange(MONDAY, 540, 600, 540, 570, 2)

      expect(api.post).toHaveBeenCalledWith(
        '/activities/activity-blocks/bulk/',
        expect.objectContaining({
          blocks:      expect.any(Array),
          deleted_ids: expect.any(Array),
        }),
      )
    })

    it('stuurt verwijderd backend-blok mee als deleted_id bij shrink', async () => {
      // Twee blokken: id 10 (9:00-9:30) en id 11 (9:30-10:00), beide Backend project
      store.blocks = [
        { id: 10, started_at: makeLocalISO(MONDAY, 9, 0),  total_seconds: 1800, dominant_title: 'Backend', project: { id: 2, name: 'Backend', color: '#f59e0b' } },
        { id: 11, started_at: makeLocalISO(MONDAY, 9, 30), total_seconds: 1800, dominant_title: 'Backend', project: { id: 2, name: 'Backend', color: '#f59e0b' } },
      ]
      store.projects = [{ id: 2, name: 'Backend', color: '#f59e0b' }]
      api.post.mockResolvedValue({ data: { created: 0, updated: 1, deleted: 1, blocks: [] } })

      // Verklein van 9:00-10:00 naar 9:00-9:30 → blok 11 valt buiten nieuw bereik
      store.resizeRange(MONDAY, 540, 600, 540, 570, 2)

      const call = api.post.mock.calls[0][1]
      expect(call.deleted_ids).toContain(11)
    })

    it('stuurt geen temp-ids mee als deleted_id', async () => {
      // Blok met groot temp-ID (zoals Date.now() * 1000 + m)
      const tempId = Date.now() * 1000 + 540
      store.blocks = [
        { id: tempId, started_at: makeLocalISO(MONDAY, 9, 0),  total_seconds: 1800, dominant_title: 'Backend', project: { id: 2, name: 'Backend', color: '#f59e0b' } },
        { id: 11,     started_at: makeLocalISO(MONDAY, 9, 30), total_seconds: 1800, dominant_title: 'Backend', project: { id: 2, name: 'Backend', color: '#f59e0b' } },
      ]
      store.projects = [{ id: 2, name: 'Backend', color: '#f59e0b' }]
      api.post.mockResolvedValue({ data: { created: 0, updated: 1, deleted: 0, blocks: [] } })

      // Verklein zodat het temp-blok buiten het bereik valt (9:30-10:00 → nieuw bereik)
      store.resizeRange(MONDAY, 540, 600, 570, 600, 2)

      const call = api.post.mock.calls[0][1]
      expect(call.deleted_ids).not.toContain(tempId)
      expect(call.deleted_ids).toHaveLength(0)
    })

    it('herlaadt blokken bij een API-fout van resizeRange', async () => {
      store.blocks = [
        {
          id: 10,
          started_at: '2024-01-15T09:00:00Z',
          total_seconds: 3600,
          dominant_title: 'Backend',
          project: { id: 2, name: 'Backend', color: '#f59e0b' },
        },
      ]
      store.projects = [{ id: 2, name: 'Backend', color: '#f59e0b' }]
      api.post.mockRejectedValue(new Error('Network error'))
      api.get.mockResolvedValue({ data: { results: [] } })

      await store.resizeRange('2024-01-15', 540, 600, 540, 570, 2)

      expect(api.get).toHaveBeenCalled()
    })
  })
})
