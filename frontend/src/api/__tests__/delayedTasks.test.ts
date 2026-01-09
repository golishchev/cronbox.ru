import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  getDelayedTasks,
  getDelayedTask,
  createDelayedTask,
  updateDelayedTask,
  cancelDelayedTask,
} from '../delayedTasks'
import { apiClient } from '../client'
import { mockDelayedTask } from '@/test/mocks/data'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('delayedTasks API', () => {
  const workspaceId = 'workspace-1'

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getDelayedTasks', () => {
    it('should return paginated list of tasks', async () => {
      const mockResponse = {
        tasks: [mockDelayedTask],
        pagination: { page: 1, limit: 20, total: 1, total_pages: 1 },
      }
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse })

      const result = await getDelayedTasks(workspaceId)

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/workspace-1/delayed')
      expect(result.tasks).toBeDefined()
      expect(Array.isArray(result.tasks)).toBe(true)
    })

    it('should support filter parameters', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { tasks: [], pagination: { page: 2, limit: 50, total: 0, total_pages: 0 } },
      })

      await getDelayedTasks(workspaceId, { page: 2, limit: 50, status: 'pending' })

      expect(apiClient.get).toHaveBeenCalledWith(
        '/workspaces/workspace-1/delayed?page=2&limit=50&status=pending'
      )
    })

    it('should work without filters', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { tasks: [], pagination: {} },
      })

      const result = await getDelayedTasks(workspaceId)

      expect(result.tasks).toBeDefined()
    })
  })

  describe('getDelayedTask', () => {
    it('should return single task', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockDelayedTask })

      const result = await getDelayedTask(workspaceId, 'delayed-task-1')

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/workspace-1/delayed/delayed-task-1')
      expect(result.id).toBe('delayed-task-1')
      expect(result.url).toBeDefined()
    })

    it('should throw error for non-existent task', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Task not found'))

      await expect(getDelayedTask(workspaceId, 'non-existent')).rejects.toThrow()
    })
  })

  describe('createDelayedTask', () => {
    it('should create and return new task', async () => {
      const newTask = {
        url: 'https://example.com/webhook',
        execute_at: '2025-01-01T00:00:00Z',
        name: 'New Delayed Task',
      }
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { ...mockDelayedTask, ...newTask },
      })

      const result = await createDelayedTask(workspaceId, newTask)

      expect(apiClient.post).toHaveBeenCalledWith('/workspaces/workspace-1/delayed', newTask)
      expect(result.id).toBeDefined()
      expect(result.url).toBe('https://example.com/webhook')
    })

    it('should throw error for past execution time', async () => {
      vi.mocked(apiClient.post).mockRejectedValue(new Error('Execution time must be in the future'))

      await expect(
        createDelayedTask(workspaceId, {
          url: 'https://example.com',
          execute_at: '2020-01-01T00:00:00Z',
        })
      ).rejects.toThrow()
    })
  })

  describe('updateDelayedTask', () => {
    it('should update and return task', async () => {
      vi.mocked(apiClient.patch).mockResolvedValue({
        data: { ...mockDelayedTask, name: 'Updated Name' },
      })

      const result = await updateDelayedTask(workspaceId, 'delayed-task-1', {
        name: 'Updated Name',
      })

      expect(apiClient.patch).toHaveBeenCalledWith('/workspaces/workspace-1/delayed/delayed-task-1', {
        name: 'Updated Name',
      })
      expect(result.name).toBe('Updated Name')
    })

    it('should update execution time', async () => {
      const newTime = '2025-06-01T00:00:00Z'
      vi.mocked(apiClient.patch).mockResolvedValue({
        data: { ...mockDelayedTask, execute_at: newTime },
      })

      const result = await updateDelayedTask(workspaceId, 'delayed-task-1', {
        execute_at: newTime,
      })

      expect(result.execute_at).toBe(newTime)
    })
  })

  describe('cancelDelayedTask', () => {
    it('should cancel task and return it', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        data: { ...mockDelayedTask, status: 'cancelled' },
      })

      const result = await cancelDelayedTask(workspaceId, 'delayed-task-1')

      expect(apiClient.delete).toHaveBeenCalledWith('/workspaces/workspace-1/delayed/delayed-task-1')
      expect(result.status).toBe('cancelled')
    })

    it('should throw error for already executed task', async () => {
      vi.mocked(apiClient.delete).mockRejectedValue(new Error('Task already executed'))

      await expect(cancelDelayedTask(workspaceId, 'executed-task')).rejects.toThrow()
    })
  })
})
