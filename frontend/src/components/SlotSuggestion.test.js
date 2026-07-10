import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import SlotSuggestion from './SlotSuggestion.vue'
import { useActivityBlocksStore } from '@/stores/activityBlocks'

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

describe('SlotSuggestion — zoekbalk', () => {
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

  it('toont zoekbalk wanneer popup open is', () => {
    const wrapper = mount(SlotSuggestion, { props: defaultProps })
    expect(wrapper.find('input[type="text"]').exists()).toBe(true)
  })

  it('toont alle projecten bij lege zoekterm', async () => {
    const wrapper = mount(SlotSuggestion, { props: defaultProps })
    const input = wrapper.find('input[type="text"]')
    await input.setValue('')
    const projectNames = wrapper.findAll('.project-item').map(el => el.text())
    expect(projectNames.some(n => n.includes('Frontend'))).toBe(true)
    expect(projectNames.some(n => n.includes('Backend'))).toBe(true)
    expect(projectNames.some(n => n.includes('Design'))).toBe(true)
  })

  it('filtert projecten op zoekterm (case-insensitief)', async () => {
    const wrapper = mount(SlotSuggestion, { props: defaultProps })
    const input = wrapper.find('input[type="text"]')
    await input.setValue('back')
    const projectNames = wrapper.findAll('.project-item').map(el => el.text())
    expect(projectNames.some(n => n.includes('Backend'))).toBe(true)
    expect(projectNames.some(n => n.includes('Frontend'))).toBe(false)
    expect(projectNames.some(n => n.includes('Design'))).toBe(false)
  })

  it('toont melding bij geen resultaten', async () => {
    const wrapper = mount(SlotSuggestion, { props: defaultProps })
    const input = wrapper.find('input[type="text"]')
    await input.setValue('xyzxyz')
    expect(wrapper.text()).toContain('Geen projecten gevonden')
  })

  it('reset zoekterm bij sluiten', async () => {
    const wrapper = mount(SlotSuggestion, { props: defaultProps })
    const input = wrapper.find('input[type="text"]')
    await input.setValue('back')
    await wrapper.find('button[data-action="annuleren"]').trigger('click')
    expect(input.element.value).toBe('')
  })
})

describe('SlotSuggestion — commentaar', () => {
  let store
  const tempId = Date.now() * 1000 + 1

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useActivityBlocksStore()
    store.blocks = [
      { id: tempId, started_at: '2024-01-15T09:00:00Z', total_seconds: 900, dominant_title: 'X', project: null, comment: 'Bestaande notitie' },
    ]
  })

  it('toont geen commentaarveld zonder blockIds', () => {
    const wrapper = mount(SlotSuggestion, { props: defaultProps })
    expect(wrapper.find('textarea').exists()).toBe(false)
  })

  it('toont commentaarveld gevuld met initialComment wanneer blockIds is meegegeven', () => {
    const wrapper = mount(SlotSuggestion, {
      props: { ...defaultProps, blockIds: [tempId], initialComment: 'Bestaande notitie' },
    })
    const textarea = wrapper.find('textarea')
    expect(textarea.exists()).toBe(true)
    expect(textarea.element.value).toBe('Bestaande notitie')
  })

  it('slaat gewijzigde tekst op via store.saveComment bij blur', async () => {
    const wrapper = mount(SlotSuggestion, {
      props: { ...defaultProps, blockIds: [tempId], initialComment: 'Bestaande notitie' },
    })
    const textarea = wrapper.find('textarea')
    await textarea.setValue('Nieuwe notitie')
    await textarea.trigger('blur')

    expect(store.blocks[0].comment).toBe('Nieuwe notitie')
  })

  it('roept geen update aan bij blur als de tekst ongewijzigd is', async () => {
    const wrapper = mount(SlotSuggestion, {
      props: { ...defaultProps, blockIds: [tempId], initialComment: 'Bestaande notitie' },
    })
    const textarea = wrapper.find('textarea')
    await textarea.trigger('blur')

    expect(store.blocks[0].comment).toBe('Bestaande notitie')
  })

  it('slaat de tekst direct op bij Enter, zonder dat een project gekozen hoeft te worden', async () => {
    const wrapper = mount(SlotSuggestion, {
      props: { ...defaultProps, blockIds: [tempId], initialComment: 'Bestaande notitie' },
    })
    const textarea = wrapper.find('textarea')
    await textarea.setValue('Direct opgeslagen')
    await textarea.trigger('keydown', { key: 'Enter' })

    expect(store.blocks[0].comment).toBe('Direct opgeslagen')
  })

  it('sluit de popup bij Enter', async () => {
    const wrapper = mount(SlotSuggestion, {
      props: { ...defaultProps, blockIds: [tempId], initialComment: 'Bestaande notitie' },
    })
    const textarea = wrapper.find('textarea')
    await textarea.setValue('Direct opgeslagen')
    await textarea.trigger('keydown', { key: 'Enter' })

    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('sluit de popup niet bij Shift+Enter', async () => {
    const wrapper = mount(SlotSuggestion, {
      props: { ...defaultProps, blockIds: [tempId], initialComment: 'Bestaande notitie' },
    })
    const textarea = wrapper.find('textarea')
    await textarea.setValue('Nog niet klaar')
    const event = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true, bubbles: true, cancelable: true })
    textarea.element.dispatchEvent(event)

    expect(wrapper.emitted('close')).toBeFalsy()
  })

  it('voorkomt de standaard nieuwe-regel bij Enter (zonder Shift)', async () => {
    const wrapper = mount(SlotSuggestion, {
      props: { ...defaultProps, blockIds: [tempId], initialComment: 'Bestaande notitie' },
    })
    const textareaEl = wrapper.find('textarea').element
    const event = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true })
    textareaEl.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
  })

  it('voegt een nieuwe regel toe bij Shift+Enter in plaats van op te slaan', async () => {
    const wrapper = mount(SlotSuggestion, {
      props: { ...defaultProps, blockIds: [tempId], initialComment: 'Bestaande notitie' },
    })
    const textarea = wrapper.find('textarea')
    await textarea.setValue('Nog niet opgeslagen')
    const event = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true, bubbles: true, cancelable: true })
    textarea.element.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(false)
    expect(store.blocks[0].comment).toBe('Bestaande notitie')
  })
})
