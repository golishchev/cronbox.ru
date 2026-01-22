import { apiClient } from './client'
import type {
  ProcessMonitor,
  CreateProcessMonitorRequest,
  UpdateProcessMonitorRequest,
  ProcessMonitorEvent,
  PaginationMeta,
} from '@/types'

interface ProcessMonitorsResponse {
  process_monitors: ProcessMonitor[]
  pagination: PaginationMeta
}

interface ProcessMonitorEventsResponse {
  events: ProcessMonitorEvent[]
  pagination: PaginationMeta
}

export async function getProcessMonitors(
  workspaceId: string,
  page = 1,
  limit = 20
): Promise<ProcessMonitorsResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
  })
  const response = await apiClient.get<ProcessMonitorsResponse>(
    `/workspaces/${workspaceId}/process-monitors?${params}`
  )
  return response.data
}

export async function getProcessMonitor(
  workspaceId: string,
  monitorId: string
): Promise<ProcessMonitor> {
  const response = await apiClient.get<ProcessMonitor>(
    `/workspaces/${workspaceId}/process-monitors/${monitorId}`
  )
  return response.data
}

export async function createProcessMonitor(
  workspaceId: string,
  data: CreateProcessMonitorRequest
): Promise<ProcessMonitor> {
  const response = await apiClient.post<ProcessMonitor>(
    `/workspaces/${workspaceId}/process-monitors`,
    data
  )
  return response.data
}

export async function updateProcessMonitor(
  workspaceId: string,
  monitorId: string,
  data: UpdateProcessMonitorRequest
): Promise<ProcessMonitor> {
  const response = await apiClient.patch<ProcessMonitor>(
    `/workspaces/${workspaceId}/process-monitors/${monitorId}`,
    data
  )
  return response.data
}

export async function deleteProcessMonitor(
  workspaceId: string,
  monitorId: string
): Promise<void> {
  await apiClient.delete(`/workspaces/${workspaceId}/process-monitors/${monitorId}`)
}

export async function pauseProcessMonitor(
  workspaceId: string,
  monitorId: string
): Promise<ProcessMonitor> {
  const response = await apiClient.post<ProcessMonitor>(
    `/workspaces/${workspaceId}/process-monitors/${monitorId}/pause`
  )
  return response.data
}

export async function resumeProcessMonitor(
  workspaceId: string,
  monitorId: string
): Promise<ProcessMonitor> {
  const response = await apiClient.post<ProcessMonitor>(
    `/workspaces/${workspaceId}/process-monitors/${monitorId}/resume`
  )
  return response.data
}

export async function getProcessMonitorEvents(
  workspaceId: string,
  monitorId: string,
  page = 1,
  limit = 20
): Promise<ProcessMonitorEventsResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
  })
  const response = await apiClient.get<ProcessMonitorEventsResponse>(
    `/workspaces/${workspaceId}/process-monitors/${monitorId}/events?${params}`
  )
  return response.data
}
