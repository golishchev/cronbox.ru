import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  getCronTasks,
  getCronTask,
  createCronTask,
  updateCronTask,
  deleteCronTask,
  runCronTask,
  pauseCronTask,
  resumeCronTask,
} from '../cronTasks'
import { apiClient } from '../client'
import { mockCronTask } from '@/test/mocks/data'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('cronTasks API', () => {
  const workspaceId = 'workspace-1'

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getCronTasks', () => {
    it('should call get with default pagination', async () => {
      const mockResponse = {
        tasks: [mockCronTask],
        pagination: { page: 1, limit: 20, total: 1, total_pages: 1 },
      }
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse })

      const result = await getCronTasks(workspaceId)

      expect(apiClient.get).toHaveBeenCalledWith(
        '/workspaces/workspace-1/cron?page=1&limit=20'
      )
      expect(result.tasks).toHaveLength(1)
    })

    it('should call get with custom pagination', async () => {
      const mockResponse = {
        tasks: [],
        pagination: { page: 2, limit: 50, total: 0, total_pages: 0 },
      }
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse })

      await getCronTasks(workspaceId, 2, 50)

      expect(apiClient.get).toHaveBeenCalledWith(
        '/workspaces/workspace-1/cron?page=2&limit=50'
      )
    })

    it('should filter by isActive', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { tasks: [], pagination: {} },
      })

      await getCronTasks(workspaceId, 1, 20, true)

      expect(apiClient.get).toHaveBeenCalledWith(
        '/workspaces/workspace-1/cron?page=1&limit=20&is_active=true'
      )
    })
  })

  describe('getCronTask', () => {
    it('should call get with task id', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockCronTask })

      const result = await getCronTask(workspaceId, 'task-1')

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/workspace-1/cron/task-1')
      expect(result.id).toBe('cron-task-1')
    })
  })

  describe('createCronTask', () => {
    it('should call post with task data', async () => {
      const newTask = {
        name: 'New Task',
        url: 'https://example.com/webhook',
        schedule: '0 * * * *',
      }
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { ...mockCronTask, ...newTask },
      })

      const result = await createCronTask(workspaceId, newTask)

      expect(apiClient.post).toHaveBeenCalledWith('/workspaces/workspace-1/cron', newTask)
      expect(result.name).toBe('New Task')
    })
  })

  describe('updateCronTask', () => {
    it('should call patch with task id and data', async () => {
      vi.mocked(apiClient.patch).mockResolvedValue({
        data: { ...mockCronTask, name: 'Updated Name' },
      })

      const result = await updateCronTask(workspaceId, 'task-1', { name: 'Updated Name' })

      expect(apiClient.patch).toHaveBeenCalledWith('/workspaces/workspace-1/cron/task-1', {
        name: 'Updated Name',
      })
      expect(result.name).toBe('Updated Name')
    })
  })

  describe('deleteCronTask', () => {
    it('should call delete with task id', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({ data: {} })

      await deleteCronTask(workspaceId, 'task-1')

      expect(apiClient.delete).toHaveBeenCalledWith('/workspaces/workspace-1/cron/task-1')
    })
  })

  describe('runCronTask', () => {
    it('should call post to run task', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { message: 'Task queued', task_id: 'exec-123' },
      })

      const result = await runCronTask(workspaceId, 'task-1')

      expect(apiClient.post).toHaveBeenCalledWith('/workspaces/workspace-1/cron/task-1/run')
      expect(result.message).toBe('Task queued')
    })
  })

  describe('pauseCronTask', () => {
    it('should call post to pause task', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { ...mockCronTask, is_active: false },
      })

      const result = await pauseCronTask(workspaceId, 'task-1')

      expect(apiClient.post).toHaveBeenCalledWith('/workspaces/workspace-1/cron/task-1/pause')
      expect(result.is_active).toBe(false)
    })
  })

  describe('resumeCronTask', () => {
    it('should call post to resume task', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { ...mockCronTask, is_active: true },
      })

      const result = await resumeCronTask(workspaceId, 'task-1')

      expect(apiClient.post).toHaveBeenCalledWith('/workspaces/workspace-1/cron/task-1/resume')
      expect(result.is_active).toBe(true)
    })
  })
})
