import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Sidebar from './Sidebar.vue'
import api from '@/api/api'

vi.mock('@/api/api', () => ({
  default: { post: vi.fn() },
}))

const mockFetchWeekBlocks = vi.fn()
vi.mock('@/stores/activityBlocks', () => ({
  useActivityBlocksStore: () => ({ fetchWeekBlocks: mockFetchWeekBlocks }),
}))

const mountSidebar = () => mount(Sidebar, { props: { isOpen: true } })

describe('Sidebar — sync-knop', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('toont een sync-knop', () => {
    const wrapper = mountSidebar()
    expect(wrapper.find('[data-testid="sync-button"]').exists()).toBe(true)
  })

  it('roept sync-endpoint aan bij klikken', async () => {
    api.post.mockResolvedValue({ data: { imported: 2, days_aggregated: ['2026-11-01'], blocks_created: 4 } })
    const wrapper = mountSidebar()

    await wrapper.find('[data-testid="sync-button"]').trigger('click')

    expect(api.post).toHaveBeenCalledWith('/activities/sync/', {})
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
