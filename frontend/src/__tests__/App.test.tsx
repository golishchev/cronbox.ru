import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import App from '@/App'
import * as authApi from '@/api/auth'
import { useAuthStore } from '@/stores/authStore'

// Mock APIs
vi.mock('@/api/auth', () => ({
  getCurrentUser: vi.fn(),
}))

vi.mock('@/api/workspaces', () => ({
  getWorkspaces: vi.fn(() => Promise.resolve([])),
}))

// Mock stores
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn(),
}))

vi.mock('@/stores/workspaceStore', () => ({
  useWorkspaceStore: vi.fn(() => ({
    currentWorkspace: null,
    workspaces: [],
    setWorkspaces: vi.fn(),
    setCurrentWorkspace: vi.fn(),
    addWorkspace: vi.fn(),
    updateWorkspace: vi.fn(),
    removeWorkspace: vi.fn(),
    clearWorkspaces: vi.fn(),
    isLoading: false,
    setLoading: vi.fn(),
  })),
}))

vi.mock('@/stores/uiStore', () => ({
  useUIStore: vi.fn(() => ({
    sidebarCollapsed: false,
    setSidebarCollapsed: vi.fn(),
    toggleSidebar: vi.fn(),
  })),
}))

describe('App', () => {
  const mockSetUser = vi.fn()
  const mockSetLoading = vi.fn()
  const mockLogout = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('should render login page when not authenticated', async () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      login: vi.fn(),
      logout: mockLogout,
      setTokens: vi.fn(),
      updateUser: vi.fn(),
      clearAuth: vi.fn(),
      setUser: mockSetUser,
      setLoading: mockSetLoading,
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('CronBox')).toBeInTheDocument()
    })
  })

  it('should show loading state', async () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: true,
      login: vi.fn(),
      logout: mockLogout,
      setTokens: vi.fn(),
      updateUser: vi.fn(),
      clearAuth: vi.fn(),
      setUser: mockSetUser,
      setLoading: mockSetLoading,
    })

    render(<App />)

    // Should show loading indicator (either spinner or loading screen)
    // The component renders a loading div with justify-center when isLoading is true
    const loadingContainer = document.querySelector('.justify-center')
    expect(loadingContainer).toBeInTheDocument()
  })

  it('should check auth on mount when token exists', async () => {
    localStorage.setItem('access_token', 'test-token')

    vi.mocked(useAuthStore).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      login: vi.fn(),
      logout: mockLogout,
      setTokens: vi.fn(),
      updateUser: vi.fn(),
      clearAuth: vi.fn(),
      setUser: mockSetUser,
      setLoading: mockSetLoading,
    })

    vi.mocked(authApi.getCurrentUser).mockResolvedValue({
      id: 'user-1',
      email: 'test@example.com',
      name: 'Test User',
      is_superuser: false,
      is_active: true,
      email_verified: true,
      telegram_username: null,
      preferred_language: 'en',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    })

    render(<App />)

    await waitFor(() => {
      expect(authApi.getCurrentUser).toHaveBeenCalled()
    })
  })

  it('should logout on auth error', async () => {
    localStorage.setItem('access_token', 'invalid-token')

    vi.mocked(useAuthStore).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      login: vi.fn(),
      logout: mockLogout,
      setTokens: vi.fn(),
      updateUser: vi.fn(),
      clearAuth: vi.fn(),
      setUser: mockSetUser,
      setLoading: mockSetLoading,
    })

    vi.mocked(authApi.getCurrentUser).mockRejectedValue(new Error('Invalid token'))

    render(<App />)

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalled()
    })
  })

  it('should show email verification required screen for unverified users', async () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: {
        id: 'user-1',
        email: 'test@example.com',
        name: 'Test User',
        is_superuser: false,
        is_active: true,
        email_verified: false,
        telegram_username: null,
        preferred_language: 'en',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: mockLogout,
      setTokens: vi.fn(),
      updateUser: vi.fn(),
      clearAuth: vi.fn(),
      setUser: mockSetUser,
      setLoading: mockSetLoading,
    })

    render(<App />)

    await waitFor(() => {
      // i18n keys are shown in tests
      expect(screen.getByText('auth.emailVerificationRequired.title')).toBeInTheDocument()
      expect(screen.getByText('test@example.com')).toBeInTheDocument()
    })
  })
})
