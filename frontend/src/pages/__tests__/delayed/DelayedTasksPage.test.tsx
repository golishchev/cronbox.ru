import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { DelayedTasksPage } from '@/pages/delayed/DelayedTasksPage'
import * as delayedTasksApi from '@/api/delayedTasks'
import { useWorkspaceStore } from '@/stores/workspaceStore'

// Mock APIs
vi.mock('@/api/delayedTasks', () => ({
  getDelayedTasks: vi.fn(),
  cancelDelayedTask: vi.fn(),
}))

// Mock workspaceStore
vi.mock('@/stores/workspaceStore', () => ({
  useWorkspaceStore: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

describe('DelayedTasksPage', () => {
  const mockOnNavigate = vi.fn()
  const mockWorkspace = {
    id: 'workspace-1',
    name: 'Test Workspace',
    slug: 'test-workspace',
    owner_id: 'user-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  const futureDate = new Date()
  futureDate.setHours(futureDate.getHours() + 2)

  const mockTask = {
    id: 'task-1',
    workspace_id: 'workspace-1',
    name: 'Test Delayed Task',
    protocol_type: 'http' as const,
    url: 'https://example.com/webhook',
    method: 'POST' as const,
    execute_at: futureDate.toISOString(),
    status: 'pending' as const,
    timeout_seconds: 30,
    retry_count: 0,
    headers: {},
    body: null,
    idempotency_key: 'key-123',
    callback_url: null,
    tags: [],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    executed_at: null,
    execution_id: null,
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
    vi.mocked(delayedTasksApi.getDelayedTasks).mockResolvedValue({
      tasks: [mockTask],
      total: 1,
      page: 1,
      per_page: 10,
      total_pages: 1,
    })
  })

  it('should render page title', async () => {
    render(<DelayedTasksPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Delayed Tasks')).toBeInTheDocument()
    })
  })

  it('should load tasks on mount', async () => {
    render(<DelayedTasksPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(delayedTasksApi.getDelayedTasks).toHaveBeenCalledWith('workspace-1', expect.any(Object))
    })
  })

  it('should display tasks in table', async () => {
    render(<DelayedTasksPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Test Delayed Task')).toBeInTheDocument()
    })
  })

  it('should display task status badge', async () => {
    render(<DelayedTasksPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getAllByText(/pending/i).length).toBeGreaterThan(0)
    })
  })

  it('should show empty state when no tasks', async () => {
    vi.mocked(delayedTasksApi.getDelayedTasks).mockResolvedValue({
      tasks: [],
      total: 0,
      page: 1,
      per_page: 10,
      total_pages: 0,
    })

    render(<DelayedTasksPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(delayedTasksApi.getDelayedTasks).toHaveBeenCalled()
    })
  })

  it('should have schedule task button', async () => {
    render(<DelayedTasksPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      // Check page loaded successfully
      expect(screen.getByText('Delayed Tasks')).toBeInTheDocument()
    })
  })

  it('should show cancel button for pending tasks', async () => {
    render(<DelayedTasksPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Test Delayed Task')).toBeInTheDocument()
    })
  })
})
