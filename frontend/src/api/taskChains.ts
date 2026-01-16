import { apiClient } from './client'
import type {
  TaskChain,
  TaskChainDetail,
  TaskChainsResponse,
  CreateTaskChainRequest,
  UpdateTaskChainRequest,
  ChainStep,
  CreateChainStepRequest,
  UpdateChainStepRequest,
  ChainExecutionDetail,
  ChainExecutionsResponse,
  ChainRunRequest,
  StepReorderRequest,
} from '@/types/chains'

// ============================================================================
// Task Chain API
// ============================================================================

export async function getTaskChains(
  workspaceId: string,
  page = 1,
  limit = 20,
  isActive?: boolean
): Promise<TaskChainsResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
  })
  if (isActive !== undefined) {
    params.set('is_active', isActive.toString())
  }
  const response = await apiClient.get<TaskChainsResponse>(
    `/workspaces/${workspaceId}/chains?${params}`
  )
  return response.data
}

export async function getTaskChain(
  workspaceId: string,
  chainId: string
): Promise<TaskChainDetail> {
  const response = await apiClient.get<TaskChainDetail>(
    `/workspaces/${workspaceId}/chains/${chainId}`
  )
  return response.data
}

export async function createTaskChain(
  workspaceId: string,
  data: CreateTaskChainRequest
): Promise<TaskChainDetail> {
  const response = await apiClient.post<TaskChainDetail>(
    `/workspaces/${workspaceId}/chains`,
    data
  )
  return response.data
}

export async function updateTaskChain(
  workspaceId: string,
  chainId: string,
  data: UpdateTaskChainRequest
): Promise<TaskChain> {
  const response = await apiClient.patch<TaskChain>(
    `/workspaces/${workspaceId}/chains/${chainId}`,
    data
  )
  return response.data
}

export async function deleteTaskChain(
  workspaceId: string,
  chainId: string
): Promise<void> {
  await apiClient.delete(`/workspaces/${workspaceId}/chains/${chainId}`)
}

export async function runTaskChain(
  workspaceId: string,
  chainId: string,
  data?: ChainRunRequest
): Promise<{ message: string; chain_id: string }> {
  const response = await apiClient.post<{ message: string; chain_id: string }>(
    `/workspaces/${workspaceId}/chains/${chainId}/run`,
    data || {}
  )
  return response.data
}

export async function pauseTaskChain(
  workspaceId: string,
  chainId: string
): Promise<TaskChain> {
  const response = await apiClient.post<TaskChain>(
    `/workspaces/${workspaceId}/chains/${chainId}/pause`
  )
  return response.data
}

export async function resumeTaskChain(
  workspaceId: string,
  chainId: string
): Promise<TaskChain> {
  const response = await apiClient.post<TaskChain>(
    `/workspaces/${workspaceId}/chains/${chainId}/resume`
  )
  return response.data
}

export async function copyTaskChain(
  workspaceId: string,
  chainId: string
): Promise<TaskChainDetail> {
  const response = await apiClient.post<TaskChainDetail>(
    `/workspaces/${workspaceId}/chains/${chainId}/copy`
  )
  return response.data
}

// ============================================================================
// Chain Step API
// ============================================================================

export async function getChainSteps(
  workspaceId: string,
  chainId: string
): Promise<ChainStep[]> {
  const response = await apiClient.get<ChainStep[]>(
    `/workspaces/${workspaceId}/chains/${chainId}/steps`
  )
  return response.data
}

export async function createChainStep(
  workspaceId: string,
  chainId: string,
  data: CreateChainStepRequest
): Promise<ChainStep> {
  const response = await apiClient.post<ChainStep>(
    `/workspaces/${workspaceId}/chains/${chainId}/steps`,
    data
  )
  return response.data
}

export async function updateChainStep(
  workspaceId: string,
  chainId: string,
  stepId: string,
  data: UpdateChainStepRequest
): Promise<ChainStep> {
  const response = await apiClient.patch<ChainStep>(
    `/workspaces/${workspaceId}/chains/${chainId}/steps/${stepId}`,
    data
  )
  return response.data
}

export async function deleteChainStep(
  workspaceId: string,
  chainId: string,
  stepId: string
): Promise<void> {
  await apiClient.delete(`/workspaces/${workspaceId}/chains/${chainId}/steps/${stepId}`)
}

export async function reorderChainSteps(
  workspaceId: string,
  chainId: string,
  data: StepReorderRequest
): Promise<ChainStep[]> {
  const response = await apiClient.put<ChainStep[]>(
    `/workspaces/${workspaceId}/chains/${chainId}/steps/reorder`,
    data
  )
  return response.data
}

// ============================================================================
// Chain Execution API
// ============================================================================

export async function getChainExecutions(
  workspaceId: string,
  chainId: string,
  page = 1,
  limit = 20
): Promise<ChainExecutionsResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
  })
  const response = await apiClient.get<ChainExecutionsResponse>(
    `/workspaces/${workspaceId}/chains/${chainId}/executions?${params}`
  )
  return response.data
}

export async function getChainExecution(
  workspaceId: string,
  chainId: string,
  executionId: string
): Promise<ChainExecutionDetail> {
  const response = await apiClient.get<ChainExecutionDetail>(
    `/workspaces/${workspaceId}/chains/${chainId}/executions/${executionId}`
  )
  return response.data
}
