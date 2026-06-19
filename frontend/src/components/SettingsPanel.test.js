import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import SettingsPanel from './SettingsPanel.vue'
import api from '@/api/api'

vi.mock('@/api/api', () => ({
  default: {
    post: vi.fn(),
    postForm: vi.fn(),
  },
}))

const mockFetchWeekBlocks = vi.fn()
vi.mock('@/stores/activityBlocks', () => ({
  useActivityBlocksStore: () => ({
    fetchWeekBlocks: mockFetchWeekBlocks,
    currentDate: '2026-06-16',
  }),
}))

const mountPanel = (props = {}) =>
  mount(SettingsPanel, { props: { isOpen: true, ...props } })

describe('SettingsPanel — log pad', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('laadt logPath uit localStorage bij mount', () => {
    localStorage.setItem('ahk_log_path', '/custom/path/log.txt')
    const wrapper = mountPanel()
    const input = wrapper.find('[data-testid="log-path-input"]')
    expect(input.element.value).toBe('/custom/path/log.txt')
  })

  it('toont lege input als localStorage leeg is', () => {
    const wrapper = mountPanel()
    const input = wrapper.find('[data-testid="log-path-input"]')
    expect(input.element.value).toBe('')
  })

  it('slaat logPath op in localStorage bij verandering', async () => {
    const wrapper = mountPanel()
    const input = wrapper.find('[data-testid="log-path-input"]')
    await input.setValue('/new/path/log.txt')
    expect(localStorage.getItem('ahk_log_path')).toBe('/new/path/log.txt')
  })

  it('toont hint over automatisch detecteren', () => {
    const wrapper = mountPanel()
    expect(wrapper.text()).toContain('automatisch detecteren')
  })
})

describe('SettingsPanel — bestand importeren', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('toont een bestandsinput die .txt accepteert', () => {
    const wrapper = mountPanel()
    const fileInput = wrapper.find('[data-testid="file-input"]')
    expect(fileInput.exists()).toBe(true)
    expect(fileInput.attributes('accept')).toBe('.txt')
  })

  it('toont importeerresultaat na succesvol importeren', async () => {
    api.post.mockResolvedValue({ data: { imported: 42 } })
    const wrapper = mountPanel()

    const fileInput = wrapper.find('[data-testid="file-input"]')
    const file = new File(['log content'], 'window_log.txt', { type: 'text/plain' })
    Object.defineProperty(fileInput.element, 'files', { value: [file], configurable: true })
    await fileInput.trigger('change')
    await flushPromises()

    expect(wrapper.text()).toContain('42')
  })

  it('ververst de blokken na succesvol importeren', async () => {
    api.post.mockResolvedValue({ data: { imported: 5 } })
    const wrapper = mountPanel()

    const fileInput = wrapper.find('[data-testid="file-input"]')
    const file = new File(['log content'], 'window_log.txt', { type: 'text/plain' })
    Object.defineProperty(fileInput.element, 'files', { value: [file], configurable: true })
    await fileInput.trigger('change')
    await flushPromises()

    expect(mockFetchWeekBlocks).toHaveBeenCalledOnce()
  })

  it('toont foutmelding bij mislukt importeren', async () => {
    api.post.mockRejectedValue(new Error('network error'))
    const wrapper = mountPanel()

    const fileInput = wrapper.find('[data-testid="file-input"]')
    const file = new File(['log content'], 'window_log.txt', { type: 'text/plain' })
    Object.defineProperty(fileInput.element, 'files', { value: [file], configurable: true })
    await fileInput.trigger('change')
    await flushPromises()

    expect(wrapper.text()).toContain('Fout')
  })

  it('stuurt POST naar /activities/import/ met FormData', async () => {
    api.post.mockResolvedValue({ data: { imported: 1 } })
    const wrapper = mountPanel()

    const fileInput = wrapper.find('[data-testid="file-input"]')
    const file = new File(['log content'], 'window_log.txt', { type: 'text/plain' })
    Object.defineProperty(fileInput.element, 'files', { value: [file], configurable: true })
    await fileInput.trigger('change')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith(
      '/activities/import/',
      expect.any(FormData),
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'multipart/form-data' }) }),
    )
  })
})

describe('SettingsPanel — regels toepassen', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('toont een knop "Regels opnieuw toepassen"', () => {
    const wrapper = mountPanel()
    const button = wrapper.find('[data-testid="apply-rules-button"]')
    expect(button.exists()).toBe(true)
    expect(button.text()).toContain('Regels')
  })

  it('roept apply-rules aan met datum van huidige week', async () => {
    api.post.mockResolvedValue({ data: { blocks_assigned: 7 } })
    const wrapper = mountPanel()

    await wrapper.find('[data-testid="apply-rules-button"]').trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/activities/apply-rules/', {
      date_from: '2026-06-16',
      date_to: '2026-06-22',
    })
  })

  it('toont succesbericht met aantal toegewezen blokken', async () => {
    api.post.mockResolvedValue({ data: { blocks_assigned: 7 } })
    const wrapper = mountPanel()

    await wrapper.find('[data-testid="apply-rules-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('7')
  })

  it('toont foutmelding als apply-rules mislukt', async () => {
    api.post.mockRejectedValue(new Error('server error'))
    const wrapper = mountPanel()

    await wrapper.find('[data-testid="apply-rules-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Fout')
  })
})

describe('SettingsPanel — zichtbaarheid', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('is zichtbaar als isOpen true is', () => {
    const wrapper = mountPanel({ isOpen: true })
    expect(wrapper.find('[data-testid="settings-panel"]').exists()).toBe(true)
  })

  it('is verborgen als isOpen false is', () => {
    const wrapper = mountPanel({ isOpen: false })
    const panel = wrapper.find('[data-testid="settings-panel"]')
    // Panel should not be visible (either not rendered or hidden)
    if (panel.exists()) {
      expect(panel.isVisible()).toBe(false)
    } else {
      expect(panel.exists()).toBe(false)
    }
  })

  it('emit close bij klikken op sluitknop', async () => {
    const wrapper = mountPanel()
    await wrapper.find('[data-testid="close-button"]').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
