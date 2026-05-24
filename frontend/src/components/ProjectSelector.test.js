import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import ProjectSelector from './ProjectSelector.vue'

describe('ProjectSelector — toetsenbord', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('emit close bij Escape', async () => {
    const wrapper = mount(ProjectSelector)
    await document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emit geen close bij andere toetsen', async () => {
    const wrapper = mount(ProjectSelector)
    await document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
    expect(wrapper.emitted('close')).toBeFalsy()
  })

  it('verwijdert de listener na unmount', async () => {
    const wrapper = mount(ProjectSelector)
    wrapper.unmount()
    await document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(wrapper.emitted('close')).toBeFalsy()
  })
})

describe('ProjectSelector — koppeling verwijderen hotkey', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('emit assign met null bij d', async () => {
    const wrapper = mount(ProjectSelector)
    await document.dispatchEvent(new KeyboardEvent('keydown', { key: 'd' }))
    expect(wrapper.emitted('assign')?.[0][0]).toBeNull()
  })

  it('emit assign met null bij Delete', async () => {
    const wrapper = mount(ProjectSelector)
    await document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Delete' }))
    expect(wrapper.emitted('assign')?.[0][0]).toBeNull()
  })
})
