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
  workspaces_count: number
  tasks_count: number
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
