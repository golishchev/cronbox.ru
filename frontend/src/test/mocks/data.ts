import type { User, Workspace, CronTask, DelayedTask, Execution } from '@/types'

export const mockUser: User = {
  id: 'user-1',
  email: 'test@example.com',
  name: 'Test User',
  telegram_id: null,
  telegram_username: null,
  email_verified: true,
  is_active: true,
  is_superuser: false,
  preferred_language: 'en',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockAdminUser: User = {
  ...mockUser,
  id: 'admin-1',
  email: 'admin@example.com',
  name: 'Admin User',
  is_superuser: true,
}

export const mockWorkspace: Workspace = {
  id: 'workspace-1',
  name: 'Test Workspace',
  slug: 'test-workspace',
  owner_id: 'user-1',
  plan_id: 'plan-1',
  cron_tasks_count: 5,
  delayed_tasks_this_month: 100,
  default_timezone: 'UTC',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockCronTask: CronTask = {
  id: 'cron-task-1',
  workspace_id: 'workspace-1',
  name: 'Test Cron Task',
  description: 'A test cron task',
  url: 'https://api.example.com/webhook',
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: '{"test": true}',
  schedule: '*/5 * * * *',
  timezone: 'UTC',
  timeout_seconds: 30,
  retry_count: 3,
  retry_delay_seconds: 60,
  is_active: true,
  is_paused: false,
  last_run_at: '2024-01-01T00:00:00Z',
  last_status: 'success',
  next_run_at: '2024-01-01T00:05:00Z',
  consecutive_failures: 0,
  notify_on_failure: true,
  notify_on_recovery: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockDelayedTask: DelayedTask = {
  id: 'delayed-task-1',
  workspace_id: 'workspace-1',
  idempotency_key: null,
  name: 'Test Delayed Task',
  tags: ['test', 'sample'],
  url: 'https://api.example.com/webhook',
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: '{"test": true}',
  execute_at: '2024-01-02T00:00:00Z',
  timeout_seconds: 30,
  retry_count: 3,
  retry_delay_seconds: 60,
  status: 'pending',
  executed_at: null,
  retry_attempt: 0,
  callback_url: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockExecution: Execution = {
  id: 'execution-1',
  workspace_id: 'workspace-1',
  task_type: 'cron',
  task_id: 'cron-task-1',
  task_name: 'Test Cron Task',
  status: 'success',
  started_at: '2024-01-01T00:00:00Z',
  finished_at: '2024-01-01T00:00:01Z',
  duration_ms: 150,
  retry_attempt: 0,
  request_url: 'https://api.example.com/webhook',
  request_method: 'POST',
  response_status_code: 200,
  error_message: null,
  error_type: null,
  created_at: '2024-01-01T00:00:00Z',
}

export const mockPlan = {
  id: 'plan-1',
  name: 'Pro',
  slug: 'pro',
  price_monthly: 990,
  price_yearly: 9900,
  max_cron_tasks: 100,
  max_delayed_tasks: 1000,
  max_executions_per_month: 100000,
  features: ['Priority support', 'API access'],
  is_active: true,
}

export const mockSubscription = {
  id: 'subscription-1',
  workspace_id: 'workspace-1',
  plan_id: 'plan-1',
  plan: mockPlan,
  status: 'active',
  billing_period: 'monthly',
  current_period_start: '2024-01-01T00:00:00Z',
  current_period_end: '2024-02-01T00:00:00Z',
  created_at: '2024-01-01T00:00:00Z',
}

// Factory functions for creating test data with overrides
export function createMockUser(overrides: Partial<User> = {}): User {
  return { ...mockUser, ...overrides }
}

export function createMockWorkspace(overrides: Partial<Workspace> = {}): Workspace {
  return { ...mockWorkspace, ...overrides }
}

export function createMockCronTask(overrides: Partial<CronTask> = {}): CronTask {
  return { ...mockCronTask, ...overrides }
}

export function createMockDelayedTask(overrides: Partial<DelayedTask> = {}): DelayedTask {
  return { ...mockDelayedTask, ...overrides }
}

export function createMockExecution(overrides: Partial<Execution> = {}): Execution {
  return { ...mockExecution, ...overrides }
}
