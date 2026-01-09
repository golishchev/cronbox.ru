import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useToast, toast, reducer } from '../use-toast'

describe('use-toast', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('reducer', () => {
    const initialState = { toasts: [] }

    it('should add a toast with ADD_TOAST action', () => {
      const newToast = { id: '1', title: 'Test', open: true }
      const action = { type: 'ADD_TOAST' as const, toast: newToast }

      const result = reducer(initialState, action)

      expect(result.toasts).toHaveLength(1)
      expect(result.toasts[0]).toEqual(newToast)
    })

    it('should limit toasts to TOAST_LIMIT (3)', () => {
      let state = initialState

      for (let i = 0; i < 5; i++) {
        state = reducer(state, {
          type: 'ADD_TOAST',
          toast: { id: String(i), title: `Toast ${i}`, open: true },
        })
      }

      expect(state.toasts).toHaveLength(3)
      // Most recent toasts should be first
      expect(state.toasts[0].id).toBe('4')
      expect(state.toasts[1].id).toBe('3')
      expect(state.toasts[2].id).toBe('2')
    })

    it('should update a toast with UPDATE_TOAST action', () => {
      const state = {
        toasts: [{ id: '1', title: 'Original', open: true }],
      }
      const action = {
        type: 'UPDATE_TOAST' as const,
        toast: { id: '1', title: 'Updated' },
      }

      const result = reducer(state, action)

      expect(result.toasts[0].title).toBe('Updated')
      expect(result.toasts[0].open).toBe(true)
    })

    it('should not update non-existing toast', () => {
      const state = {
        toasts: [{ id: '1', title: 'Original', open: true }],
      }
      const action = {
        type: 'UPDATE_TOAST' as const,
        toast: { id: '999', title: 'Updated' },
      }

      const result = reducer(state, action)

      expect(result.toasts[0].title).toBe('Original')
    })

    it('should dismiss a specific toast with DISMISS_TOAST action', () => {
      const state = {
        toasts: [
          { id: '1', title: 'Toast 1', open: true },
          { id: '2', title: 'Toast 2', open: true },
        ],
      }
      const action = { type: 'DISMISS_TOAST' as const, toastId: '1' }

      const result = reducer(state, action)

      expect(result.toasts[0].open).toBe(false)
      expect(result.toasts[1].open).toBe(true)
    })

    it('should dismiss all toasts when no toastId provided', () => {
      const state = {
        toasts: [
          { id: '1', title: 'Toast 1', open: true },
          { id: '2', title: 'Toast 2', open: true },
        ],
      }
      const action = { type: 'DISMISS_TOAST' as const }

      const result = reducer(state, action)

      expect(result.toasts[0].open).toBe(false)
      expect(result.toasts[1].open).toBe(false)
    })

    it('should remove a specific toast with REMOVE_TOAST action', () => {
      const state = {
        toasts: [
          { id: '1', title: 'Toast 1', open: true },
          { id: '2', title: 'Toast 2', open: true },
        ],
      }
      const action = { type: 'REMOVE_TOAST' as const, toastId: '1' }

      const result = reducer(state, action)

      expect(result.toasts).toHaveLength(1)
      expect(result.toasts[0].id).toBe('2')
    })

    it('should remove all toasts when no toastId provided to REMOVE_TOAST', () => {
      const state = {
        toasts: [
          { id: '1', title: 'Toast 1', open: true },
          { id: '2', title: 'Toast 2', open: true },
        ],
      }
      const action = { type: 'REMOVE_TOAST' as const }

      const result = reducer(state, action)

      expect(result.toasts).toHaveLength(0)
    })
  })

  describe('toast function', () => {
    it('should create a toast and return id, dismiss, update functions', () => {
      const result = toast({ title: 'Test Toast' })

      expect(result.id).toBeDefined()
      expect(typeof result.dismiss).toBe('function')
      expect(typeof result.update).toBe('function')
    })

    it('should generate unique ids for each toast', () => {
      const toast1 = toast({ title: 'Toast 1' })
      const toast2 = toast({ title: 'Toast 2' })
      const toast3 = toast({ title: 'Toast 3' })

      expect(toast1.id).not.toBe(toast2.id)
      expect(toast2.id).not.toBe(toast3.id)
      expect(toast1.id).not.toBe(toast3.id)
    })
  })

  describe('useToast hook', () => {
    it('should return toasts array and toast function', () => {
      const { result } = renderHook(() => useToast())

      expect(result.current.toasts).toBeDefined()
      expect(Array.isArray(result.current.toasts)).toBe(true)
      expect(typeof result.current.toast).toBe('function')
      expect(typeof result.current.dismiss).toBe('function')
    })

    it('should add toast when toast function is called', () => {
      const { result } = renderHook(() => useToast())
      const initialLength = result.current.toasts.length

      act(() => {
        result.current.toast({ title: 'New Toast' })
      })

      // Toast should be added (may be limited by TOAST_LIMIT)
      expect(result.current.toasts.length).toBeGreaterThanOrEqual(1)
      expect(result.current.toasts.some((t) => t.title === 'New Toast')).toBe(true)
    })

    it('should cleanup listener on unmount', () => {
      const { unmount } = renderHook(() => useToast())

      // Should not throw when unmounting
      expect(() => unmount()).not.toThrow()
    })
  })
})
