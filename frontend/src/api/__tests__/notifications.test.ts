import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  getNotificationSettings,
  updateNotificationSettings,
  sendTestNotification,
} from '../notifications'
import { apiClient } from '../client'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('notifications API', () => {
  const workspaceId = 'workspace-1'

  const mockSettings = {
    id: 'notif-1',
    workspace_id: workspaceId,
    telegram_enabled: false,
    telegram_chat_ids: null,
    email_enabled: true,
    email_addresses: ['test@example.com'],
    webhook_enabled: false,
    webhook_url: null,
    webhook_secret: null,
    notify_on_failure: true,
    notify_on_recovery: true,
    notify_on_success: false,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getNotificationSettings', () => {
    it('should return notification settings', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockSettings })

      const result = await getNotificationSettings(workspaceId)

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/workspace-1/notifications')
      expect(result.id).toBeDefined()
      expect(result.email_enabled).toBe(true)
      expect(result.notify_on_failure).toBe(true)
    })
  })

  describe('updateNotificationSettings', () => {
    it('should update email settings', async () => {
      vi.mocked(apiClient.patch).mockResolvedValue({
        data: { ...mockSettings, email_addresses: ['new@example.com'] },
      })

      const result = await updateNotificationSettings(workspaceId, {
        email_enabled: true,
        email_addresses: ['new@example.com'],
      })

      expect(apiClient.patch).toHaveBeenCalledWith('/workspaces/workspace-1/notifications', {
        email_enabled: true,
        email_addresses: ['new@example.com'],
      })
      expect(result.email_enabled).toBe(true)
    })

    it('should update telegram settings', async () => {
      vi.mocked(apiClient.patch).mockResolvedValue({
        data: { ...mockSettings, telegram_enabled: true, telegram_chat_ids: ['123456789'] },
      })

      const result = await updateNotificationSettings(workspaceId, {
        telegram_enabled: true,
        telegram_chat_ids: ['123456789'],
      })

      expect(result.telegram_enabled).toBe(true)
    })

    it('should update webhook settings', async () => {
      vi.mocked(apiClient.patch).mockResolvedValue({
        data: {
          ...mockSettings,
          webhook_enabled: true,
          webhook_url: 'https://example.com/webhook',
          webhook_secret: 'secret123',
        },
      })

      const result = await updateNotificationSettings(workspaceId, {
        webhook_enabled: true,
        webhook_url: 'https://example.com/webhook',
        webhook_secret: 'secret123',
      })

      expect(result.webhook_enabled).toBe(true)
    })
  })

  describe('sendTestNotification', () => {
    it('should send test email notification', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { success: true, message: 'Test email sent' },
      })

      const result = await sendTestNotification(workspaceId, 'email')

      expect(apiClient.post).toHaveBeenCalledWith('/workspaces/workspace-1/notifications/test', {
        channel: 'email',
      })
      expect(result.success).toBe(true)
      expect(result.message).toBeDefined()
    })

    it('should send test telegram notification', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { success: true, message: 'Test telegram sent' },
      })

      const result = await sendTestNotification(workspaceId, 'telegram')

      expect(apiClient.post).toHaveBeenCalledWith('/workspaces/workspace-1/notifications/test', {
        channel: 'telegram',
      })
      expect(result.success).toBe(true)
    })

    it('should handle failed test notification', async () => {
      vi.mocked(apiClient.post).mockRejectedValue(new Error('Channel not configured'))

      await expect(sendTestNotification(workspaceId, 'webhook')).rejects.toThrow()
    })
  })
})
