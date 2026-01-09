import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { RegisterPage } from '@/pages/auth/RegisterPage'
import * as authApi from '@/api/auth'
import { useAuthStore } from '@/stores/authStore'

// Mock API
vi.mock('@/api/auth', () => ({
  register: vi.fn(),
}))

// Mock authStore
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

describe('RegisterPage', () => {
  const mockOnNavigate = vi.fn()
  const mockLogin = vi.fn()

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
  })

  it('should render register form', () => {
    render(<RegisterPage onNavigate={mockOnNavigate} />)

    expect(screen.getByText('CronBox')).toBeInTheDocument()
    expect(screen.getByLabelText(/^name$/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
  })

  it('should allow typing in all fields', async () => {
    const { user } = render(<RegisterPage onNavigate={mockOnNavigate} />)

    const nameInput = screen.getByLabelText(/^name$/i)
    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/^password$/i)
    const confirmPasswordInput = screen.getByLabelText(/confirm password/i)

    await user.type(nameInput, 'John Doe')
    await user.type(emailInput, 'john@example.com')
    await user.type(passwordInput, 'password123')
    await user.type(confirmPasswordInput, 'password123')

    expect(nameInput).toHaveValue('John Doe')
    expect(emailInput).toHaveValue('john@example.com')
    expect(passwordInput).toHaveValue('password123')
    expect(confirmPasswordInput).toHaveValue('password123')
  })

  it('should call register API on form submit', async () => {
    const mockResponse = {
      user: {
        id: 'user-1',
        email: 'john@example.com',
        name: 'John Doe',
        is_superuser: false,
        is_active: true,
        email_verified: false,
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
    vi.mocked(authApi.register).mockResolvedValue(mockResponse)

    const { user } = render(<RegisterPage onNavigate={mockOnNavigate} />)

    await user.type(screen.getByLabelText(/^name$/i), 'John Doe')
    await user.type(screen.getByLabelText(/email/i), 'john@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(authApi.register).toHaveBeenCalledWith({
        name: 'John Doe',
        email: 'john@example.com',
        password: 'password123',
      })
    })
  })

  it('should navigate to dashboard on successful registration', async () => {
    const mockResponse = {
      user: {
        id: 'user-1',
        email: 'john@example.com',
        name: 'John Doe',
        is_superuser: false,
        is_active: true,
        email_verified: false,
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
    vi.mocked(authApi.register).mockResolvedValue(mockResponse)

    const { user } = render(<RegisterPage onNavigate={mockOnNavigate} />)

    await user.type(screen.getByLabelText(/^name$/i), 'John Doe')
    await user.type(screen.getByLabelText(/email/i), 'john@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(mockOnNavigate).toHaveBeenCalledWith('dashboard')
    })
  })

  it('should not submit when passwords do not match', async () => {
    const { user } = render(<RegisterPage onNavigate={mockOnNavigate} />)

    await user.type(screen.getByLabelText(/^name$/i), 'John Doe')
    await user.type(screen.getByLabelText(/email/i), 'john@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'differentpassword')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(authApi.register).not.toHaveBeenCalled()
    })
  })

  it('should not submit when password is too short', async () => {
    const { user } = render(<RegisterPage onNavigate={mockOnNavigate} />)

    await user.type(screen.getByLabelText(/^name$/i), 'John Doe')
    await user.type(screen.getByLabelText(/email/i), 'john@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'short')
    await user.type(screen.getByLabelText(/confirm password/i), 'short')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(authApi.register).not.toHaveBeenCalled()
    })
  })

  it('should show loading state during registration', async () => {
    vi.mocked(authApi.register).mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 1000))
    )

    const { user } = render(<RegisterPage onNavigate={mockOnNavigate} />)

    await user.type(screen.getByLabelText(/^name$/i), 'John Doe')
    await user.type(screen.getByLabelText(/email/i), 'john@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'password123')

    const submitButton = screen.getByRole('button', { name: /create account/i })
    await user.click(submitButton)

    // Button should be disabled during loading
    await waitFor(() => {
      expect(submitButton).toBeDisabled()
    })
  })

  it('should handle registration error', async () => {
    vi.mocked(authApi.register).mockRejectedValue(new Error('Email already exists'))

    const { user } = render(<RegisterPage onNavigate={mockOnNavigate} />)

    await user.type(screen.getByLabelText(/^name$/i), 'John Doe')
    await user.type(screen.getByLabelText(/email/i), 'existing@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    // Should not navigate on error
    await waitFor(() => {
      expect(mockOnNavigate).not.toHaveBeenCalled()
    })
  })

  it('should navigate to login page when sign in link clicked', async () => {
    const { user } = render(<RegisterPage onNavigate={mockOnNavigate} />)

    await user.click(screen.getByText(/sign in/i))

    expect(mockOnNavigate).toHaveBeenCalledWith('login')
  })
})
