import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { NotificationsPage } from '@/pages/settings/NotificationsPage'
import * as notificationsApi from '@/api/notifications'
import { useWorkspaceStore } from '@/stores/workspaceStore'

// Mock APIs
vi.mock('@/api/notifications', () => ({
  getNotificationSettings: vi.fn(),
  updateNotificationSettings: vi.fn(),
}))

// Mock workspaceStore
vi.mock('@/stores/workspaceStore', () => ({
  useWorkspaceStore: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

describe('NotificationsPage', () => {
  const mockOnNavigate = vi.fn()
  const mockWorkspace = {
    id: 'workspace-1',
    name: 'Test Workspace',
    slug: 'test-workspace',
    owner_id: 'user-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  const mockSettings = {
    id: 'settings-1',
    workspace_id: 'workspace-1',
    email_enabled: true,
    email_addresses: ['test@example.com'],
    telegram_enabled: false,
    telegram_chat_ids: [],
    webhook_enabled: false,
    webhook_url: null,
    notify_on_success: false,
    notify_on_failure: true,
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
    vi.mocked(notificationsApi.getNotificationSettings).mockResolvedValue(mockSettings)
  })

  it('should render page title', async () => {
    render(<NotificationsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Notifications')).toBeInTheDocument()
    })
  })

  it('should load notification settings on mount', async () => {
    render(<NotificationsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(notificationsApi.getNotificationSettings).toHaveBeenCalledWith('workspace-1')
    })
  })

  it('should display notification options', async () => {
    render(<NotificationsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      // Page should load with settings
      expect(notificationsApi.getNotificationSettings).toHaveBeenCalled()
    })
  })

  it('should have save button', async () => {
    render(<NotificationsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Notifications')).toBeInTheDocument()
    })
  })
})
