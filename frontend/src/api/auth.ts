import { apiClient } from './client'
import type { AuthResponse, LoginRequest, RegisterRequest, TelegramConnectResponse, User } from '@/types'

export async function login(data: LoginRequest): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>('/auth/login', data)
  return response.data
}

export async function register(data: RegisterRequest): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>('/auth/register', data)
  return response.data
}

export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>('/auth/me')
  return response.data
}

export async function refreshTokens(refreshToken: string): Promise<{ access_token: string; refresh_token: string }> {
  const response = await apiClient.post('/auth/refresh', { refresh_token: refreshToken })
  return response.data
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await apiClient.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}

export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout')
}

export async function updateProfile(data: {
  name?: string
  email?: string
  preferred_language?: 'en' | 'ru'
}): Promise<User> {
  const response = await apiClient.patch<User>('/auth/me', data)
  return response.data
}

export async function connectTelegram(): Promise<TelegramConnectResponse> {
  const response = await apiClient.post<TelegramConnectResponse>('/auth/telegram/connect')
  return response.data
}

export async function disconnectTelegram(): Promise<void> {
  await apiClient.delete('/auth/telegram/disconnect')
}

export async function uploadAvatar(file: File): Promise<User> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await apiClient.post<User>('/auth/me/avatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export async function deleteAvatar(): Promise<void> {
  await apiClient.delete('/auth/me/avatar')
}

export async function deleteAccount(confirmation: string): Promise<void> {
  await apiClient.delete('/auth/me', { data: { confirmation } })
}

export async function sendEmailVerification(): Promise<void> {
  await apiClient.post('/auth/send-verification')
}

export async function verifyEmail(token: string): Promise<User> {
  const response = await apiClient.post<User>('/auth/verify-email', { token })
  return response.data
}
