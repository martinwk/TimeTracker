import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import ProjectSelector from './ProjectSelector.vue'
import { useActivityBlocksStore } from '@/stores/activityBlocks'

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

describe('ProjectSelector — zoekbalk', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useActivityBlocksStore()
    store.projects = [
      { id: 1, name: 'Frontend', color: '#ff0000' },
      { id: 2, name: 'Backend', color: '#00ff00' },
      { id: 3, name: 'Design', color: '#0000ff' },
    ]
  })

  it('toont zoekbalk wanneer modal open is', () => {
    const wrapper = mount(ProjectSelector)
    expect(wrapper.find('input[type="text"]').exists()).toBe(true)
  })

  it('toont alle projecten bij lege zoekterm', async () => {
    const wrapper = mount(ProjectSelector)
    const input = wrapper.find('input[type="text"]')
    await input.setValue('')
    const projectNames = wrapper.findAll('.project-item').map(el => el.text())
    expect(projectNames.some(n => n.includes('Frontend'))).toBe(true)
    expect(projectNames.some(n => n.includes('Backend'))).toBe(true)
    expect(projectNames.some(n => n.includes('Design'))).toBe(true)
  })

  it('filtert projecten op zoekterm (case-insensitief)', async () => {
    const wrapper = mount(ProjectSelector)
    const input = wrapper.find('input[type="text"]')
    await input.setValue('back')
    const projectNames = wrapper.findAll('.project-item').map(el => el.text())
    expect(projectNames.some(n => n.includes('Backend'))).toBe(true)
    expect(projectNames.some(n => n.includes('Frontend'))).toBe(false)
    expect(projectNames.some(n => n.includes('Design'))).toBe(false)
  })

  it('toont melding bij geen resultaten', async () => {
    const wrapper = mount(ProjectSelector)
    const input = wrapper.find('input[type="text"]')
    await input.setValue('xyzxyz')
    expect(wrapper.text()).toContain('Geen projecten gevonden')
  })

  it('reset zoekterm bij sluiten via sluitknop', async () => {
    const wrapper = mount(ProjectSelector)
    const input = wrapper.find('input[type="text"]')
    await input.setValue('back')
    await wrapper.find('button[data-action="sluiten"]').trigger('click')
    expect(input.element.value).toBe('')
  })
})
