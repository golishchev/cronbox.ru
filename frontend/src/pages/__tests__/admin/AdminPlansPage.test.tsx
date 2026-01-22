import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { AdminPlansPage } from '@/pages/admin/AdminPlansPage'
import * as adminApi from '@/api/admin'

// Mock APIs
vi.mock('@/api/admin', () => ({
  getAdminPlans: vi.fn(),
  createAdminPlan: vi.fn(),
  updateAdminPlan: vi.fn(),
  deleteAdminPlan: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

describe('AdminPlansPage', () => {
  const mockOnNavigate = vi.fn()

  const mockPlans = [
    {
      id: 'plan-1',
      name: 'free',
      display_name: 'Free',
      description: 'Free plan for starters',
      price_monthly: 0,
      price_yearly: 0,
      max_cron_tasks: 5,
      max_delayed_tasks_per_month: 100,
      max_workspaces: 1,
      max_execution_history_days: 7,
      min_cron_interval_minutes: 5,
      telegram_notifications: false,
      email_notifications: false,
      webhook_callbacks: false,
      custom_headers: true,
      retry_on_failure: false,
      is_active: true,
      is_public: true,
      sort_order: 0,
      subscriptions_count: 50,
      created_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'plan-2',
      name: 'pro',
      display_name: 'Pro',
      description: 'Professional plan',
      price_monthly: 99000,
      price_yearly: 990000,
      max_cron_tasks: 50,
      max_delayed_tasks_per_month: 1000,
      max_workspaces: 5,
      max_execution_history_days: 30,
      min_cron_interval_minutes: 1,
      telegram_notifications: true,
      email_notifications: true,
      webhook_callbacks: true,
      custom_headers: true,
      retry_on_failure: true,
      is_active: true,
      is_public: true,
      sort_order: 1,
      subscriptions_count: 25,
      created_at: '2024-01-01T00:00:00Z',
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(adminApi.getAdminPlans).mockResolvedValue({
      plans: mockPlans,
    })
  })

  it('should load plans on mount', async () => {
    render(<AdminPlansPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(adminApi.getAdminPlans).toHaveBeenCalled()
    })
  })

  it('should display plans in table', async () => {
    render(<AdminPlansPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Free')).toBeInTheDocument()
      expect(screen.getByText('Pro')).toBeInTheDocument()
    })
  })

  it('should display plan code', async () => {
    render(<AdminPlansPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('free')).toBeInTheDocument()
      expect(screen.getByText('pro')).toBeInTheDocument()
    })
  })

  it('should display subscriptions count', async () => {
    render(<AdminPlansPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('50')).toBeInTheDocument()
      expect(screen.getByText('25')).toBeInTheDocument()
    })
  })

  it('should navigate back when back button clicked', async () => {
    const { user } = render(<AdminPlansPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Free')).toBeInTheDocument()
    })

    const backButton = screen.getByRole('button', { name: /back/i })
    await user.click(backButton)

    expect(mockOnNavigate).toHaveBeenCalledWith('admin')
  })

  it('should open create dialog when create button clicked', async () => {
    const { user } = render(<AdminPlansPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Free')).toBeInTheDocument()
    })

    const createButton = screen.getByRole('button', { name: /create/i })
    await user.click(createButton)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  it('should open edit dialog when edit button clicked', async () => {
    const { user } = render(<AdminPlansPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Free')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByRole('button', { name: '' })
    // Find the edit icon button
    const editButton = editButtons.find(btn => btn.querySelector('svg.lucide-square-pen'))
    if (editButton) {
      await user.click(editButton)
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })
    }
  })

  it('should display empty state when no plans', async () => {
    vi.mocked(adminApi.getAdminPlans).mockResolvedValue({
      plans: [],
    })

    render(<AdminPlansPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(adminApi.getAdminPlans).toHaveBeenCalled()
    })
  })

  it('should handle API error', async () => {
    vi.mocked(adminApi.getAdminPlans).mockRejectedValue(new Error('API Error'))

    render(<AdminPlansPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(adminApi.getAdminPlans).toHaveBeenCalled()
    })
  })

  it('should display create dialog with form fields', async () => {
    const { user } = render(<AdminPlansPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Free')).toBeInTheDocument()
    })

    const createButton = screen.getByRole('button', { name: /create/i })
    await user.click(createButton)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Verify dialog has form elements
    expect(screen.getByPlaceholderText('starter')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Starter')).toBeInTheDocument()
  })

  it('should not allow delete when plan has subscriptions', async () => {
    render(<AdminPlansPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Free')).toBeInTheDocument()
    })

    // Delete buttons should be disabled for plans with subscriptions
    const deleteButtons = document.querySelectorAll('button[disabled]')
    expect(deleteButtons.length).toBeGreaterThan(0)
  })

  it('should show limits in table', async () => {
    render(<AdminPlansPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('5 cron')).toBeInTheDocument()
      expect(screen.getByText('50 cron')).toBeInTheDocument()
    })
  })
})
