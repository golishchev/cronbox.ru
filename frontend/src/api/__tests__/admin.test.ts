import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  getAdminStats,
  getAdminUsers,
  getAdminUser,
  updateAdminUser,
  deleteAdminUser,
  getAdminWorkspaces,
  getAdminPlans,
  createAdminPlan,
  updateAdminPlan,
  deleteAdminPlan,
  getNotificationTemplates,
  getNotificationTemplate,
  updateNotificationTemplate,
  previewNotificationTemplate,
  resetNotificationTemplate,
} from '../admin'
import { apiClient } from '../client'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('admin API', () => {
  const mockStats = {
    total_users: 100,
    active_users: 80,
    verified_users: 75,
    total_workspaces: 50,
    total_cron_tasks: 500,
    active_cron_tasks: 400,
    total_delayed_tasks: 1000,
    pending_delayed_tasks: 100,
    total_executions: 100000,
    executions_today: 1000,
    executions_this_week: 7000,
    success_rate: 0.95,
    active_subscriptions: 30,
    revenue_this_month: 29700,
  }

  const mockAdminUser = {
    id: 'user-1',
    email: 'test@example.com',
    name: 'Test User',
    is_active: true,
    is_superuser: false,
    email_verified: true,
    telegram_username: null,
    created_at: '2024-01-01T00:00:00Z',
    workspaces_count: 2,
    tasks_count: 10,
  }

  const mockPlan = {
    id: 'plan-1',
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
    is_active: true,
    is_public: true,
    sort_order: 2,
    subscriptions_count: 50,
    created_at: '2024-01-01T00:00:00Z',
  }

  const mockTemplate = {
    id: 'template-1',
    code: 'task_failure',
    language: 'en',
    channel: 'email',
    subject: 'Task Failed: {{task_name}}',
    body: 'Your task {{task_name}} has failed.',
    description: 'Sent when a task fails',
    variables: ['task_name', 'error_message'],
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getAdminStats', () => {
    it('should return admin statistics', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockStats })

      const result = await getAdminStats()

      expect(apiClient.get).toHaveBeenCalledWith('/admin/stats')
      expect(result.total_users).toBe(100)
      expect(result.success_rate).toBe(0.95)
      expect(result.revenue_this_month).toBeDefined()
    })
  })

  describe('getAdminUsers', () => {
    it('should return paginated users list', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: {
          users: [mockAdminUser],
          total: 100,
          page: 1,
          page_size: 20,
        },
      })

      const result = await getAdminUsers()

      expect(apiClient.get).toHaveBeenCalledWith('/admin/users', { params: undefined })
      expect(result.users).toBeDefined()
      expect(result.total).toBe(100)
    })

    it('should support search parameter', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: {
          users: [mockAdminUser],
          total: 1,
          page: 1,
          page_size: 20,
        },
      })

      await getAdminUsers({ search: 'test' })

      expect(apiClient.get).toHaveBeenCalledWith('/admin/users', { params: { search: 'test' } })
    })
  })

  describe('getAdminUser', () => {
    it('should return user details', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockAdminUser })

      const result = await getAdminUser('user-1')

      expect(apiClient.get).toHaveBeenCalledWith('/admin/users/user-1')
      expect(result.id).toBe('user-1')
      expect(result.email).toBeDefined()
    })
  })

  describe('updateAdminUser', () => {
    it('should update user status', async () => {
      vi.mocked(apiClient.patch).mockResolvedValue({ data: { success: true } })

      await expect(updateAdminUser('user-1', { is_active: false })).resolves.not.toThrow()

      expect(apiClient.patch).toHaveBeenCalledWith('/admin/users/user-1', { is_active: false })
    })

    it('should update superuser status', async () => {
      vi.mocked(apiClient.patch).mockResolvedValue({ data: { success: true } })

      await expect(updateAdminUser('user-1', { is_superuser: true })).resolves.not.toThrow()

      expect(apiClient.patch).toHaveBeenCalledWith('/admin/users/user-1', { is_superuser: true })
    })
  })

  describe('deleteAdminUser', () => {
    it('should delete user', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({ data: {} })

      await expect(deleteAdminUser('user-1')).resolves.not.toThrow()

      expect(apiClient.delete).toHaveBeenCalledWith('/admin/users/user-1')
    })
  })

  describe('getAdminWorkspaces', () => {
    it('should return paginated workspaces list', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: {
          workspaces: [
            {
              id: 'ws-1',
              name: 'Test Workspace',
              slug: 'test',
              owner_email: 'owner@example.com',
              owner_name: 'Owner',
              plan_name: 'Pro',
              cron_tasks_count: 10,
              delayed_tasks_count: 50,
              executions_count: 1000,
              created_at: '2024-01-01T00:00:00Z',
            },
          ],
          total: 50,
          page: 1,
          page_size: 20,
        },
      })

      const result = await getAdminWorkspaces()

      expect(apiClient.get).toHaveBeenCalledWith('/admin/workspaces', { params: undefined })
      expect(result.workspaces).toBeDefined()
      expect(result.total).toBe(50)
    })
  })

  describe('getAdminPlans', () => {
    it('should return plans list', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: {
          plans: [mockPlan],
          total: 3,
        },
      })

      const result = await getAdminPlans()

      expect(apiClient.get).toHaveBeenCalledWith('/admin/plans')
      expect(result.plans).toBeDefined()
      expect(result.plans[0].name).toBe('pro')
    })
  })

  describe('createAdminPlan', () => {
    it('should create new plan', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: {
          ...mockPlan,
          id: 'new-plan',
          name: 'enterprise',
          display_name: 'Enterprise',
        },
      })

      const result = await createAdminPlan({
        name: 'enterprise',
        display_name: 'Enterprise',
        price_monthly: 9990,
      })

      expect(apiClient.post).toHaveBeenCalledWith('/admin/plans', {
        name: 'enterprise',
        display_name: 'Enterprise',
        price_monthly: 9990,
      })
      expect(result.id).toBeDefined()
      expect(result.name).toBe('enterprise')
    })
  })

  describe('updateAdminPlan', () => {
    it('should update plan', async () => {
      vi.mocked(apiClient.patch).mockResolvedValue({
        data: { ...mockPlan, price_monthly: 1990 },
      })

      const result = await updateAdminPlan('plan-1', { price_monthly: 1990 })

      expect(apiClient.patch).toHaveBeenCalledWith('/admin/plans/plan-1', { price_monthly: 1990 })
      expect(result.price_monthly).toBe(1990)
    })
  })

  describe('deleteAdminPlan', () => {
    it('should delete plan', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({ data: {} })

      await expect(deleteAdminPlan('plan-1')).resolves.not.toThrow()
      expect(apiClient.delete).toHaveBeenCalledWith('/admin/plans/plan-1')
    })
  })

  describe('getNotificationTemplates', () => {
    it('should return templates list', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: {
          templates: [mockTemplate],
          total: 10,
        },
      })

      const result = await getNotificationTemplates()

      expect(apiClient.get).toHaveBeenCalledWith('/admin/notification-templates', { params: undefined })
      expect(result.templates).toBeDefined()
      expect(result.templates[0].code).toBe('task_failure')
    })

    it('should filter by channel', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { templates: [], total: 0 },
      })

      await getNotificationTemplates({ channel: 'telegram' })

      expect(apiClient.get).toHaveBeenCalledWith('/admin/notification-templates', {
        params: { channel: 'telegram' },
      })
    })
  })

  describe('getNotificationTemplate', () => {
    it('should return template details', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockTemplate })

      const result = await getNotificationTemplate('template-1')

      expect(apiClient.get).toHaveBeenCalledWith('/admin/notification-templates/template-1')
      expect(result.id).toBe('template-1')
      expect(result.variables).toBeDefined()
    })
  })

  describe('updateNotificationTemplate', () => {
    it('should update template', async () => {
      vi.mocked(apiClient.patch).mockResolvedValue({
        data: { ...mockTemplate, body: 'Updated body' },
      })

      const result = await updateNotificationTemplate('template-1', {
        body: 'Updated body',
      })

      expect(apiClient.patch).toHaveBeenCalledWith('/admin/notification-templates/template-1', {
        body: 'Updated body',
      })
      expect(result.body).toBe('Updated body')
    })
  })

  describe('previewNotificationTemplate', () => {
    it('should return preview', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: {
          subject: 'Task Failed: My Task',
          body: 'Task My Task failed',
        },
      })

      const result = await previewNotificationTemplate({
        body: 'Task {{task_name}} failed',
        variables: { task_name: 'My Task' },
      })

      expect(apiClient.post).toHaveBeenCalledWith('/admin/notification-templates/preview', {
        body: 'Task {{task_name}} failed',
        variables: { task_name: 'My Task' },
      })
      expect(result.body).toContain('My Task')
    })
  })

  describe('resetNotificationTemplate', () => {
    it('should reset template to default', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockTemplate })

      const result = await resetNotificationTemplate('template-1')

      expect(apiClient.post).toHaveBeenCalledWith('/admin/notification-templates/reset/template-1')
      expect(result.id).toBe('template-1')
    })
  })
})
