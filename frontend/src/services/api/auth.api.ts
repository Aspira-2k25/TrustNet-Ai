import { httpClient } from './client';
import type { User } from '../../types';

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
  email: string;
  role: string;
}

export const authApi = {
  async login(email: string, password: string): Promise<{ user: User; token: string }> {
    const res = await httpClient.request<{ data: AuthResponse; status: string }>(
      '/api/v1/auth/login',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      },
      false
    );

    const token = res.data.access_token;
    const user: User = {
      id: res.data.user_id,
      email: res.data.email,
      role: (res.data.role as User['role']) || 'researcher',
    };

    httpClient.setToken(token);
    return { user, token };
  },

  async register(
    email: string,
    password: string,
    role: string = 'researcher'
  ): Promise<{ user: User; token: string }> {
    const res = await httpClient.request<{ data: AuthResponse; status: string }>(
      '/api/v1/auth/register',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, role }),
      },
      false
    );

    const token = res.data.access_token;
    const user: User = {
      id: res.data.user_id,
      email: res.data.email,
      role: (res.data.role as User['role']) || 'researcher',
    };

    httpClient.setToken(token);
    return { user, token };
  },

  async getMe(): Promise<User> {
    const res = await httpClient.request<{ data: User; status: string }>('/api/v1/auth/me');
    return res.data;
  },
};
