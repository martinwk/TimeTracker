// Tests voor de Weekstaat view — rendering van de uren-per-project-tabel.
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
import WeekstaatView from './Weekstaat.vue'
import { useActivityBlocksStore } from '@/stores/activityBlocks'

// Maandag 2024-01-15, week 3
const MONDAY = '2024-01-15'

const proj1 = { id: 1, name: 'TimeTracker', color: '#6366f1' }
const proj2 = { id: 2, name: 'Backend',     color: '#f59e0b' }

// Blok met UTC-timestamp zodat de store het correct parsert
const makeBlock = (id, iso, startHour, durationMin, project = null) => ({
  id,
  started_at: `${iso}T${String(startHour).padStart(2, '0')}:00:00Z`,
  total_seconds: durationMin * 60,
  dominant_title: `Blok ${id}`,
  project,
})

// api.get mocken met een lijst blokken (fetchWeekBlocks verwacht { results: [...] })
const mockBlocks = (blocks) =>
  api.get.mockResolvedValue({ data: { results: blocks } })

const mountView = () =>
  mount(WeekstaatView, {
    global: { plugins: [getActivePinia()] },
  })

describe('Weekstaat view', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useActivityBlocksStore()
    store.currentDate = MONDAY
    vi.clearAllMocks()
    api.get.mockResolvedValue({ data: { results: [] } })
  })

  // ── Initialisatie ──────────────────────────────────────────────────────────
  describe('initialisatie', () => {
    it('haalt blokken op bij mounten', async () => {
      mountView()
      await flushPromises()
      expect(api.get).toHaveBeenCalled()
    })
  })

  // ── Kolomhoofden ──────────────────────────────────────────────────────────
  describe('kolomhoofden', () => {
    it('toont 7 dagkolommen voor de huidige week', async () => {
      mockBlocks([makeBlock(1, MONDAY, 9, 60, proj1)])
      store.projects = [proj1]
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.findAll('[data-testid="dag-header"]')).toHaveLength(7)
    })

    it('eerste kolom is maandag', async () => {
      mockBlocks([makeBlock(1, MONDAY, 9, 60, proj1)])
      store.projects = [proj1]
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="dag-header"]').text()).toContain('ma')
    })

    it('laatste kolom is zondag', async () => {
      mockBlocks([makeBlock(1, MONDAY, 9, 60, proj1)])
      store.projects = [proj1]
      const wrapper = mountView()
      await flushPromises()
      const headers = wrapper.findAll('[data-testid="dag-header"]')
      expect(headers[6].text()).toContain('zo')
    })

    it('toont het dagnummer in de kolomkop', async () => {
      mockBlocks([makeBlock(1, MONDAY, 9, 60, proj1)])
      store.projects = [proj1]
      const wrapper = mountView()
      await flushPromises()
      // Maandag 15 januari
      expect(wrapper.find('[data-testid="dag-header"]').text()).toContain('15')
    })
  })

  // ── Projectrijen ──────────────────────────────────────────────────────────
  describe('projectrijen', () => {
    it('toont een rij per project dat die week voorkomt', async () => {
      mockBlocks([
        makeBlock(1, '2024-01-15', 9, 60, proj1),
        makeBlock(2, '2024-01-16', 9, 90, proj2),
      ])
      store.projects = [proj1, proj2]
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.findAll('[data-testid="project-rij"]')).toHaveLength(2)
    })

    it('toont de projectnaam in de rij', async () => {
      mockBlocks([makeBlock(1, MONDAY, 9, 60, proj1)])
      store.projects = [proj1]
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.text()).toContain('TimeTracker')
    })

    it('toont geen rij voor projecten zonder blokken die week', async () => {
      mockBlocks([makeBlock(1, MONDAY, 9, 60, proj1)])
      store.projects = [proj1, proj2]
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.findAll('[data-testid="project-rij"]')).toHaveLength(1)
      expect(wrapper.text()).not.toContain('Backend')
    })
  })

  // ── Celwaarden ────────────────────────────────────────────────────────────
  describe('celwaarden', () => {
    it('toont uren als decimaal (3600s = 1u)', async () => {
      mockBlocks([makeBlock(1, MONDAY, 9, 60, proj1)])
      store.projects = [proj1]
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.text()).toContain('1u')
    })

    it('toont halve uren met komma (5400s = 1,5u)', async () => {
      mockBlocks([makeBlock(1, MONDAY, 9, 90, proj1)])
      store.projects = [proj1]
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.text()).toContain('1,5u')
    })

    it('toont een streepje voor lege cellen', async () => {
      mockBlocks([makeBlock(1, MONDAY, 9, 60, proj1)])
      store.projects = [proj1]
      const wrapper = mountView()
      await flushPromises()
      // 6 van de 7 dagcellen zijn leeg voor proj1
      expect(wrapper.findAll('[data-testid="cel-leeg"]').length).toBeGreaterThanOrEqual(6)
    })

    it('telt meerdere blokken op dezelfde dag op', async () => {
      mockBlocks([
        makeBlock(1, MONDAY, 9,  60, proj1), // 1u
        makeBlock(2, MONDAY, 11, 30, proj1), // 0,5u → samen 1,5u
      ])
      store.projects = [proj1]
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.text()).toContain('1,5u')
    })
  })

  // ── Totalen ───────────────────────────────────────────────────────────────
  describe('totalen', () => {
    it('toont het totaal per project (rijtotaal)', async () => {
      mockBlocks([
        makeBlock(1, '2024-01-15', 9, 60, proj1), // ma: 1u
        makeBlock(2, '2024-01-16', 9, 60, proj1), // di: 1u → totaal 2u
      ])
      store.projects = [proj1]
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="rij-totaal"]').text()).toContain('2u')
    })

    it('toont het totaal per dag (kolomtotaal)', async () => {
      mockBlocks([
        makeBlock(1, '2024-01-15', 9,  60, proj1), // ma: 1u proj1
        makeBlock(2, '2024-01-15', 11, 60, proj2), // ma: 1u proj2 → ma totaal 2u
      ])
      store.projects = [proj1, proj2]
      const wrapper = mountView()
      await flushPromises()
      const kolomtotalen = wrapper.findAll('[data-testid="kolom-totaal"]')
      expect(kolomtotalen[0].text()).toContain('2u')
    })

    it('toont het totaal van de hele week (eindtotaal)', async () => {
      mockBlocks([
        makeBlock(1, '2024-01-15', 9, 120, proj1), // 2u
        makeBlock(2, '2024-01-16', 9,  60, proj2), // 1u → totaal 3u
      ])
      store.projects = [proj1, proj2]
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="eindtotaal"]').text()).toContain('3u')
    })
  })

  // ── Niet-toegewezen ───────────────────────────────────────────────────────
  describe('niet-toegewezen', () => {
    it('toont een rij voor niet-toegewezen blokken', async () => {
      mockBlocks([makeBlock(1, MONDAY, 9, 60, null)])
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="rij-niet-toegewezen"]').exists()).toBe(true)
    })

    it('toont niet-toegewezen uren in de juiste dagcel', async () => {
      mockBlocks([makeBlock(1, MONDAY, 9, 60, null)]) // ma: 1u
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="rij-niet-toegewezen"]').text()).toContain('1u')
    })

    it('toont geen niet-toegewezen rij als alle blokken zijn toegewezen', async () => {
      mockBlocks([makeBlock(1, MONDAY, 9, 60, proj1)])
      store.projects = [proj1]
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="rij-niet-toegewezen"]').exists()).toBe(false)
    })
  })

  // ── Weeknavigatie ─────────────────────────────────────────────────────────
  describe('weeknavigatie', () => {
    it('toont een vorige-week knop', async () => {
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="btn-vorige-week"]').exists()).toBe(true)
    })

    it('toont een volgende-week knop', async () => {
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="btn-volgende-week"]').exists()).toBe(true)
    })

    it('knop vorige week roept store.goToPrevWeek aan', async () => {
      const wrapper = mountView()
      await flushPromises()
      const goToPrevWeek = vi.spyOn(store, 'goToPrevWeek').mockResolvedValue()
      await wrapper.find('[data-testid="btn-vorige-week"]').trigger('click')
      expect(goToPrevWeek).toHaveBeenCalled()
    })

    it('knop volgende week roept store.goToNextWeek aan', async () => {
      const wrapper = mountView()
      await flushPromises()
      const goToNextWeek = vi.spyOn(store, 'goToNextWeek').mockResolvedValue()
      await wrapper.find('[data-testid="btn-volgende-week"]').trigger('click')
      expect(goToNextWeek).toHaveBeenCalled()
    })

    it('toont het weeknummer en datumbereik', async () => {
      const wrapper = mountView()
      await flushPromises()
      // Week 3 van 2024 (15–21 jan)
      expect(wrapper.text()).toContain('Week 3')
    })
  })

  // ── Lege week ─────────────────────────────────────────────────────────────
  describe('lege week', () => {
    it('toont een melding als er geen blokken zijn', async () => {
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="leeg-melding"]').exists()).toBe(true)
    })
  })
})
