import rawTips from '../../../data/compliance_tips.json'

export interface ComplianceTip {
  id: string
  title: string
  body: string
  source: string
  source_path: string
  roles: Array<'marketing' | 'legal' | 'admin'>
  tags: string[]
  enabled: boolean
}

const fallbackTip: ComplianceTip = {
  id: 'fallback-review-before-submit',
  title: '提交前复核关键表达',
  body: '请复核绝对化用语、功效承诺、价格宣传和平台限制；没有充分依据的内容应先修改或补充证明材料。',
  source: 'LexAd 内置提示',
  source_path: '',
  roles: ['marketing', 'legal', 'admin'],
  tags: ['合规复核'],
  enabled: true,
}

const storageKey = 'lexad:last-compliance-tip'

function validTip(value: unknown): value is ComplianceTip {
  const tip = value as Partial<ComplianceTip>
  return Boolean(
    tip
    && typeof tip.id === 'string'
    && typeof tip.title === 'string'
    && typeof tip.body === 'string'
    && Array.isArray(tip.roles)
    && typeof tip.enabled === 'boolean',
  )
}

export function selectComplianceTip(role: 'marketing' | 'legal' | 'admin'): ComplianceTip {
  const candidates = (rawTips.tips as unknown[])
    .filter(validTip)
    .filter(tip => tip.enabled && tip.roles.includes(role))

  if (!candidates.length) return fallbackTip

  const previous = window.localStorage.getItem(storageKey)
  const nonRepeating = candidates.filter(tip => tip.id !== previous)
  const pool = nonRepeating.length ? nonRepeating : candidates
  const selected = pool[Math.floor(Math.random() * pool.length)] || fallbackTip
  window.localStorage.setItem(storageKey, selected.id)
  return selected
}
