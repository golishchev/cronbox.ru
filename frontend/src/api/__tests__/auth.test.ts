import { describe, it, expect, beforeEach, vi } from 'vitest'
import { login, register, getCurrentUser, refreshTokens, changePassword, logout, updateProfile } from '../auth'
import { apiClient } from '../client'
import { mockUser } from '@/test/mocks/data'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('auth API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('login', () => {
    it('should call post with correct data and return response', async () => {
      const mockResponse = {
        data: {
          user: mockUser,
          access_token: 'token',
          refresh_token: 'refresh',
        },
      }
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const result = await login({ email: 'test@example.com', password: 'password123' })

      expect(apiClient.post).toHaveBeenCalledWith('/auth/login', {
        email: 'test@example.com',
        password: 'password123',
      })
      expect(result.user.email).toBe('test@example.com')
    })

    it('should throw error on failed login', async () => {
      vi.mocked(apiClient.post).mockRejectedValue(new Error('Invalid credentials'))

      await expect(login({ email: 'wrong@example.com', password: 'wrong' })).rejects.toThrow()
    })
  })

  describe('register', () => {
    it('should call post with registration data', async () => {
      const mockResponse = {
        data: {
          user: { ...mockUser, email: 'new@example.com', name: 'New User' },
          access_token: 'token',
          refresh_token: 'refresh',
        },
      }
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const result = await register({
        email: 'new@example.com',
        password: 'password123',
        name: 'New User',
      })

      expect(apiClient.post).toHaveBeenCalledWith('/auth/register', {
        email: 'new@example.com',
        password: 'password123',
        name: 'New User',
      })
      expect(result.user.name).toBe('New User')
    })
  })

  describe('getCurrentUser', () => {
    it('should call get and return user data', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockUser })

      const user = await getCurrentUser()

      expect(apiClient.get).toHaveBeenCalledWith('/auth/me')
      expect(user.email).toBe('test@example.com')
    })
  })

  describe('refreshTokens', () => {
    it('should call post with refresh token', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { access_token: 'new_access', refresh_token: 'new_refresh' },
      })

      const result = await refreshTokens('old_refresh_token')

      expect(apiClient.post).toHaveBeenCalledWith('/auth/refresh', {
        refresh_token: 'old_refresh_token',
      })
      expect(result.access_token).toBe('new_access')
    })
  })

  describe('changePassword', () => {
    it('should call post with passwords', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: {} })

      await changePassword('oldpass', 'newpass')

      expect(apiClient.post).toHaveBeenCalledWith('/auth/change-password', {
        current_password: 'oldpass',
        new_password: 'newpass',
      })
    })
  })

  describe('logout', () => {
    it('should call post to logout', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: {} })

      await logout()

      expect(apiClient.post).toHaveBeenCalledWith('/auth/logout')
    })
  })

  describe('updateProfile', () => {
    it('should call patch with profile data', async () => {
      vi.mocked(apiClient.patch).mockResolvedValue({
        data: { ...mockUser, name: 'Updated Name' },
      })

      const result = await updateProfile({ name: 'Updated Name' })

      expect(apiClient.patch).toHaveBeenCalledWith('/auth/me', { name: 'Updated Name' })
      expect(result.name).toBe('Updated Name')
    })
  })
})
