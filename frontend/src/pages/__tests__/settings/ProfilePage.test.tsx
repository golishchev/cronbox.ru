import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { ProfilePage } from '@/pages/settings/ProfilePage'
import * as authApi from '@/api/auth'
import { useAuthStore } from '@/stores/authStore'

// Mock API
vi.mock('@/api/auth', () => ({
  updateProfile: vi.fn(),
}))

// Mock authStore
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn(),
}))

describe('ProfilePage', () => {
  const mockOnNavigate = vi.fn()
  const mockUpdateUser = vi.fn()
  const mockUser = {
    id: 'user-1',
    email: 'test@example.com',
    name: 'Test User',
    is_superuser: false,
    is_active: true,
    email_verified: true,
    telegram_username: null,
    telegram_id: null,
    preferred_language: 'en' as const,
    avatar_url: null,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useAuthStore).mockReturnValue({
      user: mockUser,
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      setTokens: vi.fn(),
      updateUser: mockUpdateUser,
      clearAuth: vi.fn(),
    })
  })

  it('should render profile page sections', () => {
    render(<ProfilePage onNavigate={mockOnNavigate} />)

    expect(screen.getByText('Profile')).toBeInTheDocument()
    expect(screen.getByText('Personal Information')).toBeInTheDocument()
    expect(screen.getByText('Account Information')).toBeInTheDocument()
  })

  it('should display user name in input', () => {
    render(<ProfilePage onNavigate={mockOnNavigate} />)

    const nameInput = screen.getByLabelText(/^name$/i)
    expect(nameInput).toHaveValue('Test User')
  })

  it('should display user email (disabled)', () => {
    render(<ProfilePage onNavigate={mockOnNavigate} />)

    const emailInput = screen.getByLabelText(/email/i)
    expect(emailInput).toHaveValue('test@example.com')
    expect(emailInput).toBeDisabled()
  })

  it('should show verified badge when email is verified', () => {
    render(<ProfilePage onNavigate={mockOnNavigate} />)

    expect(screen.getByText('Verified')).toBeInTheDocument()
  })

  it('should show not verified badge when email is not verified', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: { ...mockUser, email_verified: false },
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      setTokens: vi.fn(),
      updateUser: mockUpdateUser,
      clearAuth: vi.fn(),
    })

    render(<ProfilePage onNavigate={mockOnNavigate} />)

    expect(screen.getByText('Not verified')).toBeInTheDocument()
  })

  it('should show telegram not connected when no telegram_id', () => {
    render(<ProfilePage onNavigate={mockOnNavigate} />)

    expect(screen.getByText('Connect Telegram')).toBeInTheDocument()
  })

  it('should disable save button when no changes', () => {
    render(<ProfilePage onNavigate={mockOnNavigate} />)

    const saveButton = screen.getByRole('button', { name: /save/i })
    expect(saveButton).toBeDisabled()
  })

  it('should enable save button when name changed', async () => {
    const { user } = render(<ProfilePage onNavigate={mockOnNavigate} />)

    const nameInput = screen.getByLabelText(/^name$/i)
    await user.clear(nameInput)
    await user.type(nameInput, 'New Name')

    const saveButton = screen.getByRole('button', { name: /save/i })
    expect(saveButton).not.toBeDisabled()
  })

  it('should call updateProfile API when save clicked', async () => {
    vi.mocked(authApi.updateProfile).mockResolvedValue({
      ...mockUser,
      name: 'New Name',
    })

    const { user } = render(<ProfilePage onNavigate={mockOnNavigate} />)

    const nameInput = screen.getByLabelText(/^name$/i)
    await user.clear(nameInput)
    await user.type(nameInput, 'New Name')

    await user.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => {
      expect(authApi.updateProfile).toHaveBeenCalledWith({
        name: 'New Name',
        preferred_language: undefined,
      })
    })
  })

  it('should update user in store after successful save', async () => {
    const updatedUser = { ...mockUser, name: 'New Name' }
    vi.mocked(authApi.updateProfile).mockResolvedValue(updatedUser)

    const { user } = render(<ProfilePage onNavigate={mockOnNavigate} />)

    const nameInput = screen.getByLabelText(/^name$/i)
    await user.clear(nameInput)
    await user.type(nameInput, 'New Name')

    await user.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => {
      expect(mockUpdateUser).toHaveBeenCalledWith(updatedUser)
    })
  })

  it('should show success message after save', async () => {
    vi.mocked(authApi.updateProfile).mockResolvedValue({
      ...mockUser,
      name: 'New Name',
    })

    const { user } = render(<ProfilePage onNavigate={mockOnNavigate} />)

    const nameInput = screen.getByLabelText(/^name$/i)
    await user.clear(nameInput)
    await user.type(nameInput, 'New Name')

    await user.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => {
      expect(screen.getByText('Settings saved')).toBeInTheDocument()
    })
  })

  it('should show error message on API failure', async () => {
    vi.mocked(authApi.updateProfile).mockRejectedValue(new Error('Update failed'))

    const { user } = render(<ProfilePage onNavigate={mockOnNavigate} />)

    const nameInput = screen.getByLabelText(/^name$/i)
    await user.clear(nameInput)
    await user.type(nameInput, 'New Name')

    await user.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => {
      expect(screen.getByText('Update failed')).toBeInTheDocument()
    })
  })

  it('should display member since date', () => {
    render(<ProfilePage onNavigate={mockOnNavigate} />)

    expect(screen.getByText('Member since')).toBeInTheDocument()
  })

  it('should render language selector', () => {
    render(<ProfilePage onNavigate={mockOnNavigate} />)

    expect(screen.getByRole('combobox')).toBeInTheDocument()
  })
})
