// Tests voor de projects store — API-interacties en state-mutaties.
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
import { useProjectsStore } from './projects'

const makeProject = (id, name, isActive = true) => ({
  id,
  name,
  color: '#4F86C6',
  is_active: isActive,
  notes: '',
  created_at: '2024-01-01T00:00:00Z',
})

describe('projects store', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useProjectsStore()
    vi.clearAllMocks()
  })

  // ── fetchProjects ──────────────────────────────────────────────────────────
  describe('fetchProjects', () => {
    it('roept GET /projects/ aan', async () => {
      api.get.mockResolvedValue({ data: { results: [] } })
      await store.fetchProjects()
      expect(api.get).toHaveBeenCalledWith('/projects/')
    })

    it('slaat opgehaalde projecten op in store.projects', async () => {
      const projects = [makeProject(1, 'Alpha'), makeProject(2, 'Beta')]
      api.get.mockResolvedValue({ data: { results: projects } })
      await store.fetchProjects()
      expect(store.projects).toHaveLength(2)
      expect(store.projects[0].name).toBe('Alpha')
    })

    it('vervangt de bestaande projectenlijst volledig', async () => {
      store.projects = [makeProject(99, 'Oud')]
      api.get.mockResolvedValue({ data: { results: [makeProject(1, 'Nieuw')] } })
      await store.fetchProjects()
      expect(store.projects).toHaveLength(1)
      expect(store.projects[0].name).toBe('Nieuw')
    })

    it('zet isLoading true tijdens fetch en false daarna', async () => {
      let resolve
      api.get.mockReturnValue(new Promise(r => { resolve = r }))
      const promise = store.fetchProjects()
      expect(store.isLoading).toBe(true)
      resolve({ data: { results: [] } })
      await promise
      expect(store.isLoading).toBe(false)
    })

    it('slaat foutmelding op bij mislukte fetch', async () => {
      api.get.mockRejectedValue({ response: { data: { detail: 'Niet gevonden' } } })
      await store.fetchProjects()
      expect(store.error).toBeTruthy()
      expect(store.isLoading).toBe(false)
    })

    it('accepteert ook een directe array als response (zonder results-wrapper)', async () => {
      api.get.mockResolvedValue({ data: [makeProject(1, 'Alpha')] })
      await store.fetchProjects()
      expect(store.projects).toHaveLength(1)
    })
  })

  // ── createProject ──────────────────────────────────────────────────────────
  describe('createProject', () => {
    it('roept POST /projects/ aan met de opgegeven gegevens', async () => {
      const serverProject = makeProject(10, 'Nieuw project')
      api.post.mockResolvedValue({ data: serverProject })
      await store.createProject({ name: 'Nieuw project', color: '#4F86C6', notes: '' })
      expect(api.post).toHaveBeenCalledWith('/projects/', {
        name: 'Nieuw project',
        color: '#4F86C6',
        notes: '',
      })
    })

    it('voegt het nieuwe project toe aan store.projects', async () => {
      const serverProject = makeProject(10, 'Nieuw project')
      api.post.mockResolvedValue({ data: serverProject })
      await store.createProject({ name: 'Nieuw project', color: '#4F86C6', notes: '' })
      expect(store.projects.some(p => p.id === 10)).toBe(true)
    })

    it('geeft het nieuwe project terug', async () => {
      const serverProject = makeProject(10, 'Nieuw project')
      api.post.mockResolvedValue({ data: serverProject })
      const result = await store.createProject({ name: 'Nieuw project', color: '#4F86C6', notes: '' })
      expect(result.id).toBe(10)
    })

    it('slaat foutmelding op bij mislukte POST', async () => {
      api.post.mockRejectedValue({ response: { data: { name: ['Naam al in gebruik'] } } })
      await store.createProject({ name: 'Dubbel', color: '#000', notes: '' })
      expect(store.error).toBeTruthy()
    })

    it('geeft null terug bij een fout', async () => {
      api.post.mockRejectedValue(new Error('Network error'))
      const result = await store.createProject({ name: 'Fout', color: '#000', notes: '' })
      expect(result).toBeNull()
    })
  })

  // ── updateProject ──────────────────────────────────────────────────────────
  describe('updateProject', () => {
    it('roept PATCH /projects/{id}/ aan met de gewijzigde gegevens', async () => {
      store.projects = [makeProject(5, 'Oud')]
      api.patch.mockResolvedValue({ data: makeProject(5, 'Nieuw') })
      await store.updateProject(5, { name: 'Nieuw' })
      expect(api.patch).toHaveBeenCalledWith('/projects/5/', { name: 'Nieuw' })
    })

    it('past het project bij in store.projects', async () => {
      store.projects = [makeProject(5, 'Oud')]
      api.patch.mockResolvedValue({ data: { ...makeProject(5, 'Nieuw'), color: '#ff0000' } })
      await store.updateProject(5, { name: 'Nieuw', color: '#ff0000' })
      const updated = store.projects.find(p => p.id === 5)
      expect(updated.name).toBe('Nieuw')
      expect(updated.color).toBe('#ff0000')
    })

    it('kan is_active op false zetten (archiveren)', async () => {
      store.projects = [makeProject(5, 'Project')]
      api.patch.mockResolvedValue({ data: { ...makeProject(5, 'Project'), is_active: false } })
      await store.updateProject(5, { is_active: false })
      expect(api.patch).toHaveBeenCalledWith('/projects/5/', { is_active: false })
      expect(store.projects.find(p => p.id === 5).is_active).toBe(false)
    })

    it('kan is_active op true zetten (heractiveren)', async () => {
      store.projects = [makeProject(5, 'Gearchiveerd', false)]
      api.patch.mockResolvedValue({ data: makeProject(5, 'Gearchiveerd', true) })
      await store.updateProject(5, { is_active: true })
      expect(store.projects.find(p => p.id === 5).is_active).toBe(true)
    })

    it('slaat foutmelding op bij mislukte PATCH', async () => {
      store.projects = [makeProject(5, 'Project')]
      api.patch.mockRejectedValue(new Error('Network error'))
      await store.updateProject(5, { name: 'Fout' })
      expect(store.error).toBeTruthy()
    })
  })

  // ── deleteProject ──────────────────────────────────────────────────────────
  describe('deleteProject', () => {
    it('roept DELETE /projects/{id}/ aan', async () => {
      store.projects = [makeProject(7, 'Te verwijderen')]
      api.delete.mockResolvedValue({})
      await store.deleteProject(7)
      expect(api.delete).toHaveBeenCalledWith('/projects/7/')
    })

    it('verwijdert het project uit store.projects', async () => {
      store.projects = [makeProject(7, 'Te verwijderen'), makeProject(8, 'Blijft')]
      api.delete.mockResolvedValue({})
      await store.deleteProject(7)
      expect(store.projects.find(p => p.id === 7)).toBeUndefined()
      expect(store.projects.find(p => p.id === 8)).toBeDefined()
    })

    it('slaat foutmelding op bij mislukte DELETE (bijv. project heeft nog blokken)', async () => {
      store.projects = [makeProject(7, 'Gekoppeld project')]
      api.delete.mockRejectedValue({ response: { status: 409, data: { detail: 'Nog in gebruik' } } })
      await store.deleteProject(7)
      expect(store.error).toBeTruthy()
    })

    it('laat het project in de store staan bij een fout', async () => {
      store.projects = [makeProject(7, 'Gekoppeld project')]
      api.delete.mockRejectedValue(new Error('Network error'))
      await store.deleteProject(7)
      expect(store.projects.find(p => p.id === 7)).toBeDefined()
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
