import { apiClient } from './client'

export interface AdminStats {
  total_users: number
  active_users: number
  verified_users: number
  total_workspaces: number
  total_cron_tasks: number
  active_cron_tasks: number
  total_delayed_tasks: number
  pending_delayed_tasks: number
  total_task_chains: number
  active_task_chains: number
  total_heartbeats: number
  active_heartbeats: number
  total_executions: number
  executions_today: number
  executions_this_week: number
  success_rate: number
  active_subscriptions: number
  revenue_this_month: number
}

export interface AdminUser {
  id: string
  email: string
  name: string
  is_active: boolean
  is_superuser: boolean
  email_verified: boolean
  telegram_username: string | null
  created_at: string
  last_login_at: string | null
  workspaces_count: number
  cron_tasks_count: number
  delayed_tasks_count: number
  task_chains_count: number
  heartbeats_count: number
  plan_name: string
  subscription_ends_at: string | null
  executions_count: number
}

export interface AdminUsersResponse {
  users: AdminUser[]
  total: number
  page: number
  page_size: number
}

export interface AdminWorkspace {
  id: string
  name: string
  slug: string
  owner_email: string
  owner_name: string
  plan_name: string
  cron_tasks_count: number
  delayed_tasks_count: number
  task_chains_count: number
  heartbeats_count: number
  executions_count: number
  created_at: string
}

export interface AdminWorkspacesResponse {
  workspaces: AdminWorkspace[]
  total: number
  page: number
  page_size: number
}

export interface UpdateUserRequest {
  is_active?: boolean
  is_superuser?: boolean
  email_verified?: boolean
}

export async function getAdminStats(): Promise<AdminStats> {
  const response = await apiClient.get<AdminStats>('/admin/stats')
  return response.data
}

export async function getAdminUsers(params?: {
  page?: number
  page_size?: number
  search?: string
}): Promise<AdminUsersResponse> {
  const response = await apiClient.get<AdminUsersResponse>('/admin/users', { params })
  return response.data
}

export async function getAdminUser(userId: string): Promise<AdminUser> {
  const response = await apiClient.get<AdminUser>(`/admin/users/${userId}`)
  return response.data
}

export async function updateAdminUser(userId: string, data: UpdateUserRequest): Promise<void> {
  await apiClient.patch(`/admin/users/${userId}`, data)
}

export interface AssignPlanRequest {
  plan_id: string
  duration_days?: number
}

export async function assignUserPlan(userId: string, data: AssignPlanRequest): Promise<void> {
  await apiClient.post(`/admin/users/${userId}/subscription`, data)
}

export async function getAdminWorkspaces(params?: {
  page?: number
  page_size?: number
  search?: string
}): Promise<AdminWorkspacesResponse> {
  const response = await apiClient.get<AdminWorkspacesResponse>('/admin/workspaces', { params })
  return response.data
}

// Plans

export interface AdminPlan {
  id: string
  name: string
  display_name: string
  description: string | null
  price_monthly: number
  price_yearly: number
  max_cron_tasks: number
  max_delayed_tasks_per_month: number
  max_workspaces: number
  max_execution_history_days: number
  min_cron_interval_minutes: number
  telegram_notifications: boolean
  email_notifications: boolean
  webhook_callbacks: boolean
  custom_headers: boolean
  retry_on_failure: boolean
  // Task Chains limits
  max_task_chains: number
  max_chain_steps: number
  chain_variable_substitution: boolean
  min_chain_interval_minutes: number
  // Heartbeats limits
  max_heartbeats: number
  min_heartbeat_interval_minutes: number
  // SSL Monitors limits
  max_ssl_monitors: number
  // Overlap prevention settings
  overlap_prevention_enabled: boolean
  max_queue_size: number
  is_active: boolean
  is_public: boolean
  sort_order: number
  subscriptions_count: number
  created_at: string
}

export interface AdminPlansResponse {
  plans: AdminPlan[]
  total: number
}

