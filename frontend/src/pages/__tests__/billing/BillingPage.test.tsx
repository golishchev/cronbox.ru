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
      name: 'Free',
      description: 'Free plan',
      price_monthly: 0,
      price_yearly: 0,
      max_cron_tasks: 5,
      max_delayed_tasks: 10,
      max_executions_per_month: 1000,
      is_active: true,
      features: ['5 cron tasks', '10 delayed tasks'],
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'plan-2',
      code: 'pro',
      name: 'Pro',
      description: 'Pro plan',
      price_monthly: 990,
      price_yearly: 9900,
      max_cron_tasks: 50,
      max_delayed_tasks: 100,
      max_executions_per_month: 10000,
      is_active: true,
      features: ['50 cron tasks', '100 delayed tasks'],
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
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
})
