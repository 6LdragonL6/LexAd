// ── API 通用响应 ──────────────────────────────────────────────────────────

/** 通用 API 响应包装 */
export interface ApiResponse<T> {
  data: T
  message?: string
}

// ── 审查模型 ──────────────────────────────────────────────────────────────

/** 命中的合规规则信息 */
export interface MatchedRule {
  rule_id: string
  rule_text: string
  source: string
  match_type: string
}

/** 单层审查结果（法律 / 行业 / 平台其中之一） */
export interface SingleLayerReview {
  level: string
  status: string
  risk_score: number
  matched_rules: MatchedRule[]
  explanations: string[]
  suggestions: string[]
}

/** 三层审查汇总结果 */
export interface ThreeLayerReview {
  legal_review: SingleLayerReview
  industry_review: SingleLayerReview
  platform_review: SingleLayerReview
}

/** 上传图片的元信息 */
export interface ImageMeta {
  filename: string
  size_bytes: number
  content_type: string
  status: string
}

/** 预处理结果：OCR 文本、图片摘要和警告信息 */
export interface PreprocessResult {
  ocr_text: string
  image_summary: string
  preprocess_status: string
  warnings: string[]
}

/** 标准化输入：原始文本 + 图片元信息 */
export interface StandardInput {
  raw_text: string
  image_meta: ImageMeta
}

/** 匹配到的历史案例参考 */
export interface CaseReference {
  case_id: string
  title: string
  similarity: number
  relevance: string
  summary: string
}

/** 广告文案合规改写模板 */
export interface RewriteTemplate {
  template_id: string
  title: string
  before: string
  after: string
  note: string
}

/** 罚金评估结果 */
export interface PenaltyAssessment {
  penalty_level: string
  penalty_amount: string
  assessment_notes: string
}

/** 审查最终结论 */
export interface FinalResult {
  overall_status: string
  summary: string
  recommendations: string[]
  notes: string
}

/** 审查完整结果 —— 包含审查全流程的所有环节 */
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

// ── 案例库和模板库 ─────────────────────────────────────────────────────────

/** 案例库条目 */
export interface CaseItem {
  case_id: string
  title: string
  summary: string
  [key: string]: any
}

/** 模板库条目 */
export interface TemplateItem {
  template_id: string
  title: string
  before: string
  after: string
  note: string
  [key: string]: any
}
