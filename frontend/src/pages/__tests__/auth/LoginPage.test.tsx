import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { LoginPage } from '@/pages/auth/LoginPage'
import * as authApi from '@/api/auth'
import * as workspacesApi from '@/api/workspaces'
import { useAuthStore } from '@/stores/authStore'
import { useWorkspaceStore } from '@/stores/workspaceStore'

// Mock API
vi.mock('@/api/auth', () => ({
  login: vi.fn(),
}))

vi.mock('@/api/workspaces', () => ({
  getWorkspaces: vi.fn(),
}))

// Mock authStore
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn(),
}))

// Mock workspaceStore
vi.mock('@/stores/workspaceStore', () => ({
  useWorkspaceStore: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

describe('LoginPage', () => {
  const mockOnNavigate = vi.fn()
  const mockLogin = vi.fn()
  const mockSetWorkspaces = vi.fn()
  const mockSetCurrentWorkspace = vi.fn()
  const mockSetWorkspacesLoading = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useAuthStore).mockReturnValue({
      user: null,
      isAuthenticated: false,
      login: mockLogin,
      logout: vi.fn(),
      setTokens: vi.fn(),
      updateUser: vi.fn(),
      clearAuth: vi.fn(),
    })
    vi.mocked(useWorkspaceStore).mockReturnValue({
      workspaces: [],
      currentWorkspace: null,
      setWorkspaces: mockSetWorkspaces,
      setCurrentWorkspace: mockSetCurrentWorkspace,
      addWorkspace: vi.fn(),
      updateWorkspace: vi.fn(),
      removeWorkspace: vi.fn(),
      clearWorkspaces: vi.fn(),
      isLoading: false,
      setLoading: mockSetWorkspacesLoading,
    })
    vi.mocked(workspacesApi.getWorkspaces).mockResolvedValue([])
  })

  it('should render login form', () => {
    render(<LoginPage onNavigate={mockOnNavigate} />)

    expect(screen.getByText('CronBox')).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('should allow typing in email and password fields', async () => {
    const { user } = render(<LoginPage onNavigate={mockOnNavigate} />)

    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)

    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')

    expect(emailInput).toHaveValue('test@example.com')
    expect(passwordInput).toHaveValue('password123')
  })

  it('should call login API on form submit', async () => {
    const mockResponse = {
      user: {
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
      },
      tokens: {
        access_token: 'access-token',
        refresh_token: 'refresh-token',
      },
    }
    vi.mocked(authApi.login).mockResolvedValue(mockResponse)

    const { user } = render(<LoginPage onNavigate={mockOnNavigate} />)

    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(authApi.login).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      })
    })
  })

  it('should navigate to dashboard on successful login', async () => {
    const mockResponse = {
      user: {
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
      },
      tokens: {
        access_token: 'access-token',
        refresh_token: 'refresh-token',
      },
    }
    vi.mocked(authApi.login).mockResolvedValue(mockResponse)

    const { user } = render(<LoginPage onNavigate={mockOnNavigate} />)

    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(mockOnNavigate).toHaveBeenCalledWith('dashboard')
    })
  })

  it('should call authStore login on successful login', async () => {
    const mockResponse = {
      user: {
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
      },
      tokens: {
        access_token: 'access-token',
        refresh_token: 'refresh-token',
      },
    }
    vi.mocked(authApi.login).mockResolvedValue(mockResponse)

    const { user } = render(<LoginPage onNavigate={mockOnNavigate} />)

    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith(
        mockResponse.user,
        'access-token',
        'refresh-token'
      )
    })
  })

  it('should show loading state during login', async () => {
    vi.mocked(authApi.login).mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 1000))
    )

    const { user } = render(<LoginPage onNavigate={mockOnNavigate} />)

    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/password/i), 'password123')

    const submitButton = screen.getByRole('button', { name: /sign in/i })
    await user.click(submitButton)

    // Button should show loading state
    await waitFor(() => {
      expect(submitButton).toBeDisabled()
    })
  })

  it('should handle login error', async () => {
    vi.mocked(authApi.login).mockRejectedValue(new Error('Invalid credentials'))

    const { user } = render(<LoginPage onNavigate={mockOnNavigate} />)

    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/password/i), 'wrongpassword')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    // Should not navigate on error
    await waitFor(() => {
      expect(mockOnNavigate).not.toHaveBeenCalled()
    })
  })

  it('should navigate to register page when sign up link clicked', async () => {
    const { user } = render(<LoginPage onNavigate={mockOnNavigate} />)

    await user.click(screen.getByText(/sign up/i))

    expect(mockOnNavigate).toHaveBeenCalledWith('register')
  })
})
