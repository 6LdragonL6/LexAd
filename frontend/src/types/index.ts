export interface User {
  id: string
  username: string
  display_name: string
  role: 'marketing' | 'legal' | 'admin'
  dept_name: string
  is_active: boolean
  created_at: string
}

export interface Material {
  id: string
  name: string
  industry: string
  platforms: string[]
  material_type: string
  raw_text: string
  image_path: string | null
  priority: 'normal' | 'urgent' | 'extreme'
  deadline: string | null
  status: string
  current_version: number
  submitter_id: string
  created_at: string
  updated_at: string
}

export interface MatchedRule {
  rule_id: string
  rule_text: string
  source_law: string
  match_type: string
}

export interface LayerResult {
  layer: string
  matched_rules: MatchedRule[]
  explanations: string[]
}

export interface EngineResult {
  risk_score: number
  layer1: LayerResult
  layer2: LayerResult
  layer3: LayerResult
  layer4: LayerResult
  summary: string
  suggestions: string[]
  case_refs: Record<string, any>[]
}

export interface Review {
  id: string
  material_id: string
  version: number
  ai_risk_score: number
  ai_result: EngineResult
  legal_decision: 'approved' | 'returned' | 'conditional' | null
  legal_notes: string | null
  return_reasons: string | null
  reviewer_id: string | null
  reviewed_at: string | null
  created_at: string
}

export interface ReviewQueueItem {
  id: string
  material_id: string
  material_name: string
  submitter_name: string
  industry: string
  ai_risk_score: number
  priority: string
  status: string
  created_at: string
  waiting_hours?: number
}

export interface LawItem {
  id: string
  title: string
  path: string
}

export interface PreviewTextResponse {
  text: string
  quality: 'good' | 'degraded' | 'minimal'
  source_format: string
}
