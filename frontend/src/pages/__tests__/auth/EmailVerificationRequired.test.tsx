import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { EmailVerificationRequired } from '../../auth/EmailVerificationRequired'
import { useAuthStore } from '@/stores/authStore'
import * as authApi from '@/api/auth'

vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn(),
}))

vi.mock('@/api/auth', () => ({
  sendEmailVerification: vi.fn(),
}))

describe('EmailVerificationRequired', () => {
  const mockOnLogout = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
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
      login: vi.fn(),
      logout: vi.fn(),
      setTokens: vi.fn(),
      updateUser: vi.fn(),
      clearAuth: vi.fn(),
    })
  })

  it('should render verification required message', () => {
    render(<EmailVerificationRequired onLogout={mockOnLogout} />)

    // i18n keys are shown in tests
    expect(screen.getByText('auth.emailVerificationRequired.title')).toBeInTheDocument()
    expect(screen.getByText('auth.emailVerificationRequired.description')).toBeInTheDocument()
  })

  it('should display user email', () => {
    render(<EmailVerificationRequired onLogout={mockOnLogout} />)

    expect(screen.getByText('test@example.com')).toBeInTheDocument()
  })

  it('should call onLogout when sign out button is clicked', async () => {
    const { user } = render(<EmailVerificationRequired onLogout={mockOnLogout} />)

    await user.click(screen.getByText('auth.emailVerificationRequired.logout'))

    expect(mockOnLogout).toHaveBeenCalled()
  })

  it('should call sendEmailVerification when resend button is clicked', async () => {
    vi.mocked(authApi.sendEmailVerification).mockResolvedValue(undefined)

    const { user } = render(<EmailVerificationRequired onLogout={mockOnLogout} />)

    await user.click(screen.getByText('auth.emailVerificationRequired.resend'))

    await waitFor(() => {
      expect(authApi.sendEmailVerification).toHaveBeenCalled()
    })
  })

  it('should show cooldown after successful resend', async () => {
    vi.mocked(authApi.sendEmailVerification).mockResolvedValue(undefined)

    const { user } = render(<EmailVerificationRequired onLogout={mockOnLogout} />)

    await user.click(screen.getByText('auth.emailVerificationRequired.resend'))

    await waitFor(() => {
      // Cooldown shows the i18n key with interpolated seconds
      expect(screen.getByText(/auth\.emailVerificationRequired\.resendIn/)).toBeInTheDocument()
    })
  })

  it('should show error message on resend failure', async () => {
    vi.mocked(authApi.sendEmailVerification).mockRejectedValue(new Error('Rate limit exceeded'))

    const { user } = render(<EmailVerificationRequired onLogout={mockOnLogout} />)

    await user.click(screen.getByText('auth.emailVerificationRequired.resend'))

    await waitFor(() => {
      expect(screen.getByText(/Rate limit exceeded/i)).toBeInTheDocument()
    })
  })

  it('should disable resend button while sending', async () => {
    vi.mocked(authApi.sendEmailVerification).mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 1000))
    )

    const { user } = render(<EmailVerificationRequired onLogout={mockOnLogout} />)

    await user.click(screen.getByText('auth.emailVerificationRequired.resend'))

    expect(screen.getByText('auth.emailVerificationRequired.sending')).toBeInTheDocument()
  })
})
