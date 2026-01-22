import { apiClient } from './client'
import type { Execution, ExecutionDetail, ExecutionStats, ExecutionTaskType, PaginationMeta } from '@/types'

export interface ExecutionsResponse {
  executions: Execution[]
  pagination: PaginationMeta
}

export interface ExecutionFilters {
  page?: number
  limit?: number
  task_type?: ExecutionTaskType
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
  executionId: string,
  executionType?: ExecutionTaskType
): Promise<ExecutionDetail> {
  const params = executionType ? `?execution_type=${executionType}` : ''
  const response = await apiClient.get<ExecutionDetail>(
    `/workspaces/${workspaceId}/executions/${executionId}${params}`
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

export interface DailyStats {
  date: string
  success: number
  failed: number
  total: number
}

export interface DailyStatsResponse {
  stats: DailyStats[]
}

export async function getDailyExecutionStats(
  workspaceId: string,
  days: number = 7
): Promise<DailyStats[]> {
  const response = await apiClient.get<DailyStatsResponse>(
    `/workspaces/${workspaceId}/executions/stats/daily?days=${days}`
  )
  return response.data.stats
}

export async function getLatestExecution(
  workspaceId: string,
  taskId: string,
  taskType?: ExecutionTaskType
): Promise<ExecutionDetail | null> {
  const filters: ExecutionFilters = {
    task_id: taskId,
    limit: 1,
    page: 1,
  }
  if (taskType) {
    filters.task_type = taskType
  }
  const response = await getExecutions(workspaceId, filters)
  if (response.executions.length === 0) {
    return null
  }
  const execution = response.executions[0]
  return await getExecution(workspaceId, execution.id, taskType)
}
