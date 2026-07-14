export interface NavItem {
  route: string
  label: string
  icon: string
  roles: string[]
  group?: 'main' | 'knowledge'
  order: number
}

export const navigationConfig: NavItem[] = [
  { route: '/', label: '工作台', icon: 'home', roles: ['marketing', 'legal', 'admin'], group: 'main', order: 1 },
  { route: '/submit', label: '提交物料', icon: 'submit', roles: ['marketing', 'admin'], group: 'main', order: 2 },
  { route: '/legal', label: '法务审核台', icon: 'legal', roles: ['marketing', 'legal', 'admin'], group: 'main', order: 3 },
  { route: '/brands', label: '品牌档案', icon: 'brand', roles: ['marketing', 'legal', 'admin'], group: 'main', order: 4 },
  { route: '/knowledge', label: '法规数据库', icon: 'knowledge', roles: ['marketing', 'legal', 'admin'], group: 'knowledge', order: 5 },
  { route: '/admin/knowledge', label: '资料中心', icon: 'admin', roles: ['admin'], group: 'knowledge', order: 6 },
  { route: '/admin/settings', label: '系统管理', icon: 'admin', roles: ['admin'], group: 'knowledge', order: 7 },
]

export function getNavItems(role: string): NavItem[] {
  return navigationConfig
    .filter(item => item.roles.includes(role))
    .sort((a, b) => a.order - b.order)
}
