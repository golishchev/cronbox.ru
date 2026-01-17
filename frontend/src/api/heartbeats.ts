import { apiClient } from './client'
import type {
  Heartbeat,
  CreateHeartbeatRequest,
  UpdateHeartbeatRequest,
  HeartbeatPing,
  PaginationMeta,
} from '@/types'

interface HeartbeatsResponse {
  heartbeats: Heartbeat[]
  pagination: PaginationMeta
}

interface HeartbeatPingsResponse {
  pings: HeartbeatPing[]
  pagination: PaginationMeta
}

export async function getHeartbeats(
  workspaceId: string,
  page = 1,
  limit = 20
): Promise<HeartbeatsResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
  })
  const response = await apiClient.get<HeartbeatsResponse>(
    `/workspaces/${workspaceId}/heartbeats?${params}`
  )
  return response.data
}

export async function getHeartbeat(
  workspaceId: string,
  heartbeatId: string
): Promise<Heartbeat> {
  const response = await apiClient.get<Heartbeat>(
    `/workspaces/${workspaceId}/heartbeats/${heartbeatId}`
  )
  return response.data
}

export async function createHeartbeat(
  workspaceId: string,
  data: CreateHeartbeatRequest
): Promise<Heartbeat> {
  const response = await apiClient.post<Heartbeat>(
    `/workspaces/${workspaceId}/heartbeats`,
    data
  )
  return response.data
}

export async function updateHeartbeat(
  workspaceId: string,
  heartbeatId: string,
  data: UpdateHeartbeatRequest
): Promise<Heartbeat> {
  const response = await apiClient.patch<Heartbeat>(
    `/workspaces/${workspaceId}/heartbeats/${heartbeatId}`,
    data
  )
  return response.data
}

export async function deleteHeartbeat(
  workspaceId: string,
  heartbeatId: string
): Promise<void> {
  await apiClient.delete(`/workspaces/${workspaceId}/heartbeats/${heartbeatId}`)
}

export async function pauseHeartbeat(
  workspaceId: string,
  heartbeatId: string
): Promise<Heartbeat> {
  const response = await apiClient.post<Heartbeat>(
    `/workspaces/${workspaceId}/heartbeats/${heartbeatId}/pause`
  )
  return response.data
}

export async function resumeHeartbeat(
  workspaceId: string,
  heartbeatId: string
): Promise<Heartbeat> {
  const response = await apiClient.post<Heartbeat>(
    `/workspaces/${workspaceId}/heartbeats/${heartbeatId}/resume`
  )
  return response.data
}

export async function getHeartbeatPings(
  workspaceId: string,
  heartbeatId: string,
  page = 1,
  limit = 20
): Promise<HeartbeatPingsResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
  })
  const response = await apiClient.get<HeartbeatPingsResponse>(
    `/workspaces/${workspaceId}/heartbeats/${heartbeatId}/pings?${params}`
  )
  return response.data
}
