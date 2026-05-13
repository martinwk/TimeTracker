import { mount } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import ActivityBlock from './ActivityBlock.vue'
import { makeLocalISO } from '@/utils/date'

const HOUR_HEIGHT = 60

// Creates a single-block props object with the given local time and duration.
const makeBlock = (startHour, startMin, durationMin, project = null) => ({
  id: 1,
  started_at: makeLocalISO('2024-01-15', startHour, startMin),
  total_seconds: durationMin * 60,
  dominant_title: 'Test blok',
  project,
})

const mountBlock = (block, extra = {}) =>
  mount(ActivityBlock, {
    props: { blocks: [block], hourHeight: HOUR_HEIGHT, ...extra },
  })

// Mocks getBoundingClientRect on the root element so edge-detection works.
const mockRect = (wrapper, height = 100) => {
  wrapper.element.getBoundingClientRect = vi.fn(() => ({
    top: 0, left: 0, right: 80, bottom: height,
    width: 80, height, x: 0, y: 0, toJSON: vi.fn(),
  }))
}

// ── Style ───────────────────────────────────────────────────────────────────────
describe('ActivityBlock — stijl', () => {
  it('berekent de juiste top-positie op basis van uur', () => {
    // 9:00 → 9 * HOUR_HEIGHT = 540px
    const wrapper = mountBlock(makeBlock(9, 0, 60))
    expect(wrapper.attributes('style')).toContain('top: 540px')
  })

  it('berekent de juiste top-positie met minuten', () => {
    // 9:30 → (9.5) * 60 = 570px
    const wrapper = mountBlock(makeBlock(9, 30, 30))
    expect(wrapper.attributes('style')).toContain('top: 570px')
  })

  it('berekent de juiste hoogte op basis van duur', () => {
    // 60 min → (60/60) * 60 = 60px
    const wrapper = mountBlock(makeBlock(9, 0, 60))
    expect(wrapper.attributes('style')).toContain('height: 60px')
  })

  it('minimum hoogte is 12px voor korte blokken', () => {
    // 1 min → (1/60)*60 = 1px → clamped to 12px
    const wrapper = mountBlock(makeBlock(9, 0, 1))
    expect(wrapper.attributes('style')).toContain('height: 12px')
  })

  it('grijze achtergrond als er geen project is', () => {
    const wrapper = mountBlock(makeBlock(9, 0, 60, null))
    // jsdom normaliseert hex naar rgb(); #f1f5f9 = rgb(241, 245, 249)
    expect(wrapper.attributes('style')).toContain('rgb(241, 245, 249)')
  })

  it('projectkleur (met alpha) als er een project is', () => {
    const project = { id: 1, name: 'Test', color: '#6366f1' }
    const wrapper = mountBlock(makeBlock(9, 0, 60, project))
    // jsdom normaliseert hex+alpha naar rgba(); #6366f1 = rgb(99, 102, 241)
    expect(wrapper.attributes('style')).toContain('rgba(99, 102, 241,')
  })
})

// ── Interactie ───────────────────────────────────────────────────────────────────
describe('ActivityBlock — interactie', () => {
  it('emit move-start bij mousedown in het midden van het blok', async () => {
    const wrapper = mountBlock(makeBlock(9, 0, 90))
    mockRect(wrapper, 100)
    // clientY=50 → y=50, niet dicht bij rand (EDGE_PX=7)
    await wrapper.trigger('mousedown', { button: 0, clientY: 50 })
    expect(wrapper.emitted('move-start')).toBeTruthy()
    expect(wrapper.emitted('resize-start')).toBeFalsy()
  })

  it('emit resize-start met edge=bottom bij mousedown dicht bij onderrand', async () => {
    const wrapper = mountBlock(makeBlock(9, 0, 90))
    mockRect(wrapper, 100)
    // clientY=96 → y=96 ≥ 100-7=93 → bottom-rand
    await wrapper.trigger('mousedown', { button: 0, clientY: 96 })
    expect(wrapper.emitted('resize-start')).toBeTruthy()
    const payload = wrapper.emitted('resize-start')[0][0]
    expect(payload.edge).toBe('bottom')
    expect(payload.blocks[0].id).toBe(1)
  })

  it('emit resize-start met edge=top bij mousedown dicht bij bovenrand', async () => {
    const wrapper = mountBlock(makeBlock(9, 0, 90))
    mockRect(wrapper, 100)
    // clientY=3 → y=3 ≤ 7 → top-rand
    await wrapper.trigger('mousedown', { button: 0, clientY: 3 })
    expect(wrapper.emitted('resize-start')).toBeTruthy()
    const payload = wrapper.emitted('resize-start')[0][0]
    expect(payload.edge).toBe('top')
  })

  it('emit niets bij rechtermuisklik (button=2)', async () => {
    const wrapper = mountBlock(makeBlock(9, 0, 90))
    mockRect(wrapper, 100)
    await wrapper.trigger('mousedown', { button: 2, clientY: 50 })
    expect(wrapper.emitted('move-start')).toBeFalsy()
    expect(wrapper.emitted('resize-start')).toBeFalsy()
  })

  it('move-start payload bevat de doorgegeven blocks', async () => {
    const block = makeBlock(9, 0, 90)
    const wrapper = mountBlock(block)
    mockRect(wrapper, 100)
    await wrapper.trigger('mousedown', { button: 0, clientY: 50 })
    const payload = wrapper.emitted('move-start')[0][0]
    expect(payload.blocks).toHaveLength(1)
    expect(payload.blocks[0].id).toBe(1)
  })
})

// ── Weergave ─────────────────────────────────────────────────────────────────────
describe('ActivityBlock — weergave', () => {
  it('toont duur als minuten voor blokken onder een uur', () => {
    // 45 min → '45m'
    const wrapper = mountBlock(makeBlock(9, 0, 45))
    expect(wrapper.text()).toContain('45m')
  })

  it('toont duur als uren+minuten voor blokken van een uur of langer', () => {
    // 90 min → '1u30m'
    const wrapper = mountBlock(makeBlock(9, 0, 90))
    expect(wrapper.text()).toContain('1u30m')
  })

  it('toont alleen uren als er geen resterende minuten zijn', () => {
    // 120 min → '2u'
    const wrapper = mountBlock(makeBlock(9, 0, 120))
    expect(wrapper.text()).toContain('2u')
    expect(wrapper.text()).not.toContain('2u0m')
  })

  it('toont geen titeltekst voor te kleine blokken (isLargeEnough=false)', () => {
    // 15 min met hourHeight=60 → (15/60)*60=15px < 22 → isLargeEnough=false
    const wrapper = mountBlock(makeBlock(9, 0, 15))
    // De titel-span is conditioneel op isLargeEnough
    const titleSpans = wrapper.findAll('span.text-\\[10px\\]')
    expect(titleSpans).toHaveLength(0)
  })

  it('toont titeltekst voor grote genoeg blokken', () => {
    // 60 min met hourHeight=60 → 60px ≥ 22 → isLargeEnough=true
    const wrapper = mountBlock(makeBlock(9, 0, 60))
    expect(wrapper.text()).toContain('Test blok')
  })

  it('toont aantal× indicator voor gemerged blok', () => {
    const block1 = makeBlock(9,  0, 60, { id: 1, name: 'P', color: '#000' })
    const block2 = { ...makeBlock(10, 0, 60, { id: 1, name: 'P', color: '#000' }), id: 2 }
    const wrapper = mount(ActivityBlock, {
      props: { blocks: [block1, block2], hourHeight: HOUR_HEIGHT },
    })
    expect(wrapper.text()).toContain('2×')
  })
})
