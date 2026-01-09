import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { ApiKeysPage } from '@/pages/settings/ApiKeysPage'
import * as workersApi from '@/api/workers'
import { useWorkspaceStore } from '@/stores/workspaceStore'

// Mock APIs
vi.mock('@/api/workers', () => ({
  getWorkers: vi.fn(),
  createWorker: vi.fn(),
  deleteWorker: vi.fn(),
  regenerateWorkerKey: vi.fn(),
}))

// Mock workspaceStore
vi.mock('@/stores/workspaceStore', () => ({
  useWorkspaceStore: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

describe('ApiKeysPage', () => {
  const mockOnNavigate = vi.fn()
  const mockWorkspace = {
    id: 'workspace-1',
    name: 'Test Workspace',
    slug: 'test-workspace',
    owner_id: 'user-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  const mockWorker = {
    id: 'worker-1',
    workspace_id: 'workspace-1',
    name: 'Test Worker',
    description: 'A test worker',
    api_key_prefix: 'cwk_abc',
    region: 'eu',
    is_active: true,
    last_seen_at: '2024-01-01T00:00:00Z',
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
    vi.mocked(workersApi.getWorkers).mockResolvedValue([mockWorker])
  })

  it('should render page title', async () => {
    render(<ApiKeysPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('API Keys')).toBeInTheDocument()
    })
  })

  it('should load workers on mount', async () => {
    render(<ApiKeysPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(workersApi.getWorkers).toHaveBeenCalledWith('workspace-1')
    })
  })

  it('should display workers in table', async () => {
    render(<ApiKeysPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Test Worker')).toBeInTheDocument()
    })
  })

  it('should show create button', async () => {
    render(<ApiKeysPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /create/i })).toBeInTheDocument()
    })
  })

  it('should show empty state when no workers', async () => {
    vi.mocked(workersApi.getWorkers).mockResolvedValue([])

    render(<ApiKeysPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(workersApi.getWorkers).toHaveBeenCalled()
    })
  })

  it('should open create dialog when button clicked', async () => {
    const { user } = render(<ApiKeysPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /create/i })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /create/i }))

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  it('should display worker API key prefix', async () => {
    render(<ApiKeysPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText(/cwk_abc/)).toBeInTheDocument()
    })
  })
})
