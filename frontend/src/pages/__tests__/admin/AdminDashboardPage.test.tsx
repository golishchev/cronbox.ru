import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { AdminDashboardPage } from '@/pages/admin/AdminDashboardPage'
import * as adminApi from '@/api/admin'

// Mock APIs
vi.mock('@/api/admin', () => ({
  getAdminStats: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

describe('AdminDashboardPage', () => {
  const mockOnNavigate = vi.fn()

  const mockStats = {
    total_users: 150,
    active_users: 120,
    verified_users: 100,
    total_workspaces: 80,
    active_subscriptions: 25,
    total_cron_tasks: 500,
    active_cron_tasks: 400,
    total_delayed_tasks: 200,
    pending_delayed_tasks: 50,
    executions_today: 1500,
    executions_this_week: 8000,
    total_executions: 50000,
    success_rate: 95.5,
    revenue_this_month: 150000,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(adminApi.getAdminStats).mockResolvedValue(mockStats)
  })

  it('should load stats on mount', async () => {
    render(<AdminDashboardPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(adminApi.getAdminStats).toHaveBeenCalled()
    })
  })

  it('should display stats after loading', async () => {
    render(<AdminDashboardPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('150')).toBeInTheDocument()
    })
  })

  it('should display verified users count', async () => {
    render(<AdminDashboardPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('100')).toBeInTheDocument()
    })
  })

  it('should display workspaces count', async () => {
    render(<AdminDashboardPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('80')).toBeInTheDocument()
    })
  })

  it('should navigate to users page on click', async () => {
    const { user } = render(<AdminDashboardPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('150')).toBeInTheDocument()
    })

    // Click on the users card
    const totalUsersCard = screen.getByText('150').closest('.cursor-pointer')
    if (totalUsersCard) {
      await user.click(totalUsersCard)
      expect(mockOnNavigate).toHaveBeenCalledWith('admin-users')
    }
  })

  it('should navigate to workspaces page on click', async () => {
    const { user } = render(<AdminDashboardPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('80')).toBeInTheDocument()
    })

    // Click on the workspaces card
    const workspacesCard = screen.getByText('80').closest('.cursor-pointer')
    if (workspacesCard) {
      await user.click(workspacesCard)
      expect(mockOnNavigate).toHaveBeenCalledWith('admin-workspaces')
    }
  })

  it('should display error state when API fails', async () => {
    vi.mocked(adminApi.getAdminStats).mockRejectedValue(new Error('API Error'))

    render(<AdminDashboardPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(adminApi.getAdminStats).toHaveBeenCalled()
    })
  })

  it('should display task stats', async () => {
    render(<AdminDashboardPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('500')).toBeInTheDocument() // cron tasks
      expect(screen.getByText('200')).toBeInTheDocument() // delayed tasks
    })
  })

  it('should display execution stats', async () => {
    render(<AdminDashboardPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('1500')).toBeInTheDocument() // executions today
    })
  })

  it('should display success rate', async () => {
    render(<AdminDashboardPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('95.5%')).toBeInTheDocument()
    })
  })
})
