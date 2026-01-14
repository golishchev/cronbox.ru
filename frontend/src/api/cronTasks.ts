import { apiClient } from './client'
import type {
  CronTask,
  CreateCronTaskRequest,
  UpdateCronTaskRequest,
  PaginationMeta,
} from '@/types'

interface CronTasksResponse {
  tasks: CronTask[]
  pagination: PaginationMeta
}

export async function getCronTasks(
  workspaceId: string,
  page = 1,
  limit = 20,
  isActive?: boolean
): Promise<CronTasksResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
  })
  if (isActive !== undefined) {
    params.set('is_active', isActive.toString())
  }
  const response = await apiClient.get<CronTasksResponse>(
    `/workspaces/${workspaceId}/cron?${params}`
  )
  return response.data
}

export async function getCronTask(workspaceId: string, taskId: string): Promise<CronTask> {
  const response = await apiClient.get<CronTask>(
    `/workspaces/${workspaceId}/cron/${taskId}`
  )
  return response.data
}

export async function createCronTask(
  workspaceId: string,
  data: CreateCronTaskRequest
): Promise<CronTask> {
  const response = await apiClient.post<CronTask>(
    `/workspaces/${workspaceId}/cron`,
    data
  )
  return response.data
}

export async function updateCronTask(
  workspaceId: string,
  taskId: string,
  data: UpdateCronTaskRequest
): Promise<CronTask> {
  const response = await apiClient.patch<CronTask>(
    `/workspaces/${workspaceId}/cron/${taskId}`,
    data
  )
  return response.data
}

export async function deleteCronTask(workspaceId: string, taskId: string): Promise<void> {
  await apiClient.delete(`/workspaces/${workspaceId}/cron/${taskId}`)
}

export async function runCronTask(
  workspaceId: string,
  taskId: string
): Promise<{ message: string; task_id: string }> {
  const response = await apiClient.post<{ message: string; task_id: string }>(
    `/workspaces/${workspaceId}/cron/${taskId}/run`
  )
  return response.data
}

export async function pauseCronTask(workspaceId: string, taskId: string): Promise<CronTask> {
  const response = await apiClient.post<CronTask>(
    `/workspaces/${workspaceId}/cron/${taskId}/pause`
  )
  return response.data
}

export async function resumeCronTask(workspaceId: string, taskId: string): Promise<CronTask> {
  const response = await apiClient.post<CronTask>(
    `/workspaces/${workspaceId}/cron/${taskId}/resume`
  )
  return response.data
}

export async function copyCronTask(workspaceId: string, taskId: string): Promise<CronTask> {
  const response = await apiClient.post<CronTask>(
    `/workspaces/${workspaceId}/cron/${taskId}/copy`
  )
  return response.data
}
