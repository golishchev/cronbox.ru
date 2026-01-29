import { apiClient } from './client'

export interface NotificationSettings {
  id: string
  workspace_id: string
  telegram_enabled: boolean
  telegram_chat_ids: string[] | null
  max_enabled: boolean
  max_chat_ids: string[] | null
  email_enabled: boolean
  email_addresses: string[] | null
  webhook_enabled: boolean
  webhook_url: string | null
  webhook_secret: string | null
  notify_on_failure: boolean
  notify_on_recovery: boolean
  notify_on_success: boolean
}

export interface NotificationSettingsUpdate {
  telegram_enabled?: boolean
  telegram_chat_ids?: string[]
  max_enabled?: boolean
  max_chat_ids?: string[]
  email_enabled?: boolean
  email_addresses?: string[]
  webhook_enabled?: boolean
  webhook_url?: string
  webhook_secret?: string
  notify_on_failure?: boolean
  notify_on_recovery?: boolean
  notify_on_success?: boolean
}

export async function getNotificationSettings(
  workspaceId: string
): Promise<NotificationSettings> {
  const response = await apiClient.get<NotificationSettings>(
    `/workspaces/${workspaceId}/notifications`
  )
  return response.data
}

export async function updateNotificationSettings(
  workspaceId: string,
  data: NotificationSettingsUpdate
): Promise<NotificationSettings> {
  const response = await apiClient.patch<NotificationSettings>(
    `/workspaces/${workspaceId}/notifications`,
    data
  )
  return response.data
}

export async function sendTestNotification(
  workspaceId: string,
  channel: 'telegram' | 'max' | 'email' | 'webhook'
): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.post<{ success: boolean; message: string }>(
    `/workspaces/${workspaceId}/notifications/test`,
    { channel }
  )
  return response.data
}