export interface CreatePlanRequest {
  name: string
  display_name: string
  description?: string | null
  price_monthly?: number
  price_yearly?: number
  max_cron_tasks?: number
  max_delayed_tasks_per_month?: number
  max_workspaces?: number
  max_execution_history_days?: number
  min_cron_interval_minutes?: number
  telegram_notifications?: boolean
  email_notifications?: boolean
  webhook_callbacks?: boolean
  custom_headers?: boolean
  retry_on_failure?: boolean
  // Task Chains limits
  max_task_chains?: number
  max_chain_steps?: number
  chain_variable_substitution?: boolean
  min_chain_interval_minutes?: number
  // Heartbeats limits
  max_heartbeats?: number
  min_heartbeat_interval_minutes?: number
  // SSL Monitors limits
  max_ssl_monitors?: number
  // Overlap prevention settings
  overlap_prevention_enabled?: boolean
  max_queue_size?: number
  is_active?: boolean
  is_public?: boolean
  sort_order?: number
}

export interface UpdatePlanRequest {
  display_name?: string
  description?: string | null
  price_monthly?: number
  price_yearly?: number
  max_cron_tasks?: number
  max_delayed_tasks_per_month?: number
  max_workspaces?: number
  max_execution_history_days?: number
  min_cron_interval_minutes?: number
  telegram_notifications?: boolean
  email_notifications?: boolean
  webhook_callbacks?: boolean
  custom_headers?: boolean
  retry_on_failure?: boolean
  // Task Chains limits
  max_task_chains?: number
  max_chain_steps?: number
  chain_variable_substitution?: boolean
  min_chain_interval_minutes?: number
  // Heartbeats limits
  max_heartbeats?: number
  min_heartbeat_interval_minutes?: number
  // SSL Monitors limits
  max_ssl_monitors?: number
  // Overlap prevention settings
  overlap_prevention_enabled?: boolean
  max_queue_size?: number
  is_active?: boolean
  is_public?: boolean
  sort_order?: number
}

export async function getAdminPlans(): Promise<AdminPlansResponse> {
  const response = await apiClient.get<AdminPlansResponse>('/admin/plans')
  return response.data
}

export async function createAdminPlan(data: CreatePlanRequest): Promise<AdminPlan> {
  const response = await apiClient.post<AdminPlan>('/admin/plans', data)
  return response.data
}

export async function updateAdminPlan(planId: string, data: UpdatePlanRequest): Promise<AdminPlan> {
  const response = await apiClient.patch<AdminPlan>(`/admin/plans/${planId}`, data)
  return response.data
}

export async function deleteAdminPlan(planId: string): Promise<void> {
  await apiClient.delete(`/admin/plans/${planId}`)
}

// Notification Templates

export interface NotificationTemplate {
  id: string
  code: string
  language: string
  channel: string
  subject: string | null
  body: string
  description: string | null
  variables: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface NotificationTemplatesResponse {
  templates: NotificationTemplate[]
  total: number
}

export interface UpdateTemplateRequest {
  subject?: string | null
  body?: string
  is_active?: boolean
}

export interface TemplatePreviewRequest {
  body: string
  subject?: string | null
  variables: Record<string, string>
}

export interface TemplatePreviewResponse {
  subject: string | null
  body: string
}

export async function getNotificationTemplates(params?: {
  code?: string
  language?: string
  channel?: string
}): Promise<NotificationTemplatesResponse> {
  const response = await apiClient.get<NotificationTemplatesResponse>('/admin/notification-templates', { params })
  return response.data
}

export async function getNotificationTemplate(templateId: string): Promise<NotificationTemplate> {
  const response = await apiClient.get<NotificationTemplate>(`/admin/notification-templates/${templateId}`)
  return response.data
}

export async function updateNotificationTemplate(
  templateId: string,
  data: UpdateTemplateRequest
): Promise<NotificationTemplate> {
  const response = await apiClient.patch<NotificationTemplate>(`/admin/notification-templates/${templateId}`, data)
  return response.data
}

export async function previewNotificationTemplate(data: TemplatePreviewRequest): Promise<TemplatePreviewResponse> {
  const response = await apiClient.post<TemplatePreviewResponse>('/admin/notification-templates/preview', data)
  return response.data
}

export async function resetNotificationTemplate(templateId: string): Promise<NotificationTemplate> {
  const response = await apiClient.post<NotificationTemplate>(`/admin/notification-templates/reset/${templateId}`)
  return response.data
}
