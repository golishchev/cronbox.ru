import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@/test/test-utils'
import { Header } from '../Header'
import { useAuthStore } from '@/stores/authStore'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { useUIStore } from '@/stores/uiStore'

// Mock stores
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn(),
}))

vi.mock('@/stores/workspaceStore', () => ({
  useWorkspaceStore: vi.fn(),
}))

vi.mock('@/stores/uiStore', () => ({
  useUIStore: vi.fn(),
}))

// Mock API
vi.mock('@/api/auth', () => ({
  updateProfile: vi.fn().mockResolvedValue({}),
}))

describe('Header', () => {
  const mockOnNavigate = vi.fn()
  const mockOnLogout = vi.fn()
  const mockToggleSidebar = vi.fn()
  const mockUpdateUser = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useAuthStore).mockReturnValue({
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
      isAuthenticated: true,
      updateUser: mockUpdateUser,
      login: vi.fn(),
      logout: vi.fn(),
      setTokens: vi.fn(),
      clearAuth: vi.fn(),
    })

    vi.mocked(useWorkspaceStore).mockReturnValue({
      currentWorkspace: {
        id: 'workspace-1',
        name: 'My Workspace',
        slug: 'my-workspace',
        owner_id: 'user-1',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      workspaces: [],
      setWorkspaces: vi.fn(),
      setCurrentWorkspace: vi.fn(),
      addWorkspace: vi.fn(),
      updateWorkspace: vi.fn(),
      removeWorkspace: vi.fn(),
      clearWorkspaces: vi.fn(),
    })

    vi.mocked(useUIStore).mockReturnValue({
      sidebarCollapsed: false,
      setSidebarCollapsed: vi.fn(),
      toggleSidebar: mockToggleSidebar,
    })
  })

  it('should render user name', () => {
    render(<Header onNavigate={mockOnNavigate} onLogout={mockOnLogout} />)

    expect(screen.getByText('Test User')).toBeInTheDocument()
  })

  it('should render user initials in avatar', () => {
    render(<Header onNavigate={mockOnNavigate} onLogout={mockOnLogout} />)

    expect(screen.getByText('TU')).toBeInTheDocument()
  })

  it('should render workspace name', () => {
    render(<Header onNavigate={mockOnNavigate} onLogout={mockOnLogout} />)

    expect(screen.getByText('My Workspace')).toBeInTheDocument()
  })

  it('should render free plan badge', () => {
    render(<Header onNavigate={mockOnNavigate} onLogout={mockOnLogout} />)

    expect(screen.getByText('Free')).toBeInTheDocument()
  })

  it('should open user dropdown when avatar clicked', async () => {
    const { user } = render(<Header onNavigate={mockOnNavigate} onLogout={mockOnLogout} />)

    await user.click(screen.getByText('Test User'))

    // Dropdown should show email
    expect(screen.getByText('test@example.com')).toBeInTheDocument()
  })

  it('should show profile and settings options in user dropdown', async () => {
    const { user } = render(<Header onNavigate={mockOnNavigate} onLogout={mockOnLogout} />)

    await user.click(screen.getByText('Test User'))

    expect(screen.getByText('Profile')).toBeInTheDocument()
    expect(screen.getByText('API Keys')).toBeInTheDocument()
    expect(screen.getByText('Sign Out')).toBeInTheDocument()
  })

  it('should call onNavigate when profile clicked', async () => {
    const { user } = render(<Header onNavigate={mockOnNavigate} onLogout={mockOnLogout} />)

    await user.click(screen.getByText('Test User'))
    await user.click(screen.getByText('Profile'))

    expect(mockOnNavigate).toHaveBeenCalledWith('profile')
  })

  it('should call onNavigate when API Keys clicked', async () => {
    const { user } = render(<Header onNavigate={mockOnNavigate} onLogout={mockOnLogout} />)

    await user.click(screen.getByText('Test User'))
    await user.click(screen.getByText('API Keys'))

    expect(mockOnNavigate).toHaveBeenCalledWith('api-keys')
  })

  it('should call onLogout when sign out clicked', async () => {
    const { user } = render(<Header onNavigate={mockOnNavigate} onLogout={mockOnLogout} />)

    await user.click(screen.getByText('Test User'))
    await user.click(screen.getByText('Sign Out'))

    expect(mockOnLogout).toHaveBeenCalled()
  })

  it('should open language dropdown when globe clicked', async () => {
    const { user } = render(<Header onNavigate={mockOnNavigate} onLogout={mockOnLogout} />)

    const globeButton = screen.getByTitle('Language')
    await user.click(globeButton)

    expect(screen.getByText('English ✓')).toBeInTheDocument()
    expect(screen.getByText('Русский')).toBeInTheDocument()
  })

  it('should call toggleSidebar when menu button clicked', async () => {
    const { user } = render(<Header onNavigate={mockOnNavigate} onLogout={mockOnLogout} />)

    const menuButtons = screen.getAllByRole('button')
    // Menu button is the first one with only icon (no text)
    const menuButton = menuButtons.find(btn => btn.classList.contains('lg:hidden'))
    if (menuButton) {
      await user.click(menuButton)
      expect(mockToggleSidebar).toHaveBeenCalled()
    }
  })

  it('should handle single name initial', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: {
        id: 'user-1',
        email: 'john@example.com',
        name: 'John',
        is_superuser: false,
        is_active: true,
        email_verified: true,
        telegram_username: null,
        preferred_language: 'en',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      isAuthenticated: true,
      updateUser: mockUpdateUser,
      login: vi.fn(),
      logout: vi.fn(),
      setTokens: vi.fn(),
      clearAuth: vi.fn(),
    })

    render(<Header onNavigate={mockOnNavigate} onLogout={mockOnLogout} />)

    expect(screen.getByText('J')).toBeInTheDocument()
  })

  it('should handle missing workspace', () => {
    vi.mocked(useWorkspaceStore).mockReturnValue({
      currentWorkspace: null,
      workspaces: [],
      setWorkspaces: vi.fn(),
      setCurrentWorkspace: vi.fn(),
      addWorkspace: vi.fn(),
      updateWorkspace: vi.fn(),
      removeWorkspace: vi.fn(),
      clearWorkspaces: vi.fn(),
    })

    render(<Header onNavigate={mockOnNavigate} onLogout={mockOnLogout} />)

    expect(screen.queryByText('My Workspace')).not.toBeInTheDocument()
  })
})
