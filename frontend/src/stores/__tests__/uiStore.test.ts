import { describe, it, expect, beforeEach } from 'vitest'
import { act } from '@testing-library/react'
import { useUIStore } from '../uiStore'

describe('uiStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useUIStore.setState({
      sidebarCollapsed: false,
      theme: 'system',
    })
  })

  describe('initial state', () => {
    it('should have sidebar expanded by default', () => {
      const state = useUIStore.getState()

      expect(state.sidebarCollapsed).toBe(false)
    })

    it('should have system theme by default', () => {
      const state = useUIStore.getState()

      expect(state.theme).toBe('system')
    })
  })

  describe('setSidebarCollapsed', () => {
    it('should set sidebar to collapsed', () => {
      act(() => {
        useUIStore.getState().setSidebarCollapsed(true)
      })

      expect(useUIStore.getState().sidebarCollapsed).toBe(true)
    })

    it('should set sidebar to expanded', () => {
      useUIStore.setState({ sidebarCollapsed: true })

      act(() => {
        useUIStore.getState().setSidebarCollapsed(false)
      })

      expect(useUIStore.getState().sidebarCollapsed).toBe(false)
    })
  })

  describe('toggleSidebar', () => {
    it('should toggle sidebar from expanded to collapsed', () => {
      useUIStore.setState({ sidebarCollapsed: false })

      act(() => {
        useUIStore.getState().toggleSidebar()
      })

      expect(useUIStore.getState().sidebarCollapsed).toBe(true)
    })

    it('should toggle sidebar from collapsed to expanded', () => {
      useUIStore.setState({ sidebarCollapsed: true })

      act(() => {
        useUIStore.getState().toggleSidebar()
      })

      expect(useUIStore.getState().sidebarCollapsed).toBe(false)
    })

    it('should toggle multiple times correctly', () => {
      useUIStore.setState({ sidebarCollapsed: false })

      act(() => {
        useUIStore.getState().toggleSidebar()
      })
      expect(useUIStore.getState().sidebarCollapsed).toBe(true)

      act(() => {
        useUIStore.getState().toggleSidebar()
      })
      expect(useUIStore.getState().sidebarCollapsed).toBe(false)

      act(() => {
        useUIStore.getState().toggleSidebar()
      })
      expect(useUIStore.getState().sidebarCollapsed).toBe(true)
    })
  })

  describe('setTheme', () => {
    it('should set theme to light', () => {
      act(() => {
        useUIStore.getState().setTheme('light')
      })

      expect(useUIStore.getState().theme).toBe('light')
    })

    it('should set theme to dark', () => {
      act(() => {
        useUIStore.getState().setTheme('dark')
      })

      expect(useUIStore.getState().theme).toBe('dark')
    })

    it('should set theme to system', () => {
      useUIStore.setState({ theme: 'dark' })

      act(() => {
        useUIStore.getState().setTheme('system')
      })

      expect(useUIStore.getState().theme).toBe('system')
    })
  })
})
