import client from './client'

export const knowledgeApi = {
  laws: (search = '') => client.get('/knowledge/laws', { params: { search } }),
  industryRules: (industry = '') => client.get('/knowledge/industry-rules', { params: { industry } }),
  cases: (search = '', province = '') => client.get('/knowledge/cases', { params: { search, province } }),
  platforms: (platform = '') => client.get('/knowledge/platforms', { params: { platform } }),
  templates: () => client.get('/knowledge/templates'),
}
