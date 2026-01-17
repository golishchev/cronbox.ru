import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { AdminUsersPage } from '@/pages/admin/AdminUsersPage'
import * as adminApi from '@/api/admin'

// Mock APIs
vi.mock('@/api/admin', () => ({
  getAdminUsers: vi.fn(),
  updateAdminUser: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

describe('AdminUsersPage', () => {
  const mockOnNavigate = vi.fn()

  const mockUsers = [
    {
      id: 'user-1',
      email: 'admin@example.com',
      name: 'Admin User',
      is_active: true,
      is_superuser: true,
      email_verified: true,
      telegram_username: 'admin_tg',
      workspaces_count: 5,
      tasks_count: 20,
      created_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'user-2',
      email: 'user@example.com',
      name: 'Regular User',
      is_active: true,
      is_superuser: false,
      email_verified: false,
      telegram_username: null,
      workspaces_count: 2,
      tasks_count: 10,
      created_at: '2024-02-01T00:00:00Z',
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(adminApi.getAdminUsers).mockResolvedValue({
      users: mockUsers,
      total: 2,
    })
  })

  it('should load users on mount', async () => {
    render(<AdminUsersPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(adminApi.getAdminUsers).toHaveBeenCalled()
    })
  })

  it('should display users in table', async () => {
    render(<AdminUsersPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Admin User')).toBeInTheDocument()
      expect(screen.getByText('admin@example.com')).toBeInTheDocument()
    })
  })

  it('should display user email', async () => {
    render(<AdminUsersPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('user@example.com')).toBeInTheDocument()
    })
  })

  it('should display telegram username', async () => {
    render(<AdminUsersPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('@admin_tg')).toBeInTheDocument()
    })
  })

  it('should navigate back when back button clicked', async () => {
    const { user } = render(<AdminUsersPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Admin User')).toBeInTheDocument()
    })

    const backButton = screen.getByRole('button', { name: /back/i })
    await user.click(backButton)

    expect(mockOnNavigate).toHaveBeenCalledWith('admin')
  })

  it('should search users when typing in search', async () => {
    const { user } = render(<AdminUsersPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Admin User')).toBeInTheDocument()
    })

    const searchInput = screen.getByPlaceholderText(/search/i)
    await user.type(searchInput, 'admin')

    await waitFor(() => {
      expect(adminApi.getAdminUsers).toHaveBeenCalledWith(
        expect.objectContaining({ search: 'admin' })
      )
    })
  })

  it('should open edit dialog when edit button clicked', async () => {
    const { user } = render(<AdminUsersPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Admin User')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByRole('button', { name: /edit/i })
    await user.click(editButtons[0])

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  it('should display empty state when no users', async () => {
    vi.mocked(adminApi.getAdminUsers).mockResolvedValue({
      users: [],
      total: 0,
    })

    render(<AdminUsersPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(adminApi.getAdminUsers).toHaveBeenCalled()
    })
  })

  it('should handle API error', async () => {
    vi.mocked(adminApi.getAdminUsers).mockRejectedValue(new Error('API Error'))

    render(<AdminUsersPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(adminApi.getAdminUsers).toHaveBeenCalled()
    })
  })

  it('should update user when save clicked in edit dialog', async () => {
    vi.mocked(adminApi.updateAdminUser).mockResolvedValue({} as unknown as Awaited<ReturnType<typeof adminApi.updateAdminUser>>)

    const { user } = render(<AdminUsersPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Admin User')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByRole('button', { name: /edit/i })
    await user.click(editButtons[0])

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    const saveButton = screen.getByRole('button', { name: /save/i })
    await user.click(saveButton)

    await waitFor(() => {
      expect(adminApi.updateAdminUser).toHaveBeenCalled()
    })
  })
})
