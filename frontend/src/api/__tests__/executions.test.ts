import { describe, it, expect, beforeEach, vi } from 'vitest'
import { getExecutions, getExecution, getExecutionStats, getLatestExecution } from '../executions'
import { apiClient } from '../client'
import { mockExecution } from '@/test/mocks/data'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('executions API', () => {
  const workspaceId = 'workspace-1'

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getExecutions', () => {
    it('should return paginated list of executions', async () => {
      const mockResponse = {
        executions: [mockExecution],
        pagination: { page: 1, limit: 20, total: 1, total_pages: 1 },
      }
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse })

      const result = await getExecutions(workspaceId)

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/workspace-1/executions')
      expect(result.executions).toBeDefined()
      expect(Array.isArray(result.executions)).toBe(true)
    })

    it('should support filter by task_type', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { executions: [mockExecution], pagination: {} },
      })

      await getExecutions(workspaceId, { task_type: 'cron' })

      expect(apiClient.get).toHaveBeenCalledWith(
        '/workspaces/workspace-1/executions?task_type=cron'
      )
    })

    it('should support filter by status', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { executions: [], pagination: {} },
      })

      await getExecutions(workspaceId, { status: 'failed' })

      expect(apiClient.get).toHaveBeenCalledWith(
        '/workspaces/workspace-1/executions?status=failed'
      )
    })

    it('should support filter by task_id', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { executions: [mockExecution], pagination: {} },
      })

      await getExecutions(workspaceId, { task_id: 'task-123' })

      expect(apiClient.get).toHaveBeenCalledWith(
        '/workspaces/workspace-1/executions?task_id=task-123'
      )
    })

    it('should support pagination', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { executions: [], pagination: { page: 3, limit: 100 } },
      })

      await getExecutions(workspaceId, { page: 3, limit: 100 })

      expect(apiClient.get).toHaveBeenCalledWith(
        '/workspaces/workspace-1/executions?page=3&limit=100'
      )
    })
  })

  describe('getExecution', () => {
    it('should return execution details', async () => {
      const detailedExecution = {
        ...mockExecution,
        request_headers: { 'Content-Type': 'application/json' },
        request_body: '{}',
        response_headers: {},
        response_body: '{"ok": true}',
        response_size_bytes: 13,
      }
      vi.mocked(apiClient.get).mockResolvedValue({ data: detailedExecution })

      const result = await getExecution(workspaceId, 'execution-1')

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/workspace-1/executions/execution-1')
      expect(result.id).toBe('execution-1')
      expect(result.request_headers).toBeDefined()
    })

    it('should throw error for non-existent execution', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Execution not found'))

      await expect(getExecution(workspaceId, 'non-existent')).rejects.toThrow()
    })
  })

  describe('getExecutionStats', () => {
    it('should return execution statistics', async () => {
      const mockStats = {
        total: 100,
        success: 95,
        failed: 5,
        success_rate: 0.95,
        avg_duration_ms: 150,
      }
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockStats })

      const result = await getExecutionStats(workspaceId)

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/workspace-1/executions/stats')
      expect(result.total).toBeDefined()
      expect(result.success).toBeDefined()
      expect(result.failed).toBeDefined()
      expect(result.success_rate).toBeDefined()
    })

    it('should support days parameter', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { total: 500, success: 480, failed: 20, success_rate: 0.96, avg_duration_ms: 120 },
      })

      await getExecutionStats(workspaceId, 30)

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/workspace-1/executions/stats?days=30')
    })
  })

  describe('getLatestExecution', () => {
    const taskId = 'task-123'

    it('should return latest execution when executions exist', async () => {
      const detailedExecution = {
        ...mockExecution,
        request_headers: { 'Content-Type': 'application/json' },
        response_headers: {},
      }

      // First call to getExecutions returns list with one execution
      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: {
          executions: [mockExecution],
          pagination: { page: 1, limit: 1, total: 1, total_pages: 1 },
        },
      })

      // Second call to getExecution returns detailed execution
      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: detailedExecution,
      })

      const result = await getLatestExecution(workspaceId, taskId)

      expect(apiClient.get).toHaveBeenNthCalledWith(1, '/workspaces/workspace-1/executions?page=1&limit=1&task_id=task-123')
      expect(apiClient.get).toHaveBeenNthCalledWith(2, '/workspaces/workspace-1/executions/execution-1')
      expect(result).toEqual(detailedExecution)
    })

    it('should return null when no executions exist', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: {
          executions: [],
          pagination: { page: 1, limit: 1, total: 0, total_pages: 0 },
        },
      })

      const result = await getLatestExecution(workspaceId, taskId)

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/workspace-1/executions?page=1&limit=1&task_id=task-123')
      expect(result).toBeNull()
    })

    it('should include task_type filter when provided', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: {
          executions: [mockExecution],
          pagination: { page: 1, limit: 1, total: 1, total_pages: 1 },
        },
      })

      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: mockExecution,
      })

      await getLatestExecution(workspaceId, taskId, 'cron')

      expect(apiClient.get).toHaveBeenNthCalledWith(1, '/workspaces/workspace-1/executions?page=1&limit=1&task_type=cron&task_id=task-123')
    })

    it('should pass task_type to getExecution when provided', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: {
          executions: [mockExecution],
          pagination: { page: 1, limit: 1, total: 1, total_pages: 1 },
        },
      })

      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: mockExecution,
      })

      await getLatestExecution(workspaceId, taskId, 'delayed')

      expect(apiClient.get).toHaveBeenNthCalledWith(2, '/workspaces/workspace-1/executions/execution-1?execution_type=delayed')
    })
  })
})
