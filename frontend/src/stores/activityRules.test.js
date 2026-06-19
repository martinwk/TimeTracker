// Tests voor de activityRules store — API-interacties en state-mutaties.
// Axios wordt gemockt zodat er geen echte backend nodig is.
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
import { useActivityRulesStore } from './activityRules'

const makeRule = (id, matchField = 'app_name', matchValue = 'VS Code', projectId = 5, priority = 10) => ({
  id,
  project: projectId,
  match_field: matchField,
  match_field_display: 'Applicatienaam (exact)',
  match_value: matchValue,
  priority,
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
})

describe('activityRules store', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useActivityRulesStore()
    vi.clearAllMocks()
  })

  // ── fetchRules ─────────────────────────────────────────────────────────────
  describe('fetchRules', () => {
    it('roept GET /activities/activity-rules/ aan', async () => {
      api.get.mockResolvedValue({ data: { results: [] } })
      await store.fetchRules()
      expect(api.get).toHaveBeenCalledWith('/activities/activity-rules/')
    })

    it('slaat opgehaalde regels op in store.rules', async () => {
      const rules = [makeRule(1), makeRule(2, 'title_contains', 'GitHub', 5, 20)]
      api.get.mockResolvedValue({ data: { results: rules } })
      await store.fetchRules()
      expect(store.rules).toHaveLength(2)
      expect(store.rules[0].id).toBe(1)
    })

    it('vervangt de bestaande lijst volledig', async () => {
      store.rules = [makeRule(99)]
      api.get.mockResolvedValue({ data: { results: [makeRule(1)] } })
      await store.fetchRules()
      expect(store.rules).toHaveLength(1)
      expect(store.rules[0].id).toBe(1)
    })

    it('zet isLoading true tijdens fetch en false daarna', async () => {
      let resolve
      api.get.mockReturnValue(new Promise(r => { resolve = r }))
      const promise = store.fetchRules()
      expect(store.isLoading).toBe(true)
      resolve({ data: { results: [] } })
      await promise
      expect(store.isLoading).toBe(false)
    })

    it('slaat foutmelding op bij mislukte fetch', async () => {
      api.get.mockRejectedValue({ response: { data: { detail: 'Niet gevonden' } } })
      await store.fetchRules()
      expect(store.error).toBeTruthy()
      expect(store.isLoading).toBe(false)
    })

    it('accepteert ook een directe array als response (zonder results-wrapper)', async () => {
      api.get.mockResolvedValue({ data: [makeRule(1)] })
      await store.fetchRules()
      expect(store.rules).toHaveLength(1)
    })
  })

  // ── createRule ─────────────────────────────────────────────────────────────
  describe('createRule', () => {
    it('roept POST /activities/activity-rules/ aan met de opgegeven gegevens', async () => {
      const serverRule = makeRule(10)
      api.post.mockResolvedValue({ data: serverRule })
      await store.createRule({ project: 5, match_field: 'app_name', match_value: 'VS Code', priority: 10, is_active: true })
      expect(api.post).toHaveBeenCalledWith('/activities/activity-rules/', {
        project: 5, match_field: 'app_name', match_value: 'VS Code', priority: 10, is_active: true,
      })
    })

    it('voegt de nieuwe regel toe aan store.rules', async () => {
      const serverRule = makeRule(10)
      api.post.mockResolvedValue({ data: serverRule })
      await store.createRule({ project: 5, match_field: 'app_name', match_value: 'VS Code', priority: 10, is_active: true })
      expect(store.rules.some(r => r.id === 10)).toBe(true)
    })

    it('geeft de nieuwe regel terug', async () => {
      const serverRule = makeRule(10)
      api.post.mockResolvedValue({ data: serverRule })
      const result = await store.createRule({ project: 5, match_field: 'app_name', match_value: 'VS Code', priority: 10, is_active: true })
      expect(result.id).toBe(10)
    })

    it('slaat foutmelding op bij mislukte POST', async () => {
      api.post.mockRejectedValue({ response: { data: { match_value: ['Dit veld is verplicht'] } } })
      await store.createRule({ project: 5, match_field: 'app_name', match_value: '', priority: 10, is_active: true })
      expect(store.error).toBeTruthy()
    })

    it('geeft null terug bij een fout', async () => {
      api.post.mockRejectedValue(new Error('Network error'))
      const result = await store.createRule({ project: 5, match_field: 'app_name', match_value: 'X', priority: 10, is_active: true })
      expect(result).toBeNull()
    })
  })

  // ── updateRule ─────────────────────────────────────────────────────────────
  describe('updateRule', () => {
    it('roept PATCH /activities/activity-rules/{id}/ aan met de gewijzigde gegevens', async () => {
      store.rules = [makeRule(5)]
      api.patch.mockResolvedValue({ data: makeRule(5, 'app_name', 'Notepad') })
      await store.updateRule(5, { match_value: 'Notepad' })
      expect(api.patch).toHaveBeenCalledWith('/activities/activity-rules/5/', { match_value: 'Notepad' })
    })

    it('past de regel bij in store.rules', async () => {
      store.rules = [makeRule(5, 'app_name', 'VS Code')]
      api.patch.mockResolvedValue({ data: makeRule(5, 'app_name', 'Notepad') })
      await store.updateRule(5, { match_value: 'Notepad' })
      const updated = store.rules.find(r => r.id === 5)
      expect(updated.match_value).toBe('Notepad')
    })

    it('slaat foutmelding op bij mislukte PATCH', async () => {
      store.rules = [makeRule(5)]
      api.patch.mockRejectedValue(new Error('Network error'))
      await store.updateRule(5, { match_value: 'Fout' })
      expect(store.error).toBeTruthy()
    })
  })

  // ── deleteRule ─────────────────────────────────────────────────────────────
  describe('deleteRule', () => {
    it('roept DELETE /activities/activity-rules/{id}/ aan', async () => {
      store.rules = [makeRule(7)]
      api.delete.mockResolvedValue({})
      await store.deleteRule(7)
      expect(api.delete).toHaveBeenCalledWith('/activities/activity-rules/7/')
    })

    it('verwijdert de regel uit store.rules', async () => {
      store.rules = [makeRule(7), makeRule(8, 'title_contains', 'GitHub', 5, 20)]
      api.delete.mockResolvedValue({})
      await store.deleteRule(7)
      expect(store.rules.find(r => r.id === 7)).toBeUndefined()
      expect(store.rules.find(r => r.id === 8)).toBeDefined()
    })

    it('slaat foutmelding op bij mislukte DELETE', async () => {
      store.rules = [makeRule(7)]
      api.delete.mockRejectedValue({ response: { status: 500, data: { detail: 'Serverfout' } } })
      await store.deleteRule(7)
      expect(store.error).toBeTruthy()
    })

    it('laat de regel in de store staan bij een fout', async () => {
      store.rules = [makeRule(7)]
      api.delete.mockRejectedValue(new Error('Network error'))
      await store.deleteRule(7)
      expect(store.rules.find(r => r.id === 7)).toBeDefined()
    })
  })

  // ── applyRules ─────────────────────────────────────────────────────────────
  describe('applyRules', () => {
    it('roept POST /activities/apply-rules/ aan met de opgegeven datums', async () => {
      api.post.mockResolvedValue({ data: { applied: 5 } })
      await store.applyRules('2026-06-17', '2026-06-23')
      expect(api.post).toHaveBeenCalledWith('/activities/apply-rules/', {
        date_from: '2026-06-17',
        date_to: '2026-06-23',
      })
    })

    it('geeft de response data terug', async () => {
      api.post.mockResolvedValue({ data: { applied: 3 } })
      const result = await store.applyRules('2026-06-17', '2026-06-23')
      expect(result).toEqual({ applied: 3 })
    })

    it('slaat foutmelding op bij mislukte POST', async () => {
      api.post.mockRejectedValue(new Error('Network error'))
      await store.applyRules('2026-06-17', '2026-06-23')
      expect(store.error).toBeTruthy()
    })

    it('geeft null terug bij een fout', async () => {
      api.post.mockRejectedValue(new Error('Network error'))
      const result = await store.applyRules('2026-06-17', '2026-06-23')
      expect(result).toBeNull()
    })
  })

  // ── clearError ─────────────────────────────────────────────────────────────
  describe('clearError', () => {
    it('wist de foutmelding', () => {
      store.error = 'Iets ging mis'
      store.clearError()
      expect(store.error).toBeNull()
    })
  })
})
