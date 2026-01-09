import { http, HttpResponse } from 'msw'
import { mockUser, mockWorkspace, mockCronTask, mockDelayedTask, mockExecution, mockPlan, mockSubscription } from './data'

const API_BASE = 'http://localhost:8000/v1'

export const handlers = [
  // Auth endpoints
  http.post(`${API_BASE}/auth/login`, async ({ request }) => {
    const body = await request.json() as { email: string; password: string }
    if (body.email === 'test@example.com' && body.password === 'password123') {
      return HttpResponse.json({
        user: mockUser,
        access_token: 'mock_access_token',
        refresh_token: 'mock_refresh_token',
      })
    }
    return HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 })
  }),

  http.post(`${API_BASE}/auth/register`, async ({ request }) => {
    const body = await request.json() as { email: string; password: string; name: string }
    return HttpResponse.json({
      user: { ...mockUser, email: body.email, name: body.name },
      access_token: 'mock_access_token',
      refresh_token: 'mock_refresh_token',
    })
  }),

  http.get(`${API_BASE}/auth/me`, () => {
    return HttpResponse.json(mockUser)
  }),

  http.post(`${API_BASE}/auth/refresh`, () => {
    return HttpResponse.json({
      access_token: 'new_access_token',
      refresh_token: 'new_refresh_token',
    })
  }),

  http.post(`${API_BASE}/auth/logout`, () => {
    return HttpResponse.json({ success: true })
  }),

  http.patch(`${API_BASE}/auth/profile`, async ({ request }) => {
    const updates = await request.json()
    return HttpResponse.json({ ...mockUser, ...updates })
  }),

  http.post(`${API_BASE}/auth/change-password`, () => {
    return HttpResponse.json({ success: true })
  }),

  // Workspaces
  http.get(`${API_BASE}/workspaces`, () => {
    return HttpResponse.json([mockWorkspace])
  }),

  http.get(`${API_BASE}/workspaces/:id`, () => {
    return HttpResponse.json(mockWorkspace)
  }),

  http.post(`${API_BASE}/workspaces`, async ({ request }) => {
    const body = await request.json() as { name: string; slug?: string }
    return HttpResponse.json({
      ...mockWorkspace,
      id: 'new-workspace-id',
      name: body.name,
      slug: body.slug || body.name.toLowerCase(),
    })
  }),

  http.patch(`${API_BASE}/workspaces/:id`, async ({ request }) => {
    const updates = await request.json()
    return HttpResponse.json({ ...mockWorkspace, ...updates })
  }),

  http.delete(`${API_BASE}/workspaces/:id`, () => {
    return HttpResponse.json({ success: true })
  }),

  // Cron Tasks
  http.get(`${API_BASE}/workspaces/:workspaceId/cron`, ({ request }) => {
    const url = new URL(request.url)
    const page = parseInt(url.searchParams.get('page') || '1')
    const limit = parseInt(url.searchParams.get('limit') || '20')
    return HttpResponse.json({
      tasks: [mockCronTask],
      pagination: { page, limit, total: 1, total_pages: 1 },
    })
  }),

  http.get(`${API_BASE}/workspaces/:workspaceId/cron/:id`, () => {
    return HttpResponse.json(mockCronTask)
  }),

  http.post(`${API_BASE}/workspaces/:workspaceId/cron`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ ...mockCronTask, ...body, id: 'new-task-id' })
  }),

  http.patch(`${API_BASE}/workspaces/:workspaceId/cron/:id`, async ({ request }) => {
    const updates = await request.json()
    return HttpResponse.json({ ...mockCronTask, ...updates })
  }),

  http.delete(`${API_BASE}/workspaces/:workspaceId/cron/:id`, () => {
    return HttpResponse.json({ success: true })
  }),

  http.post(`${API_BASE}/workspaces/:workspaceId/cron/:id/run`, () => {
    return HttpResponse.json({ success: true, execution_id: 'exec-123' })
  }),

  http.post(`${API_BASE}/workspaces/:workspaceId/cron/:id/pause`, () => {
    return HttpResponse.json({ ...mockCronTask, is_active: false })
  }),

  http.post(`${API_BASE}/workspaces/:workspaceId/cron/:id/resume`, () => {
    return HttpResponse.json({ ...mockCronTask, is_active: true })
  }),

  // Delayed Tasks
  http.get(`${API_BASE}/workspaces/:workspaceId/delayed`, ({ request }) => {
    const url = new URL(request.url)
    const page = parseInt(url.searchParams.get('page') || '1')
    const limit = parseInt(url.searchParams.get('limit') || '20')
    return HttpResponse.json({
      tasks: [mockDelayedTask],
      pagination: { page, limit, total: 1, total_pages: 1 },
    })
  }),

  http.get(`${API_BASE}/workspaces/:workspaceId/delayed/:id`, () => {
    return HttpResponse.json(mockDelayedTask)
  }),

  http.post(`${API_BASE}/workspaces/:workspaceId/delayed`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ ...mockDelayedTask, ...body, id: 'new-delayed-id' })
  }),

  http.patch(`${API_BASE}/workspaces/:workspaceId/delayed/:id`, async ({ request }) => {
    const updates = await request.json()
    return HttpResponse.json({ ...mockDelayedTask, ...updates })
  }),

  http.post(`${API_BASE}/workspaces/:workspaceId/delayed/:id/cancel`, () => {
    return HttpResponse.json({ ...mockDelayedTask, status: 'cancelled' })
  }),

  // Executions
  http.get(`${API_BASE}/workspaces/:workspaceId/executions`, ({ request }) => {
    const url = new URL(request.url)
    const page = parseInt(url.searchParams.get('page') || '1')
    const limit = parseInt(url.searchParams.get('limit') || '20')
    return HttpResponse.json({
      executions: [mockExecution],
      pagination: { page, limit, total: 1, total_pages: 1 },
    })
  }),

  http.get(`${API_BASE}/workspaces/:workspaceId/executions/:id`, () => {
    return HttpResponse.json(mockExecution)
  }),

  http.get(`${API_BASE}/workspaces/:workspaceId/executions/stats`, () => {
    return HttpResponse.json({
      total: 100,
      successful: 95,
      failed: 5,
      by_day: [],
    })
  }),

  // Notifications
  http.get(`${API_BASE}/workspaces/:workspaceId/notifications/settings`, () => {
    return HttpResponse.json({
      email_enabled: true,
      telegram_enabled: false,
      webhook_enabled: false,
      notify_on_failure: true,
      notify_on_success: false,
    })
  }),

  http.patch(`${API_BASE}/workspaces/:workspaceId/notifications/settings`, async ({ request }) => {
    const updates = await request.json()
    return HttpResponse.json({
      email_enabled: true,
      telegram_enabled: false,
      webhook_enabled: false,
      notify_on_failure: true,
      notify_on_success: false,
      ...updates,
    })
  }),

  http.post(`${API_BASE}/workspaces/:workspaceId/notifications/test`, () => {
    return HttpResponse.json({ success: true })
  }),

  // Billing
  http.get(`${API_BASE}/billing/plans`, () => {
    return HttpResponse.json([mockPlan])
  }),

  http.get(`${API_BASE}/workspaces/:workspaceId/billing/subscription`, () => {
    return HttpResponse.json(mockSubscription)
  }),

  http.post(`${API_BASE}/workspaces/:workspaceId/billing/payment`, () => {
    return HttpResponse.json({
      payment_url: 'https://yookassa.ru/checkout/123',
      payment_id: 'payment-123',
    })
  }),

  http.post(`${API_BASE}/workspaces/:workspaceId/billing/cancel`, () => {
    return HttpResponse.json({ success: true })
  }),

  http.get(`${API_BASE}/workspaces/:workspaceId/billing/payments`, () => {
    return HttpResponse.json([])
  }),

  // Workers
  http.get(`${API_BASE}/workspaces/:workspaceId/workers`, () => {
    return HttpResponse.json([])
  }),

  http.post(`${API_BASE}/workspaces/:workspaceId/workers`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ id: 'worker-1', ...body, api_key: 'key-123' })
  }),

  // Admin endpoints
  http.get(`${API_BASE}/admin/stats`, () => {
    return HttpResponse.json({
      total_users: 100,
      total_workspaces: 50,
      total_tasks: 500,
      total_executions: 10000,
    })
  }),

  http.get(`${API_BASE}/admin/users`, () => {
    return HttpResponse.json({
      users: [mockUser],
      pagination: { page: 1, limit: 20, total: 1, total_pages: 1 },
    })
  }),

  http.get(`${API_BASE}/admin/workspaces`, () => {
    return HttpResponse.json({
      workspaces: [mockWorkspace],
      pagination: { page: 1, limit: 20, total: 1, total_pages: 1 },
    })
  }),

  http.get(`${API_BASE}/admin/plans`, () => {
    return HttpResponse.json([mockPlan])
  }),
]
