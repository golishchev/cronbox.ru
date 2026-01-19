import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  getSSLMonitors,
  getSSLMonitor,
  createSSLMonitor,
  updateSSLMonitor,
  deleteSSLMonitor,
  pauseSSLMonitor,
  resumeSSLMonitor,
  checkSSLMonitor,
} from '../sslMonitors'
import { apiClient } from '../client'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockSSLMonitor = {
  id: 'ssl-1',
  workspace_id: 'workspace-1',
  name: 'Test SSL',
  description: null,
  domain: 'example.com',
  port: 443,
  status: 'valid',
  cert_expires_at: '2025-06-01T00:00:00Z',
  cert_subject: 'example.com',
  cert_issuer: "Let's Encrypt",
  tls_version: 'TLSv1.3',
  last_checked_at: '2024-01-01T12:00:00Z',
  last_error: null,
  retry_count: 0,
  next_retry_at: null,
  next_check_at: '2024-01-02T12:00:00Z',
  notify_on_expiring: true,
  notify_on_error: true,
  notified_at_14_days: false,
  notified_at_7_days: false,
  notified_at_3_days: false,
  notified_at_1_day: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

describe('sslMonitors API', () => {
  const workspaceId = 'workspace-1'

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getSSLMonitors', () => {
    it('should call get with default pagination', async () => {
      const mockResponse = {
        monitors: [mockSSLMonitor],
        pagination: { page: 1, limit: 20, total: 1, total_pages: 1 },
      }
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse })

      const result = await getSSLMonitors(workspaceId)

      expect(apiClient.get).toHaveBeenCalledWith(
        '/workspaces/workspace-1/ssl-monitors',
        { params: { page: 1, limit: 20 } }
      )
      expect(result.monitors).toHaveLength(1)
    })

    it('should call get with custom pagination', async () => {
      const mockResponse = {
        monitors: [],
        pagination: { page: 2, limit: 50, total: 0, total_pages: 0 },
      }
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse })

      await getSSLMonitors(workspaceId, 2, 50)

      expect(apiClient.get).toHaveBeenCalledWith(
        '/workspaces/workspace-1/ssl-monitors',
        { params: { page: 2, limit: 50 } }
      )
    })
  })

  describe('getSSLMonitor', () => {
    it('should call get with monitor id', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockSSLMonitor })

      const result = await getSSLMonitor(workspaceId, 'ssl-1')

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/workspace-1/ssl-monitors/ssl-1')
      expect(result.id).toBe('ssl-1')
    })
  })

  describe('createSSLMonitor', () => {
    it('should call post with monitor data', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockSSLMonitor })

      const createData = {
        name: 'Test SSL',
        domain: 'example.com',
      }

      const result = await createSSLMonitor(workspaceId, createData)

      expect(apiClient.post).toHaveBeenCalledWith(
        '/workspaces/workspace-1/ssl-monitors',
        createData
      )
      expect(result.name).toBe('Test SSL')
    })

    it('should call post with all optional fields', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockSSLMonitor })

      const createData = {
        name: 'Test SSL',
        domain: 'example.com',
        port: 8443,
        description: 'Test description',
        notify_on_expiring: true,
        notify_on_error: false,
      }

      await createSSLMonitor(workspaceId, createData)

      expect(apiClient.post).toHaveBeenCalledWith(
        '/workspaces/workspace-1/ssl-monitors',
        createData
      )
    })
  })

  describe('updateSSLMonitor', () => {
    it('should call patch with update data', async () => {
      const updatedMonitor = { ...mockSSLMonitor, name: 'Updated SSL' }
      vi.mocked(apiClient.patch).mockResolvedValue({ data: updatedMonitor })

      const updateData = { name: 'Updated SSL' }

      const result = await updateSSLMonitor(workspaceId, 'ssl-1', updateData)

      expect(apiClient.patch).toHaveBeenCalledWith(
        '/workspaces/workspace-1/ssl-monitors/ssl-1',
        updateData
      )
      expect(result.name).toBe('Updated SSL')
    })

    it('should call patch with port update', async () => {
      const updatedMonitor = { ...mockSSLMonitor, port: 8443 }
      vi.mocked(apiClient.patch).mockResolvedValue({ data: updatedMonitor })

      await updateSSLMonitor(workspaceId, 'ssl-1', { port: 8443 })

      expect(apiClient.patch).toHaveBeenCalledWith(
        '/workspaces/workspace-1/ssl-monitors/ssl-1',
        { port: 8443 }
      )
    })
  })

  describe('deleteSSLMonitor', () => {
    it('should call delete with monitor id', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({})

      await deleteSSLMonitor(workspaceId, 'ssl-1')

      expect(apiClient.delete).toHaveBeenCalledWith('/workspaces/workspace-1/ssl-monitors/ssl-1')
    })
  })

  describe('pauseSSLMonitor', () => {
    it('should call post to pause endpoint', async () => {
      const pausedMonitor = { ...mockSSLMonitor, status: 'paused' }
      vi.mocked(apiClient.post).mockResolvedValue({ data: pausedMonitor })

      const result = await pauseSSLMonitor(workspaceId, 'ssl-1')

      expect(apiClient.post).toHaveBeenCalledWith(
        '/workspaces/workspace-1/ssl-monitors/ssl-1/pause'
      )
      expect(result.status).toBe('paused')
    })
  })

  describe('resumeSSLMonitor', () => {
    it('should call post to resume endpoint', async () => {
      const resumedMonitor = { ...mockSSLMonitor, status: 'pending' }
      vi.mocked(apiClient.post).mockResolvedValue({ data: resumedMonitor })

      const result = await resumeSSLMonitor(workspaceId, 'ssl-1')

      expect(apiClient.post).toHaveBeenCalledWith(
        '/workspaces/workspace-1/ssl-monitors/ssl-1/resume'
      )
      expect(result.status).toBe('pending')
    })
  })

  describe('checkSSLMonitor', () => {
    it('should call post to check endpoint', async () => {
      const checkedMonitor = { ...mockSSLMonitor, last_checked_at: '2024-01-01T13:00:00Z' }
      vi.mocked(apiClient.post).mockResolvedValue({ data: checkedMonitor })

      const result = await checkSSLMonitor(workspaceId, 'ssl-1')

      expect(apiClient.post).toHaveBeenCalledWith(
        '/workspaces/workspace-1/ssl-monitors/ssl-1/check'
      )
      expect(result.last_checked_at).toBe('2024-01-01T13:00:00Z')
    })
  })
})
