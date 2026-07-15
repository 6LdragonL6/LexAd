import { describe, expect, it } from 'vitest'
import { resolveReturnSource } from '@/composables/useReturnNavigation'

describe('return navigation source', () => {
  it('accepts only allowlisted sources', () => {
    expect(resolveReturnSource('workbench', 'legal')).toBe('workbench')
    expect(resolveReturnSource('legal-dashboard', 'marketing')).toBe('legal-dashboard')
  })

  it('falls back by role for direct and invalid links', () => {
    expect(resolveReturnSource('https://example.com', 'marketing')).toBe('workbench')
    expect(resolveReturnSource(undefined, 'legal')).toBe('legal-dashboard')
    expect(resolveReturnSource(undefined, 'admin')).toBe('legal-dashboard')
  })
})
