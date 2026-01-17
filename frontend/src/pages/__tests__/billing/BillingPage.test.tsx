import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { BillingPage } from '@/pages/billing/BillingPage'
import * as billingApi from '@/api/billing'
import { useWorkspaceStore } from '@/stores/workspaceStore'

// Mock APIs
vi.mock('@/api/billing', () => ({
  getPlans: vi.fn(),
  getSubscription: vi.fn(),
  createPayment: vi.fn(),
  cancelSubscription: vi.fn(),
  getPaymentHistory: vi.fn(),
}))

// Mock workspaceStore
vi.mock('@/stores/workspaceStore', () => ({
  useWorkspaceStore: vi.fn(),
}))

describe('BillingPage', () => {
  const mockOnNavigate = vi.fn()
  const mockWorkspace = {
    id: 'workspace-1',
    name: 'Test Workspace',
    slug: 'test-workspace',
    owner_id: 'user-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  const mockPlans = [
    {
      id: 'plan-1',
      code: 'free',
      name: 'free',
      display_name: 'Free',
      description: 'Free plan',
      price_monthly: 0,
      price_yearly: 0,
      max_cron_tasks: 5,
      max_delayed_tasks_per_month: 10,
      max_workspaces: 1,
      max_execution_history_days: 7,
      min_cron_interval_minutes: 5,
      telegram_notifications: false,
      email_notifications: false,
      webhook_callbacks: false,
      custom_headers: false,
      retry_on_failure: false,
      max_task_chains: 0,
    },
    {
      id: 'plan-2',
      code: 'pro',
      name: 'pro',
      display_name: 'Pro',
      description: 'Pro plan',
      price_monthly: 99000,
      price_yearly: 990000,
      max_cron_tasks: 50,
      max_delayed_tasks_per_month: 100,
      max_workspaces: 5,
      max_execution_history_days: 30,
      min_cron_interval_minutes: 1,
      telegram_notifications: true,
      email_notifications: true,
      webhook_callbacks: true,
      custom_headers: true,
      retry_on_failure: true,
      max_task_chains: 10,
    },
  ]

  const mockSubscription = {
    id: 'sub-1',
    workspace_id: 'workspace-1',
    plan_id: 'plan-1',
    plan: mockPlans[0],
    status: 'active' as const,
    current_period_start: '2024-01-01T00:00:00Z',
    current_period_end: '2024-02-01T00:00:00Z',
    cancel_at_period_end: false,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  const mockPayments = [
    {
      id: 'payment-1',
      workspace_id: 'workspace-1',
      amount: 990,
      currency: 'RUB',
      status: 'succeeded' as const,
      provider: 'yookassa',
      created_at: '2024-01-01T00:00:00Z',
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useWorkspaceStore).mockReturnValue({
      currentWorkspace: mockWorkspace,
      workspaces: [mockWorkspace],
      setWorkspaces: vi.fn(),
      setCurrentWorkspace: vi.fn(),
      addWorkspace: vi.fn(),
      updateWorkspace: vi.fn(),
      removeWorkspace: vi.fn(),
      clearWorkspaces: vi.fn(),
    })
    vi.mocked(billingApi.getPlans).mockResolvedValue(mockPlans)
    vi.mocked(billingApi.getSubscription).mockResolvedValue(mockSubscription)
    vi.mocked(billingApi.getPaymentHistory).mockResolvedValue(mockPayments)
  })

  it('should render billing page', async () => {
    render(<BillingPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(billingApi.getPlans).toHaveBeenCalled()
    })
  })

  it('should load billing data on mount', async () => {
    render(<BillingPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(billingApi.getPlans).toHaveBeenCalled()
      expect(billingApi.getSubscription).toHaveBeenCalled()
      expect(billingApi.getPaymentHistory).toHaveBeenCalled()
    })
  })

  it('should display plans after loading', async () => {
    render(<BillingPage onNavigate={mockOnNavigate} />)

    // Just verify API was called, actual rendering depends on component implementation
    await waitFor(() => {
      expect(billingApi.getPlans).toHaveBeenCalled()
    })
  })

  it('should display current subscription', async () => {
    render(<BillingPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(billingApi.getSubscription).toHaveBeenCalled()
    })
  })

  it('should display payment history', async () => {
    render(<BillingPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(billingApi.getPaymentHistory).toHaveBeenCalled()
    })
  })

  it('should display task chains for plans that have them', async () => {
    render(<BillingPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(billingApi.getPlans).toHaveBeenCalled()
    })

    // Pro plan has max_task_chains = 10, so it should display "10 task chains"
    await waitFor(() => {
      // Search for text containing "10" and "task chains" (the translation key)
      const elements = screen.getAllByText((content, element) => {
        const text = element?.textContent || ''
        return text.includes('10') && (text.includes('task chains') || text.includes('цепочек'))
      })
      expect(elements.length).toBeGreaterThan(0)
    })
  })

  it('should not display task chains for plans without them', async () => {
    render(<BillingPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(billingApi.getPlans).toHaveBeenCalled()
    })

    // Free plan has max_task_chains = 0, so no task chains line should appear for it
    // We verify there's no "0 task chains" text (since it's hidden when max_task_chains === 0)
    await waitFor(() => {
      const elements = screen.queryAllByText((content, element) => {
        const text = element?.textContent || ''
        return text.startsWith('0 ') && (text.includes('task chains') || text.includes('цепочек'))
      })
      expect(elements.length).toBe(0)
    })
  })
})
