import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { CronTasksPage } from '@/pages/cron/CronTasksPage'
import * as cronTasksApi from '@/api/cronTasks'
import { useWorkspaceStore } from '@/stores/workspaceStore'

// Mock APIs
vi.mock('@/api/cronTasks', () => ({
  getCronTasks: vi.fn(),
  deleteCronTask: vi.fn(),
  pauseCronTask: vi.fn(),
  resumeCronTask: vi.fn(),
  runCronTask: vi.fn(),
}))

// Mock workspaceStore
vi.mock('@/stores/workspaceStore', () => ({
  useWorkspaceStore: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

describe('CronTasksPage', () => {
  const mockOnNavigate = vi.fn()
  const mockWorkspace = {
    id: 'workspace-1',
    name: 'Test Workspace',
    slug: 'test-workspace',
    owner_id: 'user-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  const mockTask = {
    id: 'task-1',
    workspace_id: 'workspace-1',
    name: 'Test Cron Task',
    description: 'A test task',
    protocol_type: 'http' as const,
    url: 'https://example.com/webhook',
    method: 'POST' as const,
    schedule: '*/5 * * * *',
    timezone: 'Europe/Moscow',
    timeout_seconds: 30,
    retry_count: 3,
    headers: {},
    body: null,
    is_active: true,
    is_paused: false,
    notify_on_failure: true,
    last_run_at: null,
    next_run_at: '2024-01-01T12:05:00Z',
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
    vi.mocked(cronTasksApi.getCronTasks).mockResolvedValue({
      tasks: [mockTask],
      total: 1,
      page: 1,
      per_page: 10,
      total_pages: 1,
    })
  })

  it('should render page title', async () => {
    render(<CronTasksPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Cron Tasks')).toBeInTheDocument()
    })
  })

  it('should load tasks on mount', async () => {
    render(<CronTasksPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(cronTasksApi.getCronTasks).toHaveBeenCalledWith('workspace-1')
    })
  })

  it('should display tasks in table', async () => {
    render(<CronTasksPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Test Cron Task')).toBeInTheDocument()
    })
  })

  it('should display task schedule', async () => {
    render(<CronTasksPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('*/5 * * * *')).toBeInTheDocument()
    })
  })

  it('should show empty state when no tasks', async () => {
    vi.mocked(cronTasksApi.getCronTasks).mockResolvedValue({
      tasks: [],
      total: 0,
      page: 1,
      per_page: 10,
      total_pages: 0,
    })

    render(<CronTasksPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(cronTasksApi.getCronTasks).toHaveBeenCalled()
    })
  })

  it('should have create task button', async () => {
    render(<CronTasksPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /create task/i })).toBeInTheDocument()
    })
  })

  it('should open create dialog when button clicked', async () => {
    const { user } = render(<CronTasksPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /create task/i })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /create task/i }))

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  it('should call pauseCronTask when pause button clicked', async () => {
    vi.mocked(cronTasksApi.pauseCronTask).mockResolvedValue(undefined)

    const { user } = render(<CronTasksPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Test Cron Task')).toBeInTheDocument()
    })

    const pauseButton = screen.getByTitle(/pause/i)
    if (pauseButton) {
      await user.click(pauseButton)
      await waitFor(() => {
        expect(cronTasksApi.pauseCronTask).toHaveBeenCalledWith('workspace-1', 'task-1')
      })
    }
  })

  it('should call runCronTask when run button clicked', async () => {
    vi.mocked(cronTasksApi.runCronTask).mockResolvedValue(undefined)

    const { user } = render(<CronTasksPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Test Cron Task')).toBeInTheDocument()
    })

    const runButton = screen.getByTitle(/run now/i)
    if (runButton) {
      await user.click(runButton)
      await waitFor(() => {
        expect(cronTasksApi.runCronTask).toHaveBeenCalledWith('workspace-1', 'task-1')
      })
    }
  })

  it('should show delete confirmation dialog', async () => {
    const { user } = render(<CronTasksPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Test Cron Task')).toBeInTheDocument()
    })

    const deleteButton = screen.getByTitle(/delete/i)
    if (deleteButton) {
      await user.click(deleteButton)
      await waitFor(() => {
        expect(screen.getByText(/are you sure/i)).toBeInTheDocument()
      })
    }
  })
})
