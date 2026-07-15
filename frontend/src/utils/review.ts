import type { EngineResult, MatchedRule } from '@/types'

const severityOrder: Record<string, number> = { low: 1, medium: 2, high: 3, severe: 4 }

export function confirmedRiskIssues(result?: EngineResult | null): MatchedRule[] {
  if (!result) return []
  const issues = [
    ...(result.layer1?.matched_rules ?? []),
    ...(result.layer2?.matched_rules ?? []),
    ...(result.layer3?.matched_rules ?? []),
    ...(result.layer4?.matched_rules ?? []),
  ]
  return issues.filter(issue => !issue.adjudication_status || issue.adjudication_status === 'confirmed')
}

export function highestRiskLabel(issues: MatchedRule[]): string {
  const highest = issues.reduce((current, issue) => {
    const level = issue.risk_level || issue.match_type || ''
    return (severityOrder[level] || 0) > (severityOrder[current] || 0) ? level : current
  }, '')
  return ({ severe: '严重风险', high: '高风险', medium: '中风险', low: '低风险' } as Record<string, string>)[highest]
    || '已确认风险'
}

export function requiresRiskApproval(decision: string, result?: EngineResult | null): boolean {
  return decision === 'approved' && confirmedRiskIssues(result).length > 0
}

export function scoreVariant(score: number | null | undefined): 'success' | 'warning' | 'danger' | 'gray' {
  if (score === null || score === undefined) return 'gray'
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

export function scoreRiskLabel(score: number | null | undefined): string {
  if (score === null || score === undefined) return '待人工复核'
  if (score >= 80) return '低风险'
  if (score >= 60) return '中风险'
  return '高风险'
}
