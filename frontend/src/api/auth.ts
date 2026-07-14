import client from './client'
import type { User } from '@/types'

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export const authApi = {
  login: (username: string, password: string) =>
    client.post<LoginResponse>('/auth/login', { username, password }),
  me: () => client.get<User>('/auth/me'),
}
