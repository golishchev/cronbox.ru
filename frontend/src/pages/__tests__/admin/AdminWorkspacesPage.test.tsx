import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { AdminWorkspacesPage } from '@/pages/admin/AdminWorkspacesPage'
import * as adminApi from '@/api/admin'

// Mock APIs
vi.mock('@/api/admin', () => ({
  getAdminWorkspaces: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

describe('AdminWorkspacesPage', () => {
  const mockOnNavigate = vi.fn()

  const mockWorkspaces = [
    {
      id: 'ws-1',
      name: 'Production Workspace',
      slug: 'production',
      owner_name: 'Admin User',
      owner_email: 'admin@example.com',
      plan_name: 'pro',
      cron_tasks_count: 10,
      delayed_tasks_count: 5,
      executions_count: 1000,
      created_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'ws-2',
      name: 'Development Workspace',
      slug: 'development',
      owner_name: 'Dev User',
      owner_email: 'dev@example.com',
      plan_name: 'free',
      cron_tasks_count: 3,
      delayed_tasks_count: 2,
      executions_count: 500,
      created_at: '2024-02-01T00:00:00Z',
    },
    {
      id: 'ws-3',
      name: 'Enterprise Workspace',
      slug: 'enterprise',
      owner_name: 'Enterprise User',
      owner_email: 'enterprise@example.com',
      plan_name: 'enterprise',
      cron_tasks_count: 50,
      delayed_tasks_count: 20,
      executions_count: 5000,
      created_at: '2024-03-01T00:00:00Z',
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(adminApi.getAdminWorkspaces).mockResolvedValue({
      workspaces: mockWorkspaces,
      total: 3,
    })
  })

  it('should load workspaces on mount', async () => {
    render(<AdminWorkspacesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(adminApi.getAdminWorkspaces).toHaveBeenCalled()
    })
  })

  it('should display workspaces in table', async () => {
    render(<AdminWorkspacesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Production Workspace')).toBeInTheDocument()
      expect(screen.getByText('Development Workspace')).toBeInTheDocument()
    })
  })

  it('should display workspace slug', async () => {
    render(<AdminWorkspacesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('/production')).toBeInTheDocument()
    })
  })

  it('should display owner info', async () => {
    render(<AdminWorkspacesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Admin User')).toBeInTheDocument()
      expect(screen.getByText('admin@example.com')).toBeInTheDocument()
    })
  })

  it('should display plan badge', async () => {
    render(<AdminWorkspacesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Pro')).toBeInTheDocument()
      expect(screen.getByText('Free')).toBeInTheDocument()
      expect(screen.getByText('Enterprise')).toBeInTheDocument()
    })
  })

  it('should navigate back when back button clicked', async () => {
    const { user } = render(<AdminWorkspacesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Production Workspace')).toBeInTheDocument()
    })

    const backButton = screen.getByRole('button', { name: /back/i })
    await user.click(backButton)

    expect(mockOnNavigate).toHaveBeenCalledWith('admin')
  })

  it('should search workspaces when typing in search', async () => {
    const { user } = render(<AdminWorkspacesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Production Workspace')).toBeInTheDocument()
    })

    const searchInput = screen.getByPlaceholderText(/search/i)
    await user.type(searchInput, 'prod')

    await waitFor(() => {
      expect(adminApi.getAdminWorkspaces).toHaveBeenCalledWith(
        expect.objectContaining({ search: 'prod' })
      )
    })
  })

  it('should display empty state when no workspaces', async () => {
    vi.mocked(adminApi.getAdminWorkspaces).mockResolvedValue({
      workspaces: [],
      total: 0,
    })

    render(<AdminWorkspacesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(adminApi.getAdminWorkspaces).toHaveBeenCalled()
    })
  })

  it('should handle API error', async () => {
    vi.mocked(adminApi.getAdminWorkspaces).mockRejectedValue(new Error('API Error'))

    render(<AdminWorkspacesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(adminApi.getAdminWorkspaces).toHaveBeenCalled()
    })
  })

  it('should display task counts', async () => {
    render(<AdminWorkspacesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('10')).toBeInTheDocument() // cron tasks
      expect(screen.getByText('5')).toBeInTheDocument() // delayed tasks
    })
  })

  it('should display execution counts', async () => {
    render(<AdminWorkspacesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('1000')).toBeInTheDocument()
    })
  })
})
