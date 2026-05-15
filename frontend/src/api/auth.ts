import client from './client'
import type { User } from '@/types'

export const authApi = {
  login: (username: string, password: string) =>
    client.post<{ access_token: string; token_type: string }>('/auth/login', { username, password }),
  me: () => client.get<User>('/auth/me'),
}
