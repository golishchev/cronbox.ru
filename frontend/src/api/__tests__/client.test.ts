import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import { apiClient, getErrorMessage } from '../client'

describe('apiClient', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('configuration', () => {
    it('should have correct base URL', () => {
      expect(apiClient.defaults.baseURL).toBe('/v1')
    })

    it('should have JSON content type', () => {
      expect(apiClient.defaults.headers['Content-Type']).toBe('application/json')
    })
  })

  describe('request interceptor', () => {
    it('should add authorization header when token exists', async () => {
      localStorage.setItem('access_token', 'test-token')

      // Get request config through interceptors
      const config = await apiClient.interceptors.request.handlers[0].fulfilled({
        headers: {},
      })

      expect(config.headers.Authorization).toBe('Bearer test-token')
    })

    it('should not add authorization header when no token', async () => {
      const config = await apiClient.interceptors.request.handlers[0].fulfilled({
        headers: {},
      })

      expect(config.headers.Authorization).toBeUndefined()
    })
  })
})

describe('getErrorMessage', () => {
  it('should extract detail from axios error response', () => {
    const axiosError = {
      isAxiosError: true,
      response: {
        data: { detail: 'Custom error message' },
      },
      message: 'Request failed',
    }
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(true)

    const result = getErrorMessage(axiosError)

    expect(result).toBe('Custom error message')
  })

  it('should fallback to error message if no detail', () => {
    const axiosError = {
      isAxiosError: true,
      response: {
        data: {},
      },
      message: 'Request failed with status 500',
    }
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(true)

    const result = getErrorMessage(axiosError)

    expect(result).toBe('Request failed with status 500')
  })

  it('should handle Error instances', () => {
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(false)
    const error = new Error('Standard error')

    const result = getErrorMessage(error)

    expect(result).toBe('Standard error')
  })

  it('should return default message for unknown errors', () => {
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(false)

    const result = getErrorMessage('string error')

    expect(result).toBe('An unexpected error occurred')
  })

  it('should return default message for null/undefined', () => {
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(false)

    expect(getErrorMessage(null)).toBe('An unexpected error occurred')
    expect(getErrorMessage(undefined)).toBe('An unexpected error occurred')
  })
})
