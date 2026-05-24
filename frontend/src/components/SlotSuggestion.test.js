import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import SlotSuggestion from './SlotSuggestion.vue'

const defaultProps = {
  slotInfo: { iso: '2024-01-15', hour: 9, minute: 0 },
  position: { top: '100px', left: '100px' },
}

describe('SlotSuggestion — toetsenbord', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('emit close bij Escape', async () => {
    const wrapper = mount(SlotSuggestion, { props: defaultProps })
    await document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emit geen close bij andere toetsen', async () => {
    const wrapper = mount(SlotSuggestion, { props: defaultProps })
    await document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
    expect(wrapper.emitted('close')).toBeFalsy()
  })

  it('verwijdert de listener na unmount', async () => {
    const wrapper = mount(SlotSuggestion, { props: defaultProps })
    wrapper.unmount()
    await document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(wrapper.emitted('close')).toBeFalsy()
  })
})

describe('SlotSuggestion — koppeling verwijderen hotkey', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('emit create met projectId: null bij d als canUnassign true is', async () => {
    const wrapper = mount(SlotSuggestion, { props: { ...defaultProps, canUnassign: true } })
    await document.dispatchEvent(new KeyboardEvent('keydown', { key: 'd' }))
    expect(wrapper.emitted('create')?.[0][0]).toEqual({ projectId: null, slotInfo: defaultProps.slotInfo })
  })

  it('emit create met projectId: null bij Delete als canUnassign true is', async () => {
    const wrapper = mount(SlotSuggestion, { props: { ...defaultProps, canUnassign: true } })
    await document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Delete' }))
    expect(wrapper.emitted('create')?.[0][0]).toEqual({ projectId: null, slotInfo: defaultProps.slotInfo })
  })

  it('doet niets bij d als canUnassign false is', async () => {
    const wrapper = mount(SlotSuggestion, { props: { ...defaultProps, canUnassign: false } })
    await document.dispatchEvent(new KeyboardEvent('keydown', { key: 'd' }))
    expect(wrapper.emitted('create')).toBeFalsy()
  })
})
