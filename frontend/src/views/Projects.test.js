// Tests voor de Projects view — rendering, filtering en gebruikersinteracties.
// De API wordt gemockt; de echte projects store wordt gebruikt.
import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia, getActivePinia } from 'pinia'

vi.mock('@/api/api', () => ({
  default: {
    get:    vi.fn(),
    post:   vi.fn(),
    patch:  vi.fn(),
    delete: vi.fn(),
  },
}))

import api from '@/api/api'
import ProjectsView from './Projects.vue'
import { useProjectsStore } from '@/stores/projects'

const makeProject = (id, name, isActive = true, color = '#4F86C6') => ({
  id,
  name,
  color,
  is_active: isActive,
  notes: '',
  created_at: '2024-01-01T00:00:00Z',
})

// Gebruik de al actieve Pinia zodat store en component dezelfde instantie delen.
const mountView = () =>
  mount(ProjectsView, {
    global: { plugins: [getActivePinia()] },
  })

describe('Projects view', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useProjectsStore()
    vi.clearAllMocks()
    api.get.mockResolvedValue({ data: { results: [] } })
  })

  // ── Initialisatie ──────────────────────────────────────────────────────────
  describe('initialisatie', () => {
    it('laadt projecten op bij mounten', async () => {
      api.get.mockResolvedValue({ data: { results: [makeProject(1, 'Alpha')] } })
      mountView()
      await flushPromises()
      expect(api.get).toHaveBeenCalledWith('/projects/')
    })
  })

  // ── Rendering ──────────────────────────────────────────────────────────────
  describe('rendering', () => {
    it('toont een kaart voor elk actief project', async () => {
      api.get.mockResolvedValue({ data: { results: [makeProject(1, 'Alpha'), makeProject(2, 'Beta')] } })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.findAll('[data-testid="project-card"]')).toHaveLength(2)
    })

    it('toont de projectnaam op elke kaart', async () => {
      api.get.mockResolvedValue({ data: { results: [makeProject(1, 'Mijn Project')] } })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.text()).toContain('Mijn Project')
    })

    it('toont een kleurindicator met de kleur van het project', async () => {
      api.get.mockResolvedValue({ data: { results: [makeProject(1, 'Kleur project', true, '#ff0000')] } })
      const wrapper = mountView()
      await flushPromises()
      const indicator = wrapper.find('[data-testid="project-color"]')
      expect(indicator.attributes('data-color')).toBe('#ff0000')
    })

    it('toont een melding als er geen projecten zijn (na filter)', async () => {
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="empty-message"]').exists()).toBe(true)
    })

    it('toont een badge op gearchiveerde projecten', async () => {
      api.get.mockResolvedValue({ data: { results: [makeProject(1, 'Oud project', false)] } })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="filter-alle"]').trigger('click')
      expect(wrapper.find('[data-testid="badge-gearchiveerd"]').exists()).toBe(true)
    })

    it('toont de knop Nieuw project', async () => {
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="btn-nieuw-project"]').exists()).toBe(true)
    })
  })

  // ── Filtering ──────────────────────────────────────────────────────────────
  describe('filtering', () => {
    const drieProjecten = [
      makeProject(1, 'Alpha actief', true),
      makeProject(2, 'Beta actief', true),
      makeProject(3, 'Gamma gearchiveerd', false),
    ]

    beforeEach(() => {
      api.get.mockResolvedValue({ data: { results: drieProjecten } })
    })

    it('standaard toont alleen actieve projecten', async () => {
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.findAll('[data-testid="project-card"]')).toHaveLength(2)
    })

    it('statusfilter Alle toont actieve en gearchiveerde projecten', async () => {
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="filter-alle"]').trigger('click')
      expect(wrapper.findAll('[data-testid="project-card"]')).toHaveLength(3)
    })

    it('statusfilter Gearchiveerd toont alleen gearchiveerde projecten', async () => {
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="filter-gearchiveerd"]').trigger('click')
      expect(wrapper.findAll('[data-testid="project-card"]')).toHaveLength(1)
      expect(wrapper.text()).toContain('Gamma gearchiveerd')
    })

    it('statusfilter Actief toont alleen actieve projecten', async () => {
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="filter-alle"]').trigger('click')
      await wrapper.find('[data-testid="filter-actief"]').trigger('click')
      expect(wrapper.findAll('[data-testid="project-card"]')).toHaveLength(2)
    })

    it('zoekbalk filtert live op projectnaam (case-insensitief)', async () => {
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="search-input"]').setValue('alpha')
      expect(wrapper.findAll('[data-testid="project-card"]')).toHaveLength(1)
      expect(wrapper.text()).toContain('Alpha actief')
    })

    it('zoekbalk en statusfilter werken samen', async () => {
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="filter-alle"]').trigger('click')
      await wrapper.find('[data-testid="search-input"]').setValue('gamma')
      expect(wrapper.findAll('[data-testid="project-card"]')).toHaveLength(1)
      expect(wrapper.text()).toContain('Gamma gearchiveerd')
    })

    it('toont lege-melding als zoekbalk geen resultaten geeft', async () => {
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="search-input"]').setValue('bestaat niet')
      expect(wrapper.find('[data-testid="empty-message"]').exists()).toBe(true)
    })
  })

  // ── Formulier: aanmaken ────────────────────────────────────────────────────
  describe('formulier — nieuw project', () => {
    it('formulier is standaard verborgen', async () => {
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="project-form"]').exists()).toBe(false)
    })

    it('knop Nieuw project opent het formulier', async () => {
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-nieuw-project"]').trigger('click')
      expect(wrapper.find('[data-testid="project-form"]').exists()).toBe(true)
    })

    it('formulier bevat een naamveld, kleurveld en notitiesveld', async () => {
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-nieuw-project"]').trigger('click')
      expect(wrapper.find('[data-testid="form-name"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="form-color"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="form-notes"]').exists()).toBe(true)
    })

    it('annuleren verbergt het formulier', async () => {
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-nieuw-project"]').trigger('click')
      await wrapper.find('[data-testid="btn-annuleren"]').trigger('click')
      expect(wrapper.find('[data-testid="project-form"]').exists()).toBe(false)
    })

    it('opslaan roept store.createProject aan met de ingevoerde naam en kleur', async () => {
      api.post.mockResolvedValue({ data: makeProject(99, 'Test project', true, '#ff0000') })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-nieuw-project"]').trigger('click')
      await wrapper.find('[data-testid="form-name"]').setValue('Test project')
      await wrapper.find('[data-testid="form-color"]').setValue('#ff0000')
      await wrapper.find('[data-testid="btn-opslaan"]').trigger('click')
      await flushPromises()
      expect(api.post).toHaveBeenCalledWith('/projects/', expect.objectContaining({
        name: 'Test project',
        color: '#ff0000',
      }))
    })

    it('formulier sluit na succesvol opslaan', async () => {
      api.post.mockResolvedValue({ data: makeProject(99, 'Test project') })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-nieuw-project"]').trigger('click')
      await wrapper.find('[data-testid="form-name"]').setValue('Test project')
      await wrapper.find('[data-testid="btn-opslaan"]').trigger('click')
      await flushPromises()
      expect(wrapper.find('[data-testid="project-form"]').exists()).toBe(false)
    })

    it('naamveld is leeg bij een nieuw formulier', async () => {
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-nieuw-project"]').trigger('click')
      expect(wrapper.find('[data-testid="form-name"]').element.value).toBe('')
    })
  })

  // ── Formulier: bewerken ────────────────────────────────────────────────────
  describe('formulier — bewerken', () => {
    it('bewerkknop opent het formulier met bestaande waarden', async () => {
      api.get.mockResolvedValue({ data: { results: [makeProject(1, 'Bestaand project', true, '#aabbcc')] } })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-bewerken"]').trigger('click')
      expect(wrapper.find('[data-testid="form-name"]').element.value).toBe('Bestaand project')
      expect(wrapper.find('[data-testid="form-color"]').element.value).toBe('#aabbcc')
    })

    it('opslaan na bewerken roept store.updateProject aan', async () => {
      api.get.mockResolvedValue({ data: { results: [makeProject(1, 'Oud')] } })
      api.patch.mockResolvedValue({ data: makeProject(1, 'Nieuw') })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-bewerken"]').trigger('click')
      await wrapper.find('[data-testid="form-name"]').setValue('Nieuw')
      await wrapper.find('[data-testid="btn-opslaan"]').trigger('click')
      await flushPromises()
      expect(api.patch).toHaveBeenCalledWith('/projects/1/', expect.objectContaining({ name: 'Nieuw' }))
    })

    it('formulier sluit na succesvol bewerken', async () => {
      api.get.mockResolvedValue({ data: { results: [makeProject(1, 'Project')] } })
      api.patch.mockResolvedValue({ data: makeProject(1, 'Project') })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-bewerken"]').trigger('click')
      await wrapper.find('[data-testid="btn-opslaan"]').trigger('click')
      await flushPromises()
      expect(wrapper.find('[data-testid="project-form"]').exists()).toBe(false)
    })
  })

  // ── Acties op kaarten ──────────────────────────────────────────────────────
  describe('kaartacties', () => {
    it('archiveerknop roept updateProject aan met is_active: false', async () => {
      api.get.mockResolvedValue({ data: { results: [makeProject(1, 'Actief project', true)] } })
      api.patch.mockResolvedValue({ data: makeProject(1, 'Actief project', false) })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-archiveren"]').trigger('click')
      await flushPromises()
      expect(api.patch).toHaveBeenCalledWith('/projects/1/', { is_active: false })
    })

    it('activeerknop op gearchiveerd project roept updateProject aan met is_active: true', async () => {
      api.get.mockResolvedValue({ data: { results: [makeProject(1, 'Gearchiveerd', false)] } })
      api.patch.mockResolvedValue({ data: makeProject(1, 'Gearchiveerd', true) })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="filter-alle"]').trigger('click')
      await wrapper.find('[data-testid="btn-activeren"]').trigger('click')
      await flushPromises()
      expect(api.patch).toHaveBeenCalledWith('/projects/1/', { is_active: true })
    })

    it('verwijderknop roept store.deleteProject aan', async () => {
      api.get.mockResolvedValue({ data: { results: [makeProject(1, 'Te verwijderen')] } })
      api.delete.mockResolvedValue({})
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-verwijderen"]').trigger('click')
      await flushPromises()
      expect(api.delete).toHaveBeenCalledWith('/projects/1/')
    })
  })
})
