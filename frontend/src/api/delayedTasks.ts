import { apiClient } from './client'
import type { DelayedTask, CreateDelayedTaskRequest, UpdateDelayedTaskRequest, PaginationMeta } from '@/types'

export interface DelayedTasksResponse {
  tasks: DelayedTask[]
  pagination: PaginationMeta
}

export interface DelayedTaskFilters {
  page?: number
  limit?: number
  status?: string
}

export async function getDelayedTasks(
  workspaceId: string,
  filters?: DelayedTaskFilters
): Promise<DelayedTasksResponse> {
  const params = new URLSearchParams()
  if (filters?.page) params.append('page', filters.page.toString())
  if (filters?.limit) params.append('limit', filters.limit.toString())
  if (filters?.status) params.append('status', filters.status)

  const query = params.toString() ? `?${params.toString()}` : ''
  const response = await apiClient.get<DelayedTasksResponse>(
    `/workspaces/${workspaceId}/delayed${query}`
  )
  return response.data
}

export async function getDelayedTask(
  workspaceId: string,
  taskId: string
): Promise<DelayedTask> {
  const response = await apiClient.get<DelayedTask>(
    `/workspaces/${workspaceId}/delayed/${taskId}`
  )
  return response.data
}

export async function createDelayedTask(
  workspaceId: string,
  data: CreateDelayedTaskRequest
): Promise<DelayedTask> {
  const response = await apiClient.post<DelayedTask>(
    `/workspaces/${workspaceId}/delayed`,
    data
  )
  return response.data
}

export async function updateDelayedTask(
  workspaceId: string,
  taskId: string,
  data: UpdateDelayedTaskRequest
): Promise<DelayedTask> {
  const response = await apiClient.patch<DelayedTask>(
    `/workspaces/${workspaceId}/delayed/${taskId}`,
    data
  )
  return response.data
}

export async function cancelDelayedTask(
  workspaceId: string,
  taskId: string
): Promise<DelayedTask> {
  const response = await apiClient.delete<DelayedTask>(
    `/workspaces/${workspaceId}/delayed/${taskId}`
  )
  return response.data
}
