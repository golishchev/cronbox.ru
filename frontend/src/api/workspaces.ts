import { apiClient } from './client'
import type { CreateWorkspaceRequest, Workspace, WorkspaceWithStats } from '@/types'

export async function getWorkspaces(): Promise<Workspace[]> {
  const response = await apiClient.get<Workspace[]>('/workspaces')
  return response.data
}

export async function getWorkspace(workspaceId: string): Promise<WorkspaceWithStats> {
  const response = await apiClient.get<WorkspaceWithStats>(`/workspaces/${workspaceId}`)
  return response.data
}

export async function createWorkspace(data: CreateWorkspaceRequest): Promise<Workspace> {
  const response = await apiClient.post<Workspace>('/workspaces', data)
  return response.data
}

export async function updateWorkspace(
  workspaceId: string,
  data: Partial<CreateWorkspaceRequest>
): Promise<Workspace> {
  const response = await apiClient.patch<Workspace>(`/workspaces/${workspaceId}`, data)
  return response.data
}

export async function deleteWorkspace(workspaceId: string): Promise<void> {
  await apiClient.delete(`/workspaces/${workspaceId}`)
}
