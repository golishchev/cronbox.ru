import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@/test/test-utils'
import { Sidebar } from '../Sidebar'
import { useUIStore } from '@/stores/uiStore'
import { useAuthStore } from '@/stores/authStore'

// Mock stores
vi.mock('@/stores/uiStore', () => ({
  useUIStore: vi.fn(),
}))

vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn(),
}))

describe('Sidebar', () => {
  const mockOnNavigate = vi.fn()
  const mockSetSidebarCollapsed = vi.fn()
  const mockSetMobileSidebarOpen = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useUIStore).mockReturnValue({
      sidebarCollapsed: false,
      setSidebarCollapsed: mockSetSidebarCollapsed,
      toggleSidebar: vi.fn(),
      mobileSidebarOpen: false,
      setMobileSidebarOpen: mockSetMobileSidebarOpen,
      toggleMobileSidebar: vi.fn(),
    })
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
      login: vi.fn(),
      logout: vi.fn(),
      setTokens: vi.fn(),
      updateUser: vi.fn(),
      clearAuth: vi.fn(),
    })
  })

  it('should render CronBox logo', () => {
    render(<Sidebar currentRoute="dashboard" onNavigate={mockOnNavigate} />)

    expect(screen.getByText('CronBox')).toBeInTheDocument()
  })

  it('should render main navigation items', () => {
    render(<Sidebar currentRoute="dashboard" onNavigate={mockOnNavigate} />)

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Cron Tasks')).toBeInTheDocument()
    expect(screen.getByText('Delayed Tasks')).toBeInTheDocument()
    expect(screen.getByText('Executions')).toBeInTheDocument()
  })

  it('should render settings navigation items', () => {
    render(<Sidebar currentRoute="dashboard" onNavigate={mockOnNavigate} />)

    expect(screen.getByText('Billing')).toBeInTheDocument()
    expect(screen.getByText('Notifications')).toBeInTheDocument()
    expect(screen.getByText('API Keys')).toBeInTheDocument()
  })

  it('should highlight current route', () => {
    render(<Sidebar currentRoute="cron" onNavigate={mockOnNavigate} />)

    const cronLink = screen.getByText('Cron Tasks').closest('button')
    expect(cronLink).toHaveClass('bg-primary')
  })

  it('should call onNavigate when nav item clicked', async () => {
    const { user } = render(<Sidebar currentRoute="dashboard" onNavigate={mockOnNavigate} />)

    await user.click(screen.getByText('Cron Tasks'))

    expect(mockOnNavigate).toHaveBeenCalledWith('cron')
  })

  it('should call onNavigate when logo clicked', async () => {
    const { user } = render(<Sidebar currentRoute="cron" onNavigate={mockOnNavigate} />)

    await user.click(screen.getByText('CronBox'))

    expect(mockOnNavigate).toHaveBeenCalledWith('dashboard')
  })

  it('should toggle sidebar collapsed state when chevron clicked', async () => {
    const { user } = render(<Sidebar currentRoute="dashboard" onNavigate={mockOnNavigate} />)

    const chevronButton = screen.getByRole('button', { name: '' })
    await user.click(chevronButton)

    expect(mockSetSidebarCollapsed).toHaveBeenCalledWith(true)
  })

  it('should not show admin navigation for regular users', () => {
    render(<Sidebar currentRoute="dashboard" onNavigate={mockOnNavigate} />)

    expect(screen.queryByText('Admin Dashboard')).not.toBeInTheDocument()
  })

  it('should show admin navigation for superusers', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: {
        id: 'user-1',
        email: 'admin@example.com',
        name: 'Admin User',
        is_superuser: true,
        is_active: true,
        email_verified: true,
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

    render(<Sidebar currentRoute="dashboard" onNavigate={mockOnNavigate} />)

    expect(screen.getByText('Admin Dashboard')).toBeInTheDocument()
  })

  it('should hide labels when collapsed', () => {
    vi.mocked(useUIStore).mockReturnValue({
      sidebarCollapsed: true,
      setSidebarCollapsed: mockSetSidebarCollapsed,
      toggleSidebar: vi.fn(),
      mobileSidebarOpen: false,
      setMobileSidebarOpen: mockSetMobileSidebarOpen,
      toggleMobileSidebar: vi.fn(),
    })

    render(<Sidebar currentRoute="dashboard" onNavigate={mockOnNavigate} />)

    // Text should not be visible when collapsed
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument()
    expect(screen.queryByText('CronBox')).not.toBeInTheDocument()
  })

  it('should show section labels when expanded', () => {
    render(<Sidebar currentRoute="dashboard" onNavigate={mockOnNavigate} />)

    expect(screen.getByText('Main')).toBeInTheDocument()
    // There are multiple "Settings" elements - the label and nav item
    // Use getAllByText and check at least one exists
    expect(screen.getAllByText('Settings').length).toBeGreaterThan(0)
  })

  it('should close mobile sidebar when nav item clicked', async () => {
    const { user } = render(<Sidebar currentRoute="dashboard" onNavigate={mockOnNavigate} />)

    await user.click(screen.getByText('Cron Tasks'))

    expect(mockSetMobileSidebarOpen).toHaveBeenCalledWith(false)
  })

  it('should close mobile sidebar when logo clicked', async () => {
    const { user } = render(<Sidebar currentRoute="cron" onNavigate={mockOnNavigate} />)

    await user.click(screen.getByText('CronBox'))

    expect(mockSetMobileSidebarOpen).toHaveBeenCalledWith(false)
  })

  it('should show labels when mobile sidebar is open even if collapsed', () => {
    vi.mocked(useUIStore).mockReturnValue({
      sidebarCollapsed: true,
      setSidebarCollapsed: mockSetSidebarCollapsed,
      toggleSidebar: vi.fn(),
      mobileSidebarOpen: true,
      setMobileSidebarOpen: mockSetMobileSidebarOpen,
      toggleMobileSidebar: vi.fn(),
    })

    render(<Sidebar currentRoute="dashboard" onNavigate={mockOnNavigate} />)

    // Labels should be visible when mobile sidebar is open
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('CronBox')).toBeInTheDocument()
  })
})
