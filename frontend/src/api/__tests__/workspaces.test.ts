import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  getWorkspaces,
  getWorkspace,
  createWorkspace,
  updateWorkspace,
  deleteWorkspace,
} from '../workspaces'
import { apiClient } from '../client'
import { mockWorkspace } from '@/test/mocks/data'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('workspaces API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getWorkspaces', () => {
    it('should return list of workspaces', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: [mockWorkspace] })

      const result = await getWorkspaces()

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces')
      expect(Array.isArray(result)).toBe(true)
      expect(result.length).toBe(1)
      expect(result[0].id).toBeDefined()
    })

    it('should return empty array when no workspaces', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: [] })

      const result = await getWorkspaces()

      expect(result).toEqual([])
    })
  })

  describe('getWorkspace', () => {
    it('should return workspace with stats', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { ...mockWorkspace, stats: { total_tasks: 10 } },
      })

      const result = await getWorkspace('workspace-1')

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/workspace-1')
      expect(result.id).toBe('workspace-1')
    })

    it('should throw error for non-existent workspace', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Workspace not found'))

      await expect(getWorkspace('non-existent')).rejects.toThrow()
    })
  })

  describe('createWorkspace', () => {
    it('should create and return new workspace', async () => {
      const newWorkspace = { name: 'New Workspace', slug: 'new-workspace' }
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { ...mockWorkspace, ...newWorkspace },
      })

      const result = await createWorkspace(newWorkspace)

      expect(apiClient.post).toHaveBeenCalledWith('/workspaces', newWorkspace)
      expect(result.name).toBe('New Workspace')
      expect(result.slug).toBe('new-workspace')
    })

    it('should throw error on duplicate slug', async () => {
      vi.mocked(apiClient.post).mockRejectedValue(new Error('Slug already exists'))

      await expect(
        createWorkspace({ name: 'Test', slug: 'existing-slug' })
      ).rejects.toThrow()
    })
  })

  describe('updateWorkspace', () => {
    it('should update and return workspace', async () => {
      vi.mocked(apiClient.patch).mockResolvedValue({
        data: { ...mockWorkspace, name: 'Updated Name' },
      })

      const result = await updateWorkspace('workspace-1', { name: 'Updated Name' })

      expect(apiClient.patch).toHaveBeenCalledWith('/workspaces/workspace-1', {
        name: 'Updated Name',
      })
      expect(result.name).toBe('Updated Name')
    })

    it('should throw error for non-existent workspace', async () => {
      vi.mocked(apiClient.patch).mockRejectedValue(new Error('Workspace not found'))

      await expect(updateWorkspace('non-existent', { name: 'Test' })).rejects.toThrow()
    })
  })

  describe('deleteWorkspace', () => {
    it('should delete workspace successfully', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({ data: {} })

      await expect(deleteWorkspace('workspace-1')).resolves.not.toThrow()
      expect(apiClient.delete).toHaveBeenCalledWith('/workspaces/workspace-1')
    })

    it('should throw error for non-existent workspace', async () => {
      vi.mocked(apiClient.delete).mockRejectedValue(new Error('Workspace not found'))

      await expect(deleteWorkspace('non-existent')).rejects.toThrow()
    })
  })
})
