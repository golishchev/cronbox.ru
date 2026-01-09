import { describe, it, expect, beforeEach, vi } from 'vitest'
import { act } from '@testing-library/react'
import { useAuthStore } from '../authStore'
import { createMockUser } from '@/test/mocks/data'

// Mock i18n
vi.mock('@/lib/i18n', () => ({
  default: {
    changeLanguage: vi.fn(),
    language: 'en',
  },
}))

describe('authStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: true,
    })
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should have correct initial state', () => {
      const state = useAuthStore.getState()

      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
      expect(state.isLoading).toBe(true)
    })
  })

  describe('setUser', () => {
    it('should set user and update isAuthenticated', () => {
      const mockUser = createMockUser()

      act(() => {
        useAuthStore.getState().setUser(mockUser)
      })

      const state = useAuthStore.getState()
      expect(state.user).toEqual(mockUser)
      expect(state.isAuthenticated).toBe(true)
    })

    it('should set isAuthenticated to false when user is null', () => {
      // First set a user
      const mockUser = createMockUser()
      useAuthStore.setState({ user: mockUser, isAuthenticated: true })

      act(() => {
        useAuthStore.getState().setUser(null)
      })

      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
    })

    it('should change language when user has preferred_language', async () => {
      const { default: i18n } = await import('@/lib/i18n')
      const mockUser = createMockUser({ preferred_language: 'ru' })

      act(() => {
        useAuthStore.getState().setUser(mockUser)
      })

      expect(i18n.changeLanguage).toHaveBeenCalledWith('ru')
    })
  })

  describe('setLoading', () => {
    it('should set loading state', () => {
      act(() => {
        useAuthStore.getState().setLoading(false)
      })

      expect(useAuthStore.getState().isLoading).toBe(false)

      act(() => {
        useAuthStore.getState().setLoading(true)
      })

      expect(useAuthStore.getState().isLoading).toBe(true)
    })
  })

  describe('login', () => {
    it('should set user, tokens, and update state', () => {
      const mockUser = createMockUser()
      const accessToken = 'test_access_token'
      const refreshToken = 'test_refresh_token'

      act(() => {
        useAuthStore.getState().login(mockUser, accessToken, refreshToken)
      })

      const state = useAuthStore.getState()
      expect(state.user).toEqual(mockUser)
      expect(state.isAuthenticated).toBe(true)
      expect(state.isLoading).toBe(false)
      expect(localStorage.setItem).toHaveBeenCalledWith('access_token', accessToken)
      expect(localStorage.setItem).toHaveBeenCalledWith('refresh_token', refreshToken)
    })

    it('should change language on login if user has preferred_language', async () => {
      const { default: i18n } = await import('@/lib/i18n')
      const mockUser = createMockUser({ preferred_language: 'ru' })

      act(() => {
        useAuthStore.getState().login(mockUser, 'token', 'refresh')
      })

      expect(i18n.changeLanguage).toHaveBeenCalledWith('ru')
    })
  })

  describe('logout', () => {
    it('should clear user, tokens, and reset state', () => {
      // First login
      const mockUser = createMockUser()
      useAuthStore.setState({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
      })

      act(() => {
        useAuthStore.getState().logout()
      })

      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
      expect(state.isLoading).toBe(false)
      expect(localStorage.removeItem).toHaveBeenCalledWith('access_token')
      expect(localStorage.removeItem).toHaveBeenCalledWith('refresh_token')
    })
  })

  describe('updateUser', () => {
    it('should merge updates with existing user', () => {
      const mockUser = createMockUser({ name: 'Old Name' })
      useAuthStore.setState({ user: mockUser, isAuthenticated: true })

      act(() => {
        useAuthStore.getState().updateUser({ name: 'New Name' })
      })

      const state = useAuthStore.getState()
      expect(state.user?.name).toBe('New Name')
      expect(state.user?.email).toBe(mockUser.email) // Other fields preserved
    })

    it('should do nothing if no user exists', () => {
      useAuthStore.setState({ user: null, isAuthenticated: false })

      act(() => {
        useAuthStore.getState().updateUser({ name: 'New Name' })
      })

      expect(useAuthStore.getState().user).toBeNull()
    })

    it('should change language when updating preferred_language', async () => {
      const { default: i18n } = await import('@/lib/i18n')
      const mockUser = createMockUser({ preferred_language: 'en' })
      useAuthStore.setState({ user: mockUser, isAuthenticated: true })

      act(() => {
        useAuthStore.getState().updateUser({ preferred_language: 'ru' })
      })

      expect(i18n.changeLanguage).toHaveBeenCalledWith('ru')
    })

    it('should not change language when updating other fields', async () => {
      const { default: i18n } = await import('@/lib/i18n')
      const mockUser = createMockUser()
      useAuthStore.setState({ user: mockUser, isAuthenticated: true })
      vi.clearAllMocks()

      act(() => {
        useAuthStore.getState().updateUser({ name: 'Updated Name' })
      })

      expect(i18n.changeLanguage).not.toHaveBeenCalled()
    })
  })
})
