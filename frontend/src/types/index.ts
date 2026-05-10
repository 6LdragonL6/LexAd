// ── API Response ──────────────────────────────────────────────────────────

export interface ApiResponse<T> {
  data: T
  message?: string
}

// ── Review Models ────────────────────────────────────────────────────────

export interface MatchedRule {
  rule_id: string
  rule_text: string
  source: string
  match_type: string
}

export interface SingleLayerReview {
  level: string
  status: string
  risk_score: number
  matched_rules: MatchedRule[]
  explanations: string[]
  suggestions: string[]
}

export interface ThreeLayerReview {
  legal_review: SingleLayerReview
  industry_review: SingleLayerReview
  platform_review: SingleLayerReview
}

export interface ImageMeta {
  filename: string
  size_bytes: number
  content_type: string
  status: string
}

export interface PreprocessResult {
  ocr_text: string
  image_summary: string
  preprocess_status: string
  warnings: string[]
}

export interface StandardInput {
  raw_text: string
  image_meta: ImageMeta
}

export interface CaseReference {
  case_id: string
  title: string
  similarity: number
  relevance: string
  summary: string
}

export interface RewriteTemplate {
  template_id: string
  title: string
  before: string
  after: string
  note: string
}

export interface PenaltyAssessment {
  penalty_level: string
  penalty_amount: string
  assessment_notes: string
}

export interface FinalResult {
  overall_status: string
  summary: string
  recommendations: string[]
  notes: string
}

export interface ReviewResult {
  request_id: string
  created_at: string
  input: StandardInput
  preprocess: PreprocessResult
  review: ThreeLayerReview
  case_references: CaseReference[]
  rewrite_templates: RewriteTemplate[]
  penalty_assessment: PenaltyAssessment
  final_result: FinalResult
}

// ── Case Library ─────────────────────────────────────────────────────────

export interface CaseItem {
  case_id: string
  title: string
  summary: string
  [key: string]: any
}

export interface TemplateItem {
  template_id: string
  title: string
  before: string
  after: string
  note: string
  [key: string]: any
}
