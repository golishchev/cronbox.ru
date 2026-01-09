import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  getWorkers,
  getWorker,
  createWorker,
  updateWorker,
  deleteWorker,
  regenerateWorkerKey,
} from '../workers'
import { apiClient } from '../client'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('workers API', () => {
  const workspaceId = 'workspace-1'

  const mockWorker = {
    id: 'worker-1',
    workspace_id: workspaceId,
    name: 'Test Worker',
    description: 'A test worker',
    region: 'eu-west',
    status: 'online' as const,
    is_active: true,
    api_key_prefix: 'wk_abc',
    last_heartbeat: '2024-01-01T00:00:00Z',
    tasks_completed: 100,
    tasks_failed: 5,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getWorkers', () => {
    it('should return list of workers', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: [mockWorker] })

      const result = await getWorkers(workspaceId)

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/workspace-1/workers')
      expect(Array.isArray(result)).toBe(true)
      expect(result.length).toBe(1)
      expect(result[0].name).toBe('Test Worker')
    })

    it('should return empty array when no workers', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: [] })

      const result = await getWorkers(workspaceId)

      expect(result).toEqual([])
    })
  })

  describe('getWorker', () => {
    it('should return single worker', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockWorker })

      const result = await getWorker(workspaceId, 'worker-1')

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/workspace-1/workers/worker-1')
      expect(result.id).toBe('worker-1')
      expect(result.name).toBe('Test Worker')
      expect(result.status).toBe('online')
    })

    it('should throw error for non-existent worker', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Worker not found'))

      await expect(getWorker(workspaceId, 'non-existent')).rejects.toThrow()
    })
  })

  describe('createWorker', () => {
    it('should create and return new worker with API key', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: {
          id: 'new-worker',
          workspace_id: workspaceId,
          name: 'New Worker',
          description: 'Description',
          region: 'us-east',
          api_key: 'wk_secret_full_key_12345',
          api_key_prefix: 'wk_sec',
          created_at: new Date().toISOString(),
        },
      })

      const result = await createWorker(workspaceId, {
        name: 'New Worker',
        description: 'Description',
        region: 'us-east',
      })

      expect(apiClient.post).toHaveBeenCalledWith('/workspaces/workspace-1/workers', {
        name: 'New Worker',
        description: 'Description',
        region: 'us-east',
      })
      expect(result.id).toBeDefined()
      expect(result.api_key).toBeDefined()
      expect(result.api_key_prefix).toBeDefined()
    })
  })

  describe('updateWorker', () => {
    it('should update worker name', async () => {
      vi.mocked(apiClient.patch).mockResolvedValue({
        data: { ...mockWorker, name: 'Updated Name' },
      })

      const result = await updateWorker(workspaceId, 'worker-1', { name: 'Updated Name' })

      expect(apiClient.patch).toHaveBeenCalledWith('/workspaces/workspace-1/workers/worker-1', {
        name: 'Updated Name',
      })
      expect(result.name).toBe('Updated Name')
    })

    it('should update worker active status', async () => {
      vi.mocked(apiClient.patch).mockResolvedValue({
        data: { ...mockWorker, is_active: false },
      })

      const result = await updateWorker(workspaceId, 'worker-1', { is_active: false })

      expect(result.is_active).toBe(false)
    })
  })

  describe('deleteWorker', () => {
    it('should delete worker successfully', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({ data: {} })

      await expect(deleteWorker(workspaceId, 'worker-1')).resolves.not.toThrow()
      expect(apiClient.delete).toHaveBeenCalledWith('/workspaces/workspace-1/workers/worker-1')
    })
  })

  describe('regenerateWorkerKey', () => {
    it('should regenerate and return new API key', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: {
          id: 'worker-1',
          workspace_id: workspaceId,
          name: 'Test Worker',
          description: null,
          region: null,
          api_key: 'wk_new_secret_key_67890',
          api_key_prefix: 'wk_new',
          created_at: new Date().toISOString(),
        },
      })

      const result = await regenerateWorkerKey(workspaceId, 'worker-1')

      expect(apiClient.post).toHaveBeenCalledWith('/workspaces/workspace-1/workers/worker-1/regenerate-key')
      expect(result.api_key).toBeDefined()
      expect(result.api_key).toContain('wk_new')
    })
  })
})
