import { apiClient } from './client'
import type { Execution, ExecutionDetail, ExecutionStats, PaginationMeta } from '@/types'

export interface ExecutionsResponse {
  executions: Execution[]
  pagination: PaginationMeta
}

export interface ExecutionFilters {
  page?: number
  limit?: number
  task_type?: 'cron' | 'delayed'
  status?: string
  task_id?: string
}

export async function getExecutions(
  workspaceId: string,
  filters?: ExecutionFilters
): Promise<ExecutionsResponse> {
  const params = new URLSearchParams()
  if (filters?.page) params.append('page', filters.page.toString())
  if (filters?.limit) params.append('limit', filters.limit.toString())
  if (filters?.task_type) params.append('task_type', filters.task_type)
  if (filters?.status) params.append('status', filters.status)
  if (filters?.task_id) params.append('task_id', filters.task_id)

  const query = params.toString() ? `?${params.toString()}` : ''
  const response = await apiClient.get<ExecutionsResponse>(
    `/workspaces/${workspaceId}/executions${query}`
  )
  return response.data
}

export async function getExecution(
  workspaceId: string,
  executionId: string
): Promise<ExecutionDetail> {
  const response = await apiClient.get<ExecutionDetail>(
    `/workspaces/${workspaceId}/executions/${executionId}`
  )
  return response.data
}

export async function getExecutionStats(
  workspaceId: string,
  days?: number
): Promise<ExecutionStats> {
  const params = days ? `?days=${days}` : ''
  const response = await apiClient.get<ExecutionStats>(
    `/workspaces/${workspaceId}/executions/stats${params}`
  )
  return response.data
}
