import { describe, expect, it } from 'vitest'
import { confirmedRiskIssues, highestRiskLabel, requiresRiskApproval, scoreRiskLabel, scoreVariant } from '@/utils/review'
import type { EngineResult, MatchedRule } from '@/types'

function resultWith(issues: MatchedRule[]): EngineResult {
  const emptyLayer = { layer: '', matched_rules: [], explanations: [] }
  return {
    compliance_score: 75,
    layer1: emptyLayer,
    layer2: { ...emptyLayer, matched_rules: issues },
    layer3: emptyLayer,
    layer4: emptyLayer,
    summary: '',
    suggestions: [],
    case_refs: [],
  }
}

describe('review domain helpers', () => {
  it('only returns confirmed AI risk findings', () => {
    const issues = confirmedRiskIssues(resultWith([
      { rule_id: 'confirmed', rule_text: '确认风险', source_law: '', match_type: 'high', adjudication_status: 'confirmed' },
      { rule_id: 'candidate', rule_text: '候选', source_law: '', match_type: 'medium', adjudication_status: 'rejected' as never },
    ]))
    expect(issues.map(issue => issue.rule_id)).toEqual(['confirmed'])
  })

  it('finds the highest confirmed risk level', () => {
    expect(highestRiskLabel([
      { rule_id: '1', rule_text: '', source_law: '', match_type: 'low', risk_level: 'low' },
      { rule_id: '2', rule_text: '', source_law: '', match_type: 'high', risk_level: 'high' },
    ])).toBe('高风险')
  })

  it('uses one higher-is-better score direction', () => {
    expect(scoreVariant(85)).toBe('success')
    expect(scoreVariant(70)).toBe('warning')
    expect(scoreVariant(40)).toBe('danger')
    expect(scoreRiskLabel(null)).toBe('待人工复核')
  })

  it('requires confirmation only for approved decisions with confirmed risks', () => {
    const result = resultWith([
      { rule_id: '1', rule_text: '确认风险', source_law: '', match_type: 'high' },
    ])
    expect(requiresRiskApproval('approved', result)).toBe(true)
    expect(requiresRiskApproval('conditional', result)).toBe(false)
    expect(requiresRiskApproval('returned', result)).toBe(false)
    expect(requiresRiskApproval('approved', resultWith([]))).toBe(false)
  })
})
