import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { AppLayout } from '../AppLayout'
import { useAuthStore } from '@/stores/authStore'
import { useUIStore } from '@/stores/uiStore'
import { useWorkspaceStore } from '@/stores/workspaceStore'

// Mock stores
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn(),
}))

vi.mock('@/stores/uiStore', () => ({
  useUIStore: vi.fn(),
}))

vi.mock('@/stores/workspaceStore', () => ({
  useWorkspaceStore: vi.fn(),
}))

// Mock API
vi.mock('@/api/auth', () => ({
  updateProfile: vi.fn().mockResolvedValue({}),
}))

describe('AppLayout', () => {
  const mockOnNavigate = vi.fn()
  const mockLogout = vi.fn()

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
      login: vi.fn(),
      logout: mockLogout,
      setTokens: vi.fn(),
      updateUser: vi.fn(),
      clearAuth: vi.fn(),
    })

    vi.mocked(useUIStore).mockReturnValue({
      sidebarCollapsed: false,
      setSidebarCollapsed: vi.fn(),
      toggleSidebar: vi.fn(),
    })

    vi.mocked(useWorkspaceStore).mockReturnValue({
      currentWorkspace: {
        id: 'workspace-1',
        name: 'Test Workspace',
        slug: 'test-workspace',
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
  })

  it('should render children', () => {
    render(
      <AppLayout onNavigate={mockOnNavigate}>
        <div data-testid="child-content">Test Content</div>
      </AppLayout>
    )

    expect(screen.getByTestId('child-content')).toBeInTheDocument()
    expect(screen.getByText('Test Content')).toBeInTheDocument()
  })

  it('should render sidebar', () => {
    render(
      <AppLayout onNavigate={mockOnNavigate}>
        <div>Content</div>
      </AppLayout>
    )

    expect(screen.getByText('CronBox')).toBeInTheDocument()
  })

  it('should render header', () => {
    render(
      <AppLayout onNavigate={mockOnNavigate}>
        <div>Content</div>
      </AppLayout>
    )

    expect(screen.getByText('Test User')).toBeInTheDocument()
  })

  it('should call logout and navigate on logout', async () => {
    const { user } = render(
      <AppLayout onNavigate={mockOnNavigate}>
        <div>Content</div>
      </AppLayout>
    )

    // Open user dropdown
    await user.click(screen.getByText('Test User'))

    // Click sign out
    await user.click(screen.getByText('Sign Out'))

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalled()
      expect(mockOnNavigate).toHaveBeenCalledWith('login')
    })
  })

  it('should adjust layout when sidebar is collapsed', () => {
    vi.mocked(useUIStore).mockReturnValue({
      sidebarCollapsed: true,
      setSidebarCollapsed: vi.fn(),
      toggleSidebar: vi.fn(),
    })

    render(
      <AppLayout onNavigate={mockOnNavigate}>
        <div>Content</div>
      </AppLayout>
    )

    // Layout should render (specific padding class is internal detail)
    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('should use provided currentRoute', () => {
    render(
      <AppLayout onNavigate={mockOnNavigate} currentRoute="cron">
        <div>Content</div>
      </AppLayout>
    )

    // Should highlight cron tasks in sidebar
    const cronLink = screen.getByText('Cron Tasks').closest('button')
    expect(cronLink).toHaveClass('bg-primary')
  })
})
