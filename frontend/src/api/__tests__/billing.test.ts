import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  getPlans,
  getSubscription,
  createPayment,
  cancelSubscription,
  getPaymentHistory,
} from '../billing'
import { apiClient } from '../client'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('billing API', () => {
  const workspaceId = 'workspace-1'

  const mockPlan = {
    id: 'pro',
    name: 'pro',
    display_name: 'Pro',
    description: 'Professional plan',
    price_monthly: 990,
    price_yearly: 9900,
    max_cron_tasks: 100,
    max_delayed_tasks_per_month: 10000,
    max_workspaces: 5,
    max_execution_history_days: 30,
    min_cron_interval_minutes: 1,
    telegram_notifications: true,
    email_notifications: true,
    webhook_callbacks: true,
    custom_headers: true,
    retry_on_failure: true,
  }

  const mockSubscription = {
    id: 'sub-1',
    workspace_id: workspaceId,
    plan_id: 'pro',
    status: 'active',
    current_period_start: '2024-01-01T00:00:00Z',
    current_period_end: '2024-02-01T00:00:00Z',
    cancel_at_period_end: false,
    cancelled_at: null,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getPlans', () => {
    it('should return list of plans', async () => {
      const plans = [
        { ...mockPlan, id: 'free', name: 'free', price_monthly: 0 },
        mockPlan,
        { ...mockPlan, id: 'business', name: 'business', price_monthly: 2990 },
      ]
      vi.mocked(apiClient.get).mockResolvedValue({ data: plans })

      const result = await getPlans()

      expect(apiClient.get).toHaveBeenCalledWith('/plans')
      expect(Array.isArray(result)).toBe(true)
      expect(result.length).toBe(3)
      expect(result[0].id).toBeDefined()
      expect(result[0].price_monthly).toBeDefined()
    })
  })

  describe('getSubscription', () => {
    it('should return subscription for workspace', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockSubscription })

      const result = await getSubscription(workspaceId)

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/workspace-1/subscription')
      expect(result).not.toBeNull()
      expect(result?.id).toBeDefined()
      expect(result?.status).toBeDefined()
      expect(result?.plan_id).toBeDefined()
    })

    it('should return null when no subscription', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: null })

      const result = await getSubscription(workspaceId)

      expect(result).toBeNull()
    })
  })

  describe('createPayment', () => {
    it('should create monthly payment', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: {
          id: 'payment-123',
          workspace_id: workspaceId,
          amount: 990,
          currency: 'RUB',
          status: 'pending',
          description: 'Pro plan subscription',
          yookassa_confirmation_url: 'https://yookassa.ru/checkout/123',
          paid_at: null,
          created_at: new Date().toISOString(),
        },
      })

      const result = await createPayment(workspaceId, 'pro', 'monthly')

      expect(apiClient.post).toHaveBeenCalledWith('/workspaces/workspace-1/subscribe', {
        plan_id: 'pro',
        billing_period: 'monthly',
        return_url: undefined,
      })
      expect(result.id).toBeDefined()
      expect(result.status).toBe('pending')
      expect(result.yookassa_confirmation_url).toBeDefined()
    })

    it('should create yearly payment', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: {
          id: 'payment-124',
          workspace_id: workspaceId,
          amount: 9900,
          currency: 'RUB',
          status: 'pending',
          description: null,
          yookassa_confirmation_url: 'https://yookassa.ru/checkout/124',
          paid_at: null,
          created_at: new Date().toISOString(),
        },
      })

      const result = await createPayment(workspaceId, 'pro', 'yearly')

      expect(apiClient.post).toHaveBeenCalledWith('/workspaces/workspace-1/subscribe', {
        plan_id: 'pro',
        billing_period: 'yearly',
        return_url: undefined,
      })
      expect(result.amount).toBe(9900)
    })

    it('should include return URL', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: {
          id: 'payment-125',
          workspace_id: workspaceId,
          amount: 990,
          currency: 'RUB',
          status: 'pending',
          description: null,
          yookassa_confirmation_url: 'https://yookassa.ru/checkout/125',
          paid_at: null,
          created_at: new Date().toISOString(),
        },
      })

      await createPayment(workspaceId, 'pro', 'monthly', 'https://cronbox.ru/billing')

      expect(apiClient.post).toHaveBeenCalledWith('/workspaces/workspace-1/subscribe', {
        plan_id: 'pro',
        billing_period: 'monthly',
        return_url: 'https://cronbox.ru/billing',
      })
    })
  })

  describe('cancelSubscription', () => {
    it('should cancel subscription at period end', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { success: true } })

      await expect(cancelSubscription(workspaceId, false)).resolves.not.toThrow()

      expect(apiClient.post).toHaveBeenCalledWith('/workspaces/workspace-1/subscription/cancel', {
        immediately: false,
      })
    })

    it('should cancel subscription immediately', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { success: true } })

      await expect(cancelSubscription(workspaceId, true)).resolves.not.toThrow()

      expect(apiClient.post).toHaveBeenCalledWith('/workspaces/workspace-1/subscription/cancel', {
        immediately: true,
      })
    })
  })

  describe('getPaymentHistory', () => {
    it('should return payment history', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: [
          {
            id: 'payment-1',
            workspace_id: workspaceId,
            amount: 990,
            currency: 'RUB',
            status: 'succeeded',
            description: 'Pro plan',
            paid_at: '2024-01-01T00:00:00Z',
            created_at: '2024-01-01T00:00:00Z',
          },
        ],
      })

      const result = await getPaymentHistory(workspaceId)

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/workspace-1/payments', {
        params: { limit: 20, offset: 0 },
      })
      expect(Array.isArray(result)).toBe(true)
      expect(result[0].id).toBeDefined()
      expect(result[0].status).toBe('succeeded')
    })

    it('should support pagination', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: [] })

      await getPaymentHistory(workspaceId, 50, 100)

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/workspace-1/payments', {
        params: { limit: 50, offset: 100 },
      })
    })
  })
})
