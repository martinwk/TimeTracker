import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import Sidebar from './Sidebar.vue'
import api from '@/api/api'

vi.mock('@/api/api', () => ({
  default: { post: vi.fn() },
}))

const mockFetchWeekBlocks = vi.fn()
vi.mock('@/stores/activityBlocks', () => ({
  useActivityBlocksStore: () => ({
    fetchWeekBlocks: mockFetchWeekBlocks,
    currentDate: '2026-06-16',
  }),
}))

const mountSidebar = () => mount(Sidebar, { props: { isOpen: true } })

describe('Sidebar — sync-knop', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('toont een sync-knop', () => {
    const wrapper = mountSidebar()
    expect(wrapper.find('[data-testid="sync-button"]').exists()).toBe(true)
  })

  it('roept sync-endpoint aan bij klikken zonder log pad', async () => {
    api.post.mockResolvedValue({ data: { imported: 2, days_aggregated: ['2026-11-01'], blocks_created: 4 } })
    const wrapper = mountSidebar()

    await wrapper.find('[data-testid="sync-button"]').trigger('click')

    expect(api.post).toHaveBeenCalledWith('/activities/sync/', {}, { timeout: 60000 })
  })

  it('stuurt log_path mee als dat in localStorage staat', async () => {
    localStorage.setItem('ahk_log_path', '/custom/log.txt')
    api.post.mockResolvedValue({ data: { imported: 2, days_aggregated: ['2026-11-01'], blocks_created: 4 } })
    const wrapper = mountSidebar()

    await wrapper.find('[data-testid="sync-button"]').trigger('click')

    expect(api.post).toHaveBeenCalledWith('/activities/sync/', { log_path: '/custom/log.txt' }, { timeout: 60000 })
  })

  it('ververst de blokken na succesvolle sync', async () => {
    api.post.mockResolvedValue({ data: { imported: 2, days_aggregated: ['2026-11-01'], blocks_created: 4 } })
    const wrapper = mountSidebar()

    await wrapper.find('[data-testid="sync-button"]').trigger('click')
    await flushPromises()

    expect(mockFetchWeekBlocks).toHaveBeenCalledOnce()
  })

  it('ververst de blokken niet bij een fout', async () => {
    api.post.mockRejectedValue({ response: { status: 404 } })
    const wrapper = mountSidebar()

    await wrapper.find('[data-testid="sync-button"]').trigger('click')
    await flushPromises()

    expect(mockFetchWeekBlocks).not.toHaveBeenCalled()
  })

  it('toont resultaat na succesvolle sync', async () => {
    api.post.mockResolvedValue({ data: { imported: 5, days_aggregated: ['2026-11-01', '2026-11-02'], blocks_created: 8 } })
    const wrapper = mountSidebar()

    await wrapper.find('[data-testid="sync-button"]').trigger('click')
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('8')   // blocks_created
    expect(text).toContain('2')   // days_aggregated.length
  })

  it('toont foutmelding als logbestand niet gevonden (404)', async () => {
    api.post.mockRejectedValue({ response: { status: 404 } })
    const wrapper = mountSidebar()

    await wrapper.find('[data-testid="sync-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('niet gevonden')
  })

  it('toont generieke foutmelding bij andere fouten', async () => {
    api.post.mockRejectedValue({ response: { status: 500 } })
    const wrapper = mountSidebar()

    await wrapper.find('[data-testid="sync-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Fout')
  })
})

describe('Sidebar — instellingen-knop', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('toont een instellingen-knop (tandwiel)', () => {
    const wrapper = mountSidebar()
    expect(wrapper.find('[data-testid="settings-button"]').exists()).toBe(true)
  })

  it('opent het instellingenpaneel bij klikken op tandwiel', async () => {
    const wrapper = mountSidebar()

    // Panel should not be visible initially
    expect(wrapper.find('[data-testid="settings-panel"]').exists()).toBe(false)

    await wrapper.find('[data-testid="settings-button"]').trigger('click')

    expect(wrapper.find('[data-testid="settings-panel"]').exists()).toBe(true)
  })

  it('sluit het instellingenpaneel bij opnieuw klikken op tandwiel', async () => {
    const wrapper = mountSidebar()

    await wrapper.find('[data-testid="settings-button"]').trigger('click')
    expect(wrapper.find('[data-testid="settings-panel"]').exists()).toBe(true)

    await wrapper.find('[data-testid="settings-button"]').trigger('click')
    expect(wrapper.find('[data-testid="settings-panel"]').exists()).toBe(false)
  })

  it('sluit het instellingenpaneel via de sluitknop in het paneel', async () => {
    const wrapper = mountSidebar()

    await wrapper.find('[data-testid="settings-button"]').trigger('click')
    expect(wrapper.find('[data-testid="settings-panel"]').exists()).toBe(true)

    await wrapper.find('[data-testid="close-button"]').trigger('click')
    expect(wrapper.find('[data-testid="settings-panel"]').exists()).toBe(false)
  })
})
