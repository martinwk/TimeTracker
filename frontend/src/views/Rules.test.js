// Tests voor de Rules view — rendering en gebruikersinteracties.
// De API wordt gemockt; de echte stores worden gebruikt.
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
import RulesView from './Rules.vue'
import { useActivityRulesStore } from '@/stores/activityRules'
import { useProjectsStore } from '@/stores/projects'
import { useActivityBlocksStore } from '@/stores/activityBlocks'

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

const makeProject = (id, name) => ({
  id,
  name,
  color: '#4F86C6',
  is_active: true,
  notes: '',
  created_at: '2024-01-01T00:00:00Z',
})

// Gebruik de al actieve Pinia zodat store en component dezelfde instantie delen.
const mountView = () =>
  mount(RulesView, {
    global: { plugins: [getActivePinia()] },
  })

describe('Rules view', () => {
  let rulesStore
  let projectsStore

  beforeEach(() => {
    setActivePinia(createPinia())
    rulesStore = useActivityRulesStore()
    projectsStore = useProjectsStore()
    vi.clearAllMocks()

    // Standaard lege responses
    api.get.mockResolvedValue({ data: { results: [] } })
    api.post.mockResolvedValue({ data: {} })
  })

  // ── Initialisatie ──────────────────────────────────────────────────────────
  describe('initialisatie', () => {
    it('laadt regels op bij mounten', async () => {
      mountView()
      await flushPromises()
      expect(api.get).toHaveBeenCalledWith('/activities/activity-rules/')
    })

    it('laadt projecten op bij mounten als de lijst leeg is', async () => {
      mountView()
      await flushPromises()
      expect(api.get).toHaveBeenCalledWith('/projects/')
    })

    it('laadt geen projecten op als de lijst al gevuld is', async () => {
      projectsStore.projects = [makeProject(5, 'Mijn project')]
      mountView()
      await flushPromises()
      const projectCalls = api.get.mock.calls.filter(c => c[0] === '/projects/')
      expect(projectCalls).toHaveLength(0)
    })
  })

  // ── Rendering ──────────────────────────────────────────────────────────────
  describe('rendering', () => {
    it('toont een rij voor elke regel', async () => {
      api.get.mockImplementation(url => {
        if (url === '/activities/activity-rules/') {
          return Promise.resolve({ data: { results: [makeRule(1), makeRule(2, 'title_contains', 'GitHub', 5, 20)] } })
        }
        return Promise.resolve({ data: { results: [] } })
      })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.findAll('[data-testid="rule-row"]')).toHaveLength(2)
    })

    it('toont de match_field_display van elke regel', async () => {
      api.get.mockImplementation(url => {
        if (url === '/activities/activity-rules/') {
          return Promise.resolve({ data: { results: [makeRule(1)] } })
        }
        return Promise.resolve({ data: { results: [] } })
      })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.text()).toContain('Applicatienaam (exact)')
    })

    it('toont de match_value van elke regel', async () => {
      api.get.mockImplementation(url => {
        if (url === '/activities/activity-rules/') {
          return Promise.resolve({ data: { results: [makeRule(1, 'app_name', 'VS Code')] } })
        }
        return Promise.resolve({ data: { results: [] } })
      })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.text()).toContain('VS Code')
    })

    it('toont de projectnaam van de gekoppelde regel', async () => {
      api.get.mockImplementation(url => {
        if (url === '/activities/activity-rules/') {
          return Promise.resolve({ data: { results: [makeRule(1, 'app_name', 'VS Code', 5)] } })
        }
        if (url === '/projects/') {
          return Promise.resolve({ data: { results: [makeProject(5, 'Mijn project')] } })
        }
        return Promise.resolve({ data: { results: [] } })
      })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.text()).toContain('Mijn project')
    })

    it('toont de prioriteit van elke regel', async () => {
      api.get.mockImplementation(url => {
        if (url === '/activities/activity-rules/') {
          return Promise.resolve({ data: { results: [makeRule(1, 'app_name', 'VS Code', 5, 10)] } })
        }
        return Promise.resolve({ data: { results: [] } })
      })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.text()).toContain('10')
    })

    it('toont een lege-melding als er geen regels zijn', async () => {
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="empty-message"]').exists()).toBe(true)
    })

    it('toont de knop Nieuwe regel', async () => {
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="btn-nieuwe-regel"]').exists()).toBe(true)
    })

    it('toont de knop Regels toepassen', async () => {
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="btn-regels-toepassen"]').exists()).toBe(true)
    })
  })

  // ── Formulier: aanmaken ────────────────────────────────────────────────────
  describe('formulier — nieuwe regel', () => {
    it('formulier is standaard verborgen', async () => {
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="rule-form"]').exists()).toBe(false)
    })

    it('knop Nieuwe regel opent het formulier', async () => {
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-nieuwe-regel"]').trigger('click')
      expect(wrapper.find('[data-testid="rule-form"]').exists()).toBe(true)
    })

    it('formulier bevat alle vereiste velden', async () => {
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-nieuwe-regel"]').trigger('click')
      expect(wrapper.find('[data-testid="form-priority"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="form-match-field"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="form-match-value"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="form-project"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="form-is-active"]').exists()).toBe(true)
    })

    it('annuleren verbergt het formulier', async () => {
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-nieuwe-regel"]').trigger('click')
      await wrapper.find('[data-testid="btn-annuleren"]').trigger('click')
      expect(wrapper.find('[data-testid="rule-form"]').exists()).toBe(false)
    })

    it('opslaan roept store.createRule aan met de ingevoerde gegevens', async () => {
      projectsStore.projects = [makeProject(5, 'Mijn project')]
      api.post.mockResolvedValue({ data: makeRule(99) })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-nieuwe-regel"]').trigger('click')
      await wrapper.find('[data-testid="form-priority"]').setValue('15')
      await wrapper.find('[data-testid="form-match-value"]').setValue('Notepad')
      await wrapper.find('[data-testid="btn-opslaan"]').trigger('click')
      await flushPromises()
      expect(api.post).toHaveBeenCalledWith('/activities/activity-rules/', expect.objectContaining({
        priority: 15,
        match_value: 'Notepad',
      }))
    })

    it('formulier sluit na succesvol opslaan', async () => {
      api.post.mockResolvedValue({ data: makeRule(99) })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-nieuwe-regel"]').trigger('click')
      await wrapper.find('[data-testid="btn-opslaan"]').trigger('click')
      await flushPromises()
      expect(wrapper.find('[data-testid="rule-form"]').exists()).toBe(false)
    })
  })

  // ── Formulier: bewerken ────────────────────────────────────────────────────
  describe('formulier — bewerken', () => {
    it('bewerkknop opent het formulier met bestaande waarden', async () => {
      api.get.mockImplementation(url => {
        if (url === '/activities/activity-rules/') {
          return Promise.resolve({ data: { results: [makeRule(1, 'app_name', 'VS Code', 5, 10)] } })
        }
        if (url === '/projects/') {
          return Promise.resolve({ data: { results: [makeProject(5, 'Mijn project')] } })
        }
        return Promise.resolve({ data: { results: [] } })
      })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-bewerken"]').trigger('click')
      expect(wrapper.find('[data-testid="form-match-value"]').element.value).toBe('VS Code')
      expect(wrapper.find('[data-testid="form-priority"]').element.value).toBe('10')
    })

    it('opslaan na bewerken roept store.updateRule aan', async () => {
      api.get.mockImplementation(url => {
        if (url === '/activities/activity-rules/') {
          return Promise.resolve({ data: { results: [makeRule(1, 'app_name', 'VS Code', 5, 10)] } })
        }
        return Promise.resolve({ data: { results: [] } })
      })
      api.patch.mockResolvedValue({ data: makeRule(1, 'app_name', 'Notepad', 5, 10) })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-bewerken"]').trigger('click')
      await wrapper.find('[data-testid="form-match-value"]').setValue('Notepad')
      await wrapper.find('[data-testid="btn-opslaan"]').trigger('click')
      await flushPromises()
      expect(api.patch).toHaveBeenCalledWith('/activities/activity-rules/1/', expect.objectContaining({
        match_value: 'Notepad',
      }))
    })

    it('formulier sluit na succesvol bewerken', async () => {
      api.get.mockImplementation(url => {
        if (url === '/activities/activity-rules/') {
          return Promise.resolve({ data: { results: [makeRule(1)] } })
        }
        return Promise.resolve({ data: { results: [] } })
      })
      api.patch.mockResolvedValue({ data: makeRule(1) })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-bewerken"]').trigger('click')
      await wrapper.find('[data-testid="btn-opslaan"]').trigger('click')
      await flushPromises()
      expect(wrapper.find('[data-testid="rule-form"]').exists()).toBe(false)
    })
  })

  // ── Verwijderen ────────────────────────────────────────────────────────────
  describe('verwijderen', () => {
    it('verwijderknop roept store.deleteRule aan na bevestiging', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true)
      api.get.mockImplementation(url => {
        if (url === '/activities/activity-rules/') {
          return Promise.resolve({ data: { results: [makeRule(1)] } })
        }
        return Promise.resolve({ data: { results: [] } })
      })
      api.delete.mockResolvedValue({})
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-verwijderen"]').trigger('click')
      await flushPromises()
      expect(api.delete).toHaveBeenCalledWith('/activities/activity-rules/1/')
    })

    it('verwijderknop doet niets als gebruiker annuleert', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(false)
      api.get.mockImplementation(url => {
        if (url === '/activities/activity-rules/') {
          return Promise.resolve({ data: { results: [makeRule(1)] } })
        }
        return Promise.resolve({ data: { results: [] } })
      })
      api.delete.mockResolvedValue({})
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-verwijderen"]').trigger('click')
      await flushPromises()
      expect(api.delete).not.toHaveBeenCalled()
    })
  })

  // ── Regels toepassen ───────────────────────────────────────────────────────
  describe('regels toepassen', () => {
    it('knop Regels toepassen roept applyRules aan voor het huidige weekbereik', async () => {
      const blocksStore = useActivityBlocksStore()
      blocksStore.currentDate = '2026-06-17'
      api.post.mockResolvedValue({ data: { applied: 3 } })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-regels-toepassen"]').trigger('click')
      await flushPromises()
      expect(api.post).toHaveBeenCalledWith('/activities/apply-rules/', {
        date_from: '2026-06-17',
        date_to: '2026-06-23',
      })
    })

    it('toont een succesmelding na succesvol toepassen', async () => {
      const blocksStore = useActivityBlocksStore()
      blocksStore.currentDate = '2026-06-17'
      api.post.mockResolvedValue({ data: { applied: 3 } })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-regels-toepassen"]').trigger('click')
      await flushPromises()
      expect(wrapper.find('[data-testid="apply-success"]').exists()).toBe(true)
    })

    it('toont een foutmelding als toepassen mislukt', async () => {
      const blocksStore = useActivityBlocksStore()
      blocksStore.currentDate = '2026-06-17'
      api.post.mockRejectedValue(new Error('Network error'))
      const wrapper = mountView()
      await flushPromises()
      await wrapper.find('[data-testid="btn-regels-toepassen"]').trigger('click')
      await flushPromises()
      expect(wrapper.find('[data-testid="apply-error"]').exists()).toBe(true)
    })
  })
})
