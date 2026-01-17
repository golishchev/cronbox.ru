import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { HeartbeatsPage } from '@/pages/heartbeats/HeartbeatsPage'
import * as heartbeatsApi from '@/api/heartbeats'
import { useWorkspaceStore } from '@/stores/workspaceStore'

// Mock APIs
vi.mock('@/api/heartbeats', () => ({
  getHeartbeats: vi.fn(),
  deleteHeartbeat: vi.fn(),
  pauseHeartbeat: vi.fn(),
  resumeHeartbeat: vi.fn(),
}))

// Mock workspaceStore
vi.mock('@/stores/workspaceStore', () => ({
  useWorkspaceStore: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

describe('HeartbeatsPage', () => {
  const mockOnNavigate = vi.fn()
  const mockWorkspace = {
    id: 'workspace-1',
    name: 'Test Workspace',
    slug: 'test-workspace',
    owner_id: 'user-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  const mockHeartbeat = {
    id: 'heartbeat-1',
    workspace_id: 'workspace-1',
    name: 'Test Heartbeat',
    description: 'A test heartbeat monitor',
    ping_token: 'abc123',
    ping_url: 'https://cronbox.ru/ping/abc123',
    expected_interval: 3600,
    grace_period: 600,
    status: 'healthy' as const,
    is_paused: false,
    last_ping_at: '2024-01-01T11:00:00Z',
    next_expected_at: '2024-01-01T12:10:00Z',
    consecutive_misses: 0,
    alert_sent: false,
    notify_on_late: true,
    notify_on_recovery: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useWorkspaceStore).mockReturnValue({
      currentWorkspace: mockWorkspace,
      workspaces: [mockWorkspace],
      setWorkspaces: vi.fn(),
      setCurrentWorkspace: vi.fn(),
      addWorkspace: vi.fn(),
      updateWorkspace: vi.fn(),
      removeWorkspace: vi.fn(),
      clearWorkspaces: vi.fn(),
    })
    vi.mocked(heartbeatsApi.getHeartbeats).mockResolvedValue({
      heartbeats: [mockHeartbeat],
      pagination: {
        page: 1,
        limit: 20,
        total: 1,
        total_pages: 1,
      },
    })
  })

  it('should render page title', async () => {
    render(<HeartbeatsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Heartbeats')).toBeInTheDocument()
    })
  })

  it('should load heartbeats on mount', async () => {
    render(<HeartbeatsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(heartbeatsApi.getHeartbeats).toHaveBeenCalledWith('workspace-1')
    })
  })

  it('should display heartbeats in table', async () => {
    render(<HeartbeatsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Test Heartbeat')).toBeInTheDocument()
    })
  })

  it('should display heartbeat status badge', async () => {
    render(<HeartbeatsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Healthy')).toBeInTheDocument()
    })
  })

  it('should display ping URL', async () => {
    render(<HeartbeatsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText(/abc123/)).toBeInTheDocument()
    })
  })

  it('should show empty state when no heartbeats', async () => {
    vi.mocked(heartbeatsApi.getHeartbeats).mockResolvedValue({
      heartbeats: [],
      pagination: {
        page: 1,
        limit: 20,
        total: 0,
        total_pages: 0,
      },
    })

    render(<HeartbeatsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(heartbeatsApi.getHeartbeats).toHaveBeenCalled()
    })

    await waitFor(() => {
      expect(screen.getByText(/no heartbeat monitors yet/i)).toBeInTheDocument()
    })
  })

  it('should have create heartbeat button', async () => {
    render(<HeartbeatsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /create heartbeat/i })).toBeInTheDocument()
    })
  })

  it('should open create dialog when button clicked', async () => {
    const { user } = render(<HeartbeatsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /create heartbeat/i })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /create heartbeat/i }))

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  it('should call pauseHeartbeat when pause button clicked', async () => {
    vi.mocked(heartbeatsApi.pauseHeartbeat).mockResolvedValue(undefined)

    const { user } = render(<HeartbeatsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Test Heartbeat')).toBeInTheDocument()
    })

    const pauseButton = screen.getByTitle(/pause/i)
    if (pauseButton) {
      await user.click(pauseButton)
      await waitFor(() => {
        expect(heartbeatsApi.pauseHeartbeat).toHaveBeenCalledWith('workspace-1', 'heartbeat-1')
      })
    }
  })

  it('should show delete confirmation dialog', async () => {
    const { user } = render(<HeartbeatsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Test Heartbeat')).toBeInTheDocument()
    })

    const deleteButton = screen.getByTitle(/delete/i)
    if (deleteButton) {
      await user.click(deleteButton)
      await waitFor(() => {
        expect(screen.getByText(/are you sure/i)).toBeInTheDocument()
      })
    }
  })

  it('should display interval formatted correctly', async () => {
    render(<HeartbeatsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      // 3600 seconds = 1h
      expect(screen.getByText('1h')).toBeInTheDocument()
    })
  })

  it('should display waiting status for new heartbeat', async () => {
    vi.mocked(heartbeatsApi.getHeartbeats).mockResolvedValue({
      heartbeats: [{
        ...mockHeartbeat,
        status: 'waiting' as const,
        last_ping_at: null,
      }],
      pagination: {
        page: 1,
        limit: 20,
        total: 1,
        total_pages: 1,
      },
    })

    render(<HeartbeatsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Waiting')).toBeInTheDocument()
      expect(screen.getByText('Never pinged')).toBeInTheDocument()
    })
  })

  it('should display late status for overdue heartbeat', async () => {
    vi.mocked(heartbeatsApi.getHeartbeats).mockResolvedValue({
      heartbeats: [{
        ...mockHeartbeat,
        status: 'late' as const,
        consecutive_misses: 1,
      }],
      pagination: {
        page: 1,
        limit: 20,
        total: 1,
        total_pages: 1,
      },
    })

    render(<HeartbeatsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Late')).toBeInTheDocument()
    })
  })

  it('should display dead status for dead heartbeat', async () => {
    vi.mocked(heartbeatsApi.getHeartbeats).mockResolvedValue({
      heartbeats: [{
        ...mockHeartbeat,
        status: 'dead' as const,
        consecutive_misses: 3,
      }],
      pagination: {
        page: 1,
        limit: 20,
        total: 1,
        total_pages: 1,
      },
    })

    render(<HeartbeatsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Dead')).toBeInTheDocument()
    })
  })
})
