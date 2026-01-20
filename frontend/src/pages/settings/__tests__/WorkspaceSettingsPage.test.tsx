import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { WorkspaceSettingsPage } from '@/pages/settings/WorkspaceSettingsPage'
import * as workspacesApi from '@/api/workspaces'
import * as notificationsApi from '@/api/notifications'
import { useWorkspaceStore } from '@/stores/workspaceStore'

// Mock APIs
vi.mock('@/api/workspaces', () => ({
  updateWorkspace: vi.fn(),
}))

vi.mock('@/api/notifications', () => ({
  getNotificationSettings: vi.fn(),
  updateNotificationSettings: vi.fn(),
  sendTestNotification: vi.fn(),
}))

// Mock workspaceStore
vi.mock('@/stores/workspaceStore', () => ({
  useWorkspaceStore: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

describe('WorkspaceSettingsPage', () => {
  const mockWorkspace = {
    id: 'workspace-1',
    name: 'Test Workspace',
    slug: 'test-workspace',
    owner_id: 'user-1',
    default_timezone: 'Europe/Moscow',
    cron_tasks_count: 0,
    delayed_tasks_this_month: 0,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  const mockNavigate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useWorkspaceStore).mockReturnValue({
      currentWorkspace: mockWorkspace,
      updateWorkspace: vi.fn(),
      workspaces: [mockWorkspace],
      setWorkspaces: vi.fn(),
      setCurrentWorkspace: vi.fn(),
      isLoading: false,
      setLoading: vi.fn(),
      addWorkspace: vi.fn(),
      removeWorkspace: vi.fn(),
    })
  })

  it('renders workspace settings page with title', () => {
    render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

    expect(screen.getByText('Workspace Settings')).toBeInTheDocument()
    expect(screen.getByText('Manage settings for the current workspace')).toBeInTheDocument()
  })

  it('displays workspace name and slug', () => {
    render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

    expect(screen.getByDisplayValue('Test Workspace')).toBeInTheDocument()
    expect(screen.getByDisplayValue('test-workspace')).toBeInTheDocument()
  })

  it('displays timezone section', () => {
    render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

    expect(screen.getByText('Timezone')).toBeInTheDocument()
    expect(screen.getByText('Timezone is used for displaying time in notifications')).toBeInTheDocument()
  })

  it('displays general information section', () => {
    render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

    expect(screen.getByText('General Information')).toBeInTheDocument()
  })

  it('shows no workspace message when workspace is null', () => {
    vi.mocked(useWorkspaceStore).mockReturnValue({
      currentWorkspace: null,
      updateWorkspace: vi.fn(),
      workspaces: [],
      setWorkspaces: vi.fn(),
      setCurrentWorkspace: vi.fn(),
      isLoading: false,
      setLoading: vi.fn(),
      addWorkspace: vi.fn(),
      removeWorkspace: vi.fn(),
    })

    render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

    expect(screen.getByText('No workspace selected')).toBeInTheDocument()
  })

  it('slug field is disabled', () => {
    render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

    const slugInput = screen.getByDisplayValue('test-workspace')
    expect(slugInput).toBeDisabled()
  })

  it('shows slug description hint', () => {
    render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

    expect(screen.getByText('Identifier cannot be changed after creation')).toBeInTheDocument()
  })

  it('auto-saves when name changes', async () => {
    const mockUpdateWorkspace = vi.fn().mockResolvedValue({
      ...mockWorkspace,
      name: 'New Workspace Name',
    })
    vi.mocked(workspacesApi.updateWorkspace).mockImplementation(mockUpdateWorkspace)

    const mockStoreUpdate = vi.fn()
    vi.mocked(useWorkspaceStore).mockReturnValue({
      currentWorkspace: mockWorkspace,
      updateWorkspace: mockStoreUpdate,
      workspaces: [mockWorkspace],
      setWorkspaces: vi.fn(),
      setCurrentWorkspace: vi.fn(),
      isLoading: false,
      setLoading: vi.fn(),
      addWorkspace: vi.fn(),
      removeWorkspace: vi.fn(),
    })

    const { user } = render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

    // Wait for initialization
    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Workspace')).toBeInTheDocument()
    })

    const nameInput = screen.getByDisplayValue('Test Workspace')
    await user.clear(nameInput)
    await user.type(nameInput, 'New Workspace Name')

    // Wait for debounced auto-save
    await waitFor(() => {
      expect(mockUpdateWorkspace).toHaveBeenCalledWith('workspace-1', {
        name: 'New Workspace Name',
      })
    }, { timeout: 1000 })
  })

  it('displays error message on API failure', async () => {
    vi.mocked(workspacesApi.updateWorkspace).mockRejectedValue(new Error('Network error'))

    const { user } = render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

    // Wait for initialization
    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Workspace')).toBeInTheDocument()
    })

    const nameInput = screen.getByDisplayValue('Test Workspace')
    await user.clear(nameInput)
    await user.type(nameInput, 'New Workspace Name')

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument()
    }, { timeout: 1000 })
  })

  it('updates workspace in store after successful auto-save', async () => {
    const updatedWorkspace = {
      ...mockWorkspace,
      name: 'New Workspace Name',
    }
    vi.mocked(workspacesApi.updateWorkspace).mockResolvedValue(updatedWorkspace)

    const mockStoreUpdate = vi.fn()
    vi.mocked(useWorkspaceStore).mockReturnValue({
      currentWorkspace: mockWorkspace,
      updateWorkspace: mockStoreUpdate,
      workspaces: [mockWorkspace],
      setWorkspaces: vi.fn(),
      setCurrentWorkspace: vi.fn(),
      isLoading: false,
      setLoading: vi.fn(),
      addWorkspace: vi.fn(),
      removeWorkspace: vi.fn(),
    })

    const { user } = render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

    // Wait for initialization
    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Workspace')).toBeInTheDocument()
    })

    const nameInput = screen.getByDisplayValue('Test Workspace')
    await user.clear(nameInput)
    await user.type(nameInput, 'New Workspace Name')

    await waitFor(() => {
      expect(mockStoreUpdate).toHaveBeenCalledWith(updatedWorkspace)
    }, { timeout: 1000 })
  })

  describe('Notifications Section', () => {
    const mockNotificationSettings = {
      id: 'notification-1',
      workspace_id: 'workspace-1',
      telegram_enabled: false,
      telegram_chat_ids: [],
      email_enabled: false,
      email_addresses: [],
      webhook_enabled: false,
      webhook_url: null,
      webhook_secret: null,
      notify_on_failure: true,
      notify_on_recovery: true,
      notify_on_success: false,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    }

    beforeEach(() => {
      vi.mocked(notificationsApi.getNotificationSettings).mockResolvedValue(mockNotificationSettings)
      vi.mocked(notificationsApi.updateNotificationSettings).mockResolvedValue(mockNotificationSettings)
    })

    it('loads notification settings on mount', async () => {
      render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

      await waitFor(() => {
        expect(notificationsApi.getNotificationSettings).toHaveBeenCalledWith('workspace-1')
      })
    })

    it('displays notifications section header', async () => {
      render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

      await waitFor(() => {
        expect(screen.getByText('Notifications')).toBeInTheDocument()
      })
    })

    it('displays notification events section', async () => {
      render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

      await waitFor(() => {
        expect(screen.getByText('Notification Events')).toBeInTheDocument()
      })
    })

    it('displays telegram section', async () => {
      render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

      await waitFor(() => {
        expect(screen.getByText('Telegram')).toBeInTheDocument()
      })
    })

    it('displays email section', async () => {
      render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

      await waitFor(() => {
        expect(screen.getByText('Email')).toBeInTheDocument()
      })
    })

    it('displays webhook section', async () => {
      render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

      await waitFor(() => {
        expect(screen.getByText('Webhook')).toBeInTheDocument()
      })
    })

    it('displays task failure notification option', async () => {
      render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

      await waitFor(() => {
        expect(screen.getByText('Task Failure')).toBeInTheDocument()
      })
    })

    it('displays task recovery notification option', async () => {
      render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

      await waitFor(() => {
        expect(screen.getByText('Task Recovery')).toBeInTheDocument()
      })
    })

    it('displays task success notification option', async () => {
      render(<WorkspaceSettingsPage onNavigate={mockNavigate} />)

      await waitFor(() => {
        expect(screen.getByText('Task Success')).toBeInTheDocument()
      })
    })
  })
})
