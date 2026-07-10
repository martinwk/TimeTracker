import { describe, it, expect } from 'vitest'
import client from './api.js'

describe('api client', () => {
  it('gebruikt Django als baseURL', () => {
    expect(client.defaults.baseURL).toBe('http://localhost:8000/api')
  })

  it('heeft een default timeout zodat een offline backend snel faalt', () => {
    expect(client.defaults.timeout).toBe(10000)
  })
})
