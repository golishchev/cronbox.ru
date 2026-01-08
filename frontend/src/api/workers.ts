import { apiClient } from './client'
import type { Worker, WorkerCreateRequest, WorkerCreateResponse, WorkerUpdateRequest } from '@/types'

export async function getWorkers(workspaceId: string): Promise<Worker[]> {
  const response = await apiClient.get<Worker[]>(`/workspaces/${workspaceId}/workers`)
  return response.data
}

export async function getWorker(workspaceId: string, workerId: string): Promise<Worker> {
  const response = await apiClient.get<Worker>(`/workspaces/${workspaceId}/workers/${workerId}`)
  return response.data
}

export async function createWorker(workspaceId: string, data: WorkerCreateRequest): Promise<WorkerCreateResponse> {
  const response = await apiClient.post<WorkerCreateResponse>(`/workspaces/${workspaceId}/workers`, data)
  return response.data
}

export async function updateWorker(workspaceId: string, workerId: string, data: WorkerUpdateRequest): Promise<Worker> {
  const response = await apiClient.patch<Worker>(`/workspaces/${workspaceId}/workers/${workerId}`, data)
  return response.data
}

export async function deleteWorker(workspaceId: string, workerId: string): Promise<void> {
  await apiClient.delete(`/workspaces/${workspaceId}/workers/${workerId}`)
}

export async function regenerateWorkerKey(workspaceId: string, workerId: string): Promise<WorkerCreateResponse> {
  const response = await apiClient.post<WorkerCreateResponse>(`/workspaces/${workspaceId}/workers/${workerId}/regenerate-key`)
  return response.data
}
