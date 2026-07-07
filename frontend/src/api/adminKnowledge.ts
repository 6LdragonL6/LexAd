import client from './client'

export type PublicOpinionStatus = 'draft' | 'ai_processing' | 'pending_review' | 'published' | 'archived'

export interface PublicOpinionEvent {
  id: string
  external_id: string | null
  title: string
  source_text: string
  consequence_text: string
  source_meta: Record<string, any>
  status: PublicOpinionStatus
  created_by_id: string
  updated_by_id: string | null
  published_by_id: string | null
  archived_by_id: string | null
  restored_by_id: string | null
  created_at: string
  updated_at: string
  published_at: string | null
  archived_at: string | null
}

export interface PublicOpinionEventVersion {
  id: string
  event_id: string
  version: number
  title: string
  industry: string[]
  platforms: string[]
  occurred_at: string | null
  source_text: string
  sources: any[]
  event_process: Record<string, any>
  consequences: Record<string, any>
  risk_topics: string[]
  trigger_patterns: string[]
  affected_groups: string[]
  propagation_drivers: string[]
  normalized_tags: Record<string, any>
  severity_level: string | null
  summary: string
  confidence: number | null
  model_name: string | null
  model_version: string | null
  generated_at: string | null
  edited_by_id: string | null
  edit_notes: string
  created_at: string
}

export interface PublicOpinionEventDetail {
  event: PublicOpinionEvent
  versions: PublicOpinionEventVersion[]
}

export interface PublicOpinionEventList {
  items: PublicOpinionEvent[]
  total: number
}

export interface PlatformRuleSet {
  id: string
  platform_name: string
  display_name: string
  description: string
  created_at: string
  updated_at: string
}

export interface PlatformRuleVersion {
  id: string
  rule_set_id: string
  version_label: string
  source_name: string
  source_url: string
  published_at: string | null
  effective_at: string | null
  expires_at: string | null
  raw_text: string
  structured_rules: any[]
  diff_summary: Record<string, any>
  status: string
  imported_by_id: string
  reviewed_by_id: string | null
  activated_by_id: string | null
  created_at: string
  updated_at: string
  activated_at: string | null
}

export interface PlatformRuleSetDetail {
  rule_set: PlatformRuleSet
  active_version: PlatformRuleVersion | null
  versions: PlatformRuleVersion[]
}

export interface PlatformRuleSetList {
  items: PlatformRuleSetDetail[]
  total: number
}

export interface KnowledgeImportJob {
  id: string
  import_type: string
  file_name: string
  status: string
  total_items: number
  valid_items: number
  invalid_items: number
  error_summary: Record<string, any>
  options: Record<string, any>
  created_by_id: string
  created_at: string
  updated_at: string
  completed_at: string | null
}

export interface KnowledgeAuditLog {
  id: string
  actor_id: string
  action: string
  target_type: string
  target_id: string
  before_state: Record<string, any>
  after_state: Record<string, any>
  message: string
  created_at: string
}

export interface ImportConfirmResult {
  job: KnowledgeImportJob
  created_event_ids: string[]
  updated_event_ids: string[]
  skipped_external_ids: string[]
}

export const adminKnowledgeApi = {
  listPublicOpinionEvents: (params?: { status?: string; keyword?: string }) =>
    client.get<PublicOpinionEventList>('/admin/knowledge/public-opinion/events', { params }),
  createPublicOpinionEvent: (data: {
    external_id?: string | null
    title?: string
    source_text: string
    consequence_text: string
    source_meta?: Record<string, any>
  }) => client.post<PublicOpinionEvent>('/admin/knowledge/public-opinion/events', data),
  getPublicOpinionEvent: (id: string) =>
    client.get<PublicOpinionEventDetail>(`/admin/knowledge/public-opinion/events/${id}`),
  updatePublicOpinionEvent: (id: string, data: Partial<PublicOpinionEvent>) =>
    client.put<PublicOpinionEvent>(`/admin/knowledge/public-opinion/events/${id}`, data),
  structurePublicOpinionEvent: (id: string) =>
    client.post<PublicOpinionEventVersion>(`/admin/knowledge/public-opinion/events/${id}/structure`),
  publishPublicOpinionEvent: (id: string) =>
    client.post<PublicOpinionEvent>(`/admin/knowledge/public-opinion/events/${id}/publish`),
  archivePublicOpinionEvent: (id: string) =>
    client.post<PublicOpinionEvent>(`/admin/knowledge/public-opinion/events/${id}/archive`),
  restorePublicOpinionEvent: (id: string) =>
    client.post<PublicOpinionEvent>(`/admin/knowledge/public-opinion/events/${id}/restore`),
  deletePublicOpinionEvent: (id: string) =>
    client.delete(`/admin/knowledge/public-opinion/events/${id}`),
  getPublicOpinionImportTemplate: () =>
    client.get<Record<string, any>>('/admin/knowledge/public-opinion/import-template'),
  previewPublicOpinionImport: (payload: Record<string, any>, file_name = 'cases.json') =>
    client.post<KnowledgeImportJob>('/admin/knowledge/public-opinion/import/preview', { payload, file_name }),
  confirmPublicOpinionImport: (jobId: string, data: { duplicate_actions?: Record<string, string>; run_structure?: boolean }) =>
    client.post<ImportConfirmResult>(`/admin/knowledge/public-opinion/imports/${jobId}/confirm`, data),

  listPlatformRules: () =>
    client.get<PlatformRuleSetList>('/admin/knowledge/platform-rules'),
  createPlatformRuleSet: (data: { platform_name: string; display_name: string; description?: string }) =>
    client.post<PlatformRuleSet>('/admin/knowledge/platform-rules', data),
  updatePlatformRuleSet: (id: string, data: { display_name?: string; description?: string }) =>
    client.put<PlatformRuleSet>(`/admin/knowledge/platform-rules/${id}`, data),
  getPlatformRuleSet: (id: string) =>
    client.get<PlatformRuleSetDetail>(`/admin/knowledge/platform-rules/${id}`),
  createPlatformRuleVersion: (ruleSetId: string, data: {
    version_label: string
    source_name?: string
    source_url?: string
    raw_text?: string
    structured_rules?: any[]
    effective_at?: string | null
  }) => client.post<PlatformRuleVersion>(`/admin/knowledge/platform-rules/${ruleSetId}/versions`, data),
  activatePlatformRuleVersion: (versionId: string) =>
    client.post<PlatformRuleVersion>(`/admin/knowledge/platform-rule-versions/${versionId}/activate`),
  rollbackPlatformRuleVersion: (versionId: string) =>
    client.post<PlatformRuleVersion>(`/admin/knowledge/platform-rule-versions/${versionId}/rollback`),

  listImportJobs: () =>
    client.get<KnowledgeImportJob[]>('/admin/knowledge/imports'),
  listAuditLogs: (target_type?: string) =>
    client.get<KnowledgeAuditLog[]>('/admin/knowledge/audit-logs', { params: { target_type } }),
}
