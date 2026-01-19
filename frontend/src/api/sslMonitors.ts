import { apiClient } from './client'
import type {
  SSLMonitor,
  CreateSSLMonitorRequest,
  UpdateSSLMonitorRequest,
  PaginationMeta,
} from '@/types'

interface SSLMonitorListResponse {
  monitors: SSLMonitor[]
  pagination: PaginationMeta
}

export async function getSSLMonitors(
  workspaceId: string,
  page: number = 1,
  limit: number = 20
): Promise<SSLMonitorListResponse> {
  const response = await apiClient.get<SSLMonitorListResponse>(
    `/workspaces/${workspaceId}/ssl-monitors`,
    { params: { page, limit } }
  )
  return response.data
}

export async function getSSLMonitor(workspaceId: string, monitorId: string): Promise<SSLMonitor> {
  const response = await apiClient.get<SSLMonitor>(
    `/workspaces/${workspaceId}/ssl-monitors/${monitorId}`
  )
  return response.data
}

export async function createSSLMonitor(
  workspaceId: string,
  data: CreateSSLMonitorRequest
): Promise<SSLMonitor> {
  const response = await apiClient.post<SSLMonitor>(
    `/workspaces/${workspaceId}/ssl-monitors`,
    data
  )
  return response.data
}

export async function updateSSLMonitor(
  workspaceId: string,
  monitorId: string,
  data: UpdateSSLMonitorRequest
): Promise<SSLMonitor> {
  const response = await apiClient.patch<SSLMonitor>(
    `/workspaces/${workspaceId}/ssl-monitors/${monitorId}`,
    data
  )
  return response.data
}

export async function deleteSSLMonitor(workspaceId: string, monitorId: string): Promise<void> {
  await apiClient.delete(`/workspaces/${workspaceId}/ssl-monitors/${monitorId}`)
}

export async function pauseSSLMonitor(workspaceId: string, monitorId: string): Promise<SSLMonitor> {
  const response = await apiClient.post<SSLMonitor>(
    `/workspaces/${workspaceId}/ssl-monitors/${monitorId}/pause`
  )
  return response.data
}

export async function resumeSSLMonitor(workspaceId: string, monitorId: string): Promise<SSLMonitor> {
  const response = await apiClient.post<SSLMonitor>(
    `/workspaces/${workspaceId}/ssl-monitors/${monitorId}/resume`
  )
  return response.data
}

export async function checkSSLMonitor(workspaceId: string, monitorId: string): Promise<SSLMonitor> {
  const response = await apiClient.post<SSLMonitor>(
    `/workspaces/${workspaceId}/ssl-monitors/${monitorId}/check`
  )
  return response.data
}
