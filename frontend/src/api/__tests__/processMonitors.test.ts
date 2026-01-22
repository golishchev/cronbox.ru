import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  getProcessMonitors,
  getProcessMonitor,
  createProcessMonitor,
  updateProcessMonitor,
  deleteProcessMonitor,
  pauseProcessMonitor,
  resumeProcessMonitor,
  getProcessMonitorEvents,
} from '../processMonitors'
import { apiClient } from '../client'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockProcessMonitor = {
  id: 'pm-1',
  workspace_id: 'workspace-1',
  name: 'Test Process Monitor',
  description: 'A test process monitor',
  start_token: 'start-token-123',
  end_token: 'end-token-456',
  start_url: 'https://api.example.com/ping/start/start-token-123',
  end_url: 'https://api.example.com/ping/end/end-token-456',
  schedule_type: 'cron',
  schedule_cron: '0 2 * * *',
  schedule_interval: null,
  schedule_exact_time: null,
  timezone: 'UTC',
  start_grace_period: 300,
  end_timeout: 3600,
  status: 'waiting_start',
  is_paused: false,
  last_start_at: null,
  last_end_at: null,
  last_duration_ms: null,
  next_expected_start: '2024-01-01T02:00:00Z',
  start_deadline: '2024-01-01T02:05:00Z',
  end_deadline: null,
  current_run_id: null,
  consecutive_successes: 0,
  consecutive_failures: 0,
  notify_on_missed_start: true,
  notify_on_missed_end: true,
  notify_on_recovery: true,
  notify_on_success: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const mockProcessMonitorEvent = {
  id: 'event-1',
  monitor_id: 'pm-1',
  event_type: 'start',
  run_id: 'run-123',
  duration_ms: null,
  status_message: 'Process started',
  payload: null,
  source_ip: '127.0.0.1',
  created_at: '2024-01-01T02:00:00Z',
}

describe('processMonitors API', () => {
  const workspaceId = 'workspace-1'

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getProcessMonitors', () => {
    it('should call get with default pagination', async () => {
      const mockResponse = {
        process_monitors: [mockProcessMonitor],
        pagination: { page: 1, limit: 20, total: 1, total_pages: 1 },
      }
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse })

      const result = await getProcessMonitors(workspaceId)

      expect(apiClient.get).toHaveBeenCalledWith(
        '/workspaces/workspace-1/process-monitors?page=1&limit=20'
      )
      expect(result.process_monitors).toHaveLength(1)
    })

    it('should call get with custom pagination', async () => {
      const mockResponse = {
        process_monitors: [],
        pagination: { page: 2, limit: 50, total: 0, total_pages: 0 },
      }
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse })

      await getProcessMonitors(workspaceId, 2, 50)

      expect(apiClient.get).toHaveBeenCalledWith(
        '/workspaces/workspace-1/process-monitors?page=2&limit=50'
      )
    })
  })

  describe('getProcessMonitor', () => {
    it('should call get with monitor id', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockProcessMonitor })

      const result = await getProcessMonitor(workspaceId, 'pm-1')

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/workspace-1/process-monitors/pm-1')
      expect(result.id).toBe('pm-1')
    })
  })

  describe('createProcessMonitor', () => {
    it('should call post with monitor data', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockProcessMonitor })

      const createData = {
        name: 'Test Process Monitor',
        schedule_type: 'cron' as const,
        schedule_cron: '0 2 * * *',
        start_grace_period: '5m',
        end_timeout: '1h',
      }

      const result = await createProcessMonitor(workspaceId, createData)

      expect(apiClient.post).toHaveBeenCalledWith(
        '/workspaces/workspace-1/process-monitors',
        createData
      )
      expect(result.name).toBe('Test Process Monitor')
    })

    it('should call post with interval schedule', async () => {
      const intervalMonitor = { ...mockProcessMonitor, schedule_type: 'interval', schedule_interval: 21600 }
      vi.mocked(apiClient.post).mockResolvedValue({ data: intervalMonitor })

      const createData = {
        name: 'Interval Monitor',
        schedule_type: 'interval' as const,
        schedule_interval: '6h',
        start_grace_period: '10m',
        end_timeout: '1h',
      }

      await createProcessMonitor(workspaceId, createData)

      expect(apiClient.post).toHaveBeenCalledWith(
        '/workspaces/workspace-1/process-monitors',
        createData
      )
    })

    it('should call post with exact_time schedule', async () => {
      const exactTimeMonitor = { ...mockProcessMonitor, schedule_type: 'exact_time', schedule_exact_time: '09:00' }
      vi.mocked(apiClient.post).mockResolvedValue({ data: exactTimeMonitor })

      const createData = {
        name: 'Exact Time Monitor',
        schedule_type: 'exact_time' as const,
        schedule_exact_time: '09:00',
        timezone: 'Europe/Moscow',
        start_grace_period: '15m',
        end_timeout: '2h',
      }

      await createProcessMonitor(workspaceId, createData)

      expect(apiClient.post).toHaveBeenCalledWith(
        '/workspaces/workspace-1/process-monitors',
        createData
      )
    })

    it('should call post with all notification settings', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockProcessMonitor })

      const createData = {
        name: 'Full Settings Monitor',
        description: 'Monitor with all settings',
        schedule_type: 'cron' as const,
        schedule_cron: '0 * * * *',
        start_grace_period: '5m',
        end_timeout: '30m',
        notify_on_missed_start: true,
        notify_on_missed_end: true,
        notify_on_recovery: true,
        notify_on_success: true,
      }

      await createProcessMonitor(workspaceId, createData)

      expect(apiClient.post).toHaveBeenCalledWith(
        '/workspaces/workspace-1/process-monitors',
        createData
      )
    })
  })

  describe('updateProcessMonitor', () => {
    it('should call patch with update data', async () => {
      const updatedMonitor = { ...mockProcessMonitor, name: 'Updated Monitor' }
      vi.mocked(apiClient.patch).mockResolvedValue({ data: updatedMonitor })

      const updateData = { name: 'Updated Monitor' }

      const result = await updateProcessMonitor(workspaceId, 'pm-1', updateData)

      expect(apiClient.patch).toHaveBeenCalledWith(
        '/workspaces/workspace-1/process-monitors/pm-1',
        updateData
      )
      expect(result.name).toBe('Updated Monitor')
    })

    it('should call patch with schedule update', async () => {
      const updatedMonitor = { ...mockProcessMonitor, schedule_type: 'interval', schedule_interval: 7200 }
      vi.mocked(apiClient.patch).mockResolvedValue({ data: updatedMonitor })

      await updateProcessMonitor(workspaceId, 'pm-1', {
        schedule_type: 'interval',
        schedule_interval: '2h',
      })

      expect(apiClient.patch).toHaveBeenCalledWith(
        '/workspaces/workspace-1/process-monitors/pm-1',
        { schedule_type: 'interval', schedule_interval: '2h' }
      )
    })
  })

  describe('deleteProcessMonitor', () => {
    it('should call delete with monitor id', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({})

      await deleteProcessMonitor(workspaceId, 'pm-1')

      expect(apiClient.delete).toHaveBeenCalledWith('/workspaces/workspace-1/process-monitors/pm-1')
    })
  })

  describe('pauseProcessMonitor', () => {
    it('should call post to pause endpoint', async () => {
      const pausedMonitor = { ...mockProcessMonitor, status: 'paused', is_paused: true }
      vi.mocked(apiClient.post).mockResolvedValue({ data: pausedMonitor })

      const result = await pauseProcessMonitor(workspaceId, 'pm-1')

      expect(apiClient.post).toHaveBeenCalledWith(
        '/workspaces/workspace-1/process-monitors/pm-1/pause'
      )
      expect(result.status).toBe('paused')
      expect(result.is_paused).toBe(true)
    })
  })

  describe('resumeProcessMonitor', () => {
    it('should call post to resume endpoint', async () => {
      const resumedMonitor = { ...mockProcessMonitor, status: 'waiting_start', is_paused: false }
      vi.mocked(apiClient.post).mockResolvedValue({ data: resumedMonitor })

      const result = await resumeProcessMonitor(workspaceId, 'pm-1')

      expect(apiClient.post).toHaveBeenCalledWith(
        '/workspaces/workspace-1/process-monitors/pm-1/resume'
      )
      expect(result.status).toBe('waiting_start')
      expect(result.is_paused).toBe(false)
    })
  })

  describe('getProcessMonitorEvents', () => {
    it('should call get with default pagination', async () => {
      const mockResponse = {
        events: [mockProcessMonitorEvent],
        pagination: { page: 1, limit: 20, total: 1, total_pages: 1 },
      }
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse })

      const result = await getProcessMonitorEvents(workspaceId, 'pm-1')

      expect(apiClient.get).toHaveBeenCalledWith(
        '/workspaces/workspace-1/process-monitors/pm-1/events?page=1&limit=20'
      )
      expect(result.events).toHaveLength(1)
    })

    it('should call get with custom pagination', async () => {
      const mockResponse = {
        events: [],
        pagination: { page: 3, limit: 10, total: 0, total_pages: 0 },
      }
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse })

      await getProcessMonitorEvents(workspaceId, 'pm-1', 3, 10)

      expect(apiClient.get).toHaveBeenCalledWith(
        '/workspaces/workspace-1/process-monitors/pm-1/events?page=3&limit=10'
      )
    })

    it('should return multiple event types', async () => {
      const endEvent = { ...mockProcessMonitorEvent, id: 'event-2', event_type: 'end', duration_ms: 45000 }
      const mockResponse = {
        events: [endEvent, mockProcessMonitorEvent],
        pagination: { page: 1, limit: 20, total: 2, total_pages: 1 },
      }
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse })

      const result = await getProcessMonitorEvents(workspaceId, 'pm-1')

      expect(result.events).toHaveLength(2)
      expect(result.events[0].event_type).toBe('end')
      expect(result.events[0].duration_ms).toBe(45000)
      expect(result.events[1].event_type).toBe('start')
    })
  })
})
