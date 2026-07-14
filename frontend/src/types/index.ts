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
  brand_id?: string | null
  created_at: string
  updated_at: string
}

export interface PlatformOption {
  value: string
  label: string
}

export interface MatchedRule {
  rule_id: string
  rule_text: string
  source_law: string
  match_type: string
  explanation?: string
  matched_text?: string
  match_method?: string
  score?: number | null
  source_id?: string
  suggestion?: string
  evidence_quote?: string
  reasoning?: string
  risk_level?: 'high' | 'medium' | 'low'
  risk_level_label?: string
  confidence?: number
  adjudication_status?: 'confirmed'
  basis_refs?: BasisReference[]
}

export interface BasisReference {
  id: string
  title: string
  version?: string
}

export interface VerificationItem {
  item_id: string
  evidence_quote: string
  verification_type: string
  reason: string
  required_materials: string[]
  basis_refs?: BasisReference[]
}

export interface LayerResult {
  layer: string
  matched_rules: MatchedRule[]
  explanations: string[]
  status?: 'matched' | 'no_match' | 'unavailable' | 'failed'
  source_versions?: string[]
  candidate_count?: number
  verification_items?: VerificationItem[]
  requires_manual_review?: boolean
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
  platform_rule_version_ids?: string[]
  unavailable_platforms?: string[]
  platform_version_labels?: Record<string, string>
  hit_count?: number
  risk_topics?: string[]
  verification_items?: VerificationItem[]
  requires_manual_review?: boolean
  review_status?: 'completed' | 'confirmed_risk' | 'needs_verification' | 'manual_review' | 'no_clear_risk'
}

export interface Review {
  id: string
  material_id: string
  version: number
  ai_risk_score: number
  ai_result: EngineResult
  task_status: 'processing' | 'completed' | 'failed'
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  legal_library_version_id?: string | null
  industry_library_version_id?: string | null
  platform_rule_version_ids?: string[]
  public_opinion_library_version_id?: string | null
  legal_module_status?: 'pending' | 'running' | 'succeeded' | 'failed' | 'unavailable'
  legal_module_error?: string | null
  legal_module_retry_count?: number
  legal_module_completed_at?: string | null
  public_opinion_module_status?: 'pending' | 'running' | 'succeeded' | 'failed' | 'unavailable'
  public_opinion_result?: Record<string, any>
  public_opinion_module_error?: string | null
  public_opinion_module_retry_count?: number
  public_opinion_module_completed_at?: string | null
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
  legal_decision?: 'approved' | 'returned' | 'conditional' | null
  return_reasons?: string | null
  legal_notes?: string | null
  version?: number
  material_version?: number
}

export interface MaterialVersion {
  review_id: string
  version: number
  risk_score: number
  task_status: string
  legal_decision: 'approved' | 'returned' | 'conditional' | null
  return_reasons: string | null
  legal_notes: string | null
  reviewed_at: string | null
  created_at: string
  version_label: string
  legal_review_label: string
  snapshot_complete: boolean
  submission: {
    name: string
    raw_text: string
    industry: string
    platforms: string[]
    material_type: string
    priority: string
    deadline: string | null
  } | null
}

export interface LawItem {
  id: string
  title: string
  path: string
}

export interface KnowledgeItem {
  id: string
  title: string
  group: string
}

export interface KnowledgeCatalog {
  layer: 'L1' | 'L2' | 'L3' | 'L4' | 'L5'
  label: string
  items: KnowledgeItem[]
  total: number
}

export interface KnowledgeContent {
  id: string
  title: string
  layer: string
  content: string
}

export interface PreviewTextResponse {
  text: string
  quality: 'good' | 'degraded' | 'minimal'
  source_format: string
}

export interface Brand {
  id: string
  name: string
  aliases: string[]
  industry: string
  description: string
  status: 'active' | 'archived'
  created_at: string
}

export interface BrandProfile {
  brand: Brand
  total_materials: number
  total_reviews: number
  decided_reviews: number
  approved_count: number
  pass_rate: number | null
  avg_versions: number | null
  top_violations: { rule_id: string; rule_text: string; count: number }[]
  recent_reviews: { id: string; version: number; ai_risk_score: number; legal_decision: string | null; created_at: string }[]
  approved_materials: { id: string; name: string; raw_text_preview: string }[]
}

export interface AiConfigStatus {
  configured: boolean
  provider: string
  base_url: string
  model: string
  masked_key: string
  source: 'database' | 'environment' | 'none'
  validation_status: string
  last_error: string
  updated_at: string | null
  validated_at: string | null
  updated_by_id: string | null
}

export type RecycleTargetType = 'material' | 'brand' | 'public_opinion_event' | 'platform_rule_set'

export interface RecycleBinEntry {
  id: string
  target_type: RecycleTargetType
  target_id: string
  display_name: string
  deleted_by_id: string
  deleted_at: string
  purge_after: string
  remaining_days: number
}

export interface RecycleBinList {
  items: RecycleBinEntry[]
  total: number
  page: number
  page_size: number
}
