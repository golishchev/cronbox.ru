import { describe, it, expect, vi } from 'vitest'
import { translateApiError } from '../translateApiError'
import type { TFunction } from 'i18next'

describe('translateApiError', () => {
  const mockT: TFunction = vi.fn((key: string, params?: Record<string, unknown>) => {
    if (params) {
      let result = key
      Object.entries(params).forEach(([k, v]) => {
        result = result.replace(`{{${k}}}`, String(v))
      })
      return result
    }
    return key
  }) as unknown as TFunction

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('cron interval too frequent', () => {
    it('should translate cron interval error with 1 minute', () => {
      const message = 'Cron interval too frequent. Your plan allows minimum 1 minute interval'
      const result = translateApiError(message, mockT)

      expect(mockT).toHaveBeenCalledWith('apiErrors.cronIntervalTooFrequent', { minutes: 1 })
      expect(result).toBe('apiErrors.cronIntervalTooFrequent')
    })

    it('should translate cron interval error with 5 minutes', () => {
      const message = 'Cron interval too frequent. Your plan allows minimum 5 minute interval'
      const result = translateApiError(message, mockT)

      expect(mockT).toHaveBeenCalledWith('apiErrors.cronIntervalTooFrequent', { minutes: 5 })
      expect(result).toBe('apiErrors.cronIntervalTooFrequent')
    })

    it('should be case insensitive', () => {
      const message = 'CRON INTERVAL TOO FREQUENT. Your plan allows MINIMUM 10 MINUTE interval'
      const result = translateApiError(message, mockT)

      expect(mockT).toHaveBeenCalledWith('apiErrors.cronIntervalTooFrequent', { minutes: 10 })
      expect(result).toBe('apiErrors.cronIntervalTooFrequent')
    })
  })

  describe('cron task limit reached', () => {
    it('should translate task limit error with limit', () => {
      const message = 'Cron task limit reached. Your plan allows 10 cron tasks'
      const result = translateApiError(message, mockT)

      expect(mockT).toHaveBeenCalledWith('apiErrors.cronTaskLimitReached', { limit: 10 })
      expect(result).toBe('apiErrors.cronTaskLimitReached')
    })

    it('should handle large limits', () => {
      const message = 'Cron task limit reached. Your plan allows 1000 cron tasks'
      const result = translateApiError(message, mockT)

      expect(mockT).toHaveBeenCalledWith('apiErrors.cronTaskLimitReached', { limit: 1000 })
      expect(result).toBe('apiErrors.cronTaskLimitReached')
    })
  })

  describe('heartbeat interval too short', () => {
    it('should translate heartbeat interval error with minutes', () => {
      const message = 'Heartbeat interval too short. Your plan requires minimum 5 minute(s)'
      const result = translateApiError(message, mockT)

      expect(mockT).toHaveBeenCalledWith('apiErrors.heartbeatIntervalTooShort', { minutes: 5 })
      expect(result).toBe('apiErrors.heartbeatIntervalTooShort')
    })

    it('should be case insensitive', () => {
      const message = 'HEARTBEAT INTERVAL TOO SHORT. Your plan requires MINIMUM 10 MINUTE(S)'
      const result = translateApiError(message, mockT)

      expect(mockT).toHaveBeenCalledWith('apiErrors.heartbeatIntervalTooShort', { minutes: 10 })
      expect(result).toBe('apiErrors.heartbeatIntervalTooShort')
    })
  })

  describe('heartbeat limit reached', () => {
    it('should translate heartbeat limit error with limit', () => {
      const message = 'Heartbeat monitor limit reached. Your plan allows 5 heartbeat(s)'
      const result = translateApiError(message, mockT)

      expect(mockT).toHaveBeenCalledWith('apiErrors.heartbeatLimitReached', { limit: 5 })
      expect(result).toBe('apiErrors.heartbeatLimitReached')
    })

    it('should handle singular form', () => {
      const message = 'Heartbeat monitor limit reached. Your plan allows 1 heartbeat'
      const result = translateApiError(message, mockT)

      expect(mockT).toHaveBeenCalledWith('apiErrors.heartbeatLimitReached', { limit: 1 })
      expect(result).toBe('apiErrors.heartbeatLimitReached')
    })
  })

  describe('connection failed with DNS error', () => {
    it('should translate DNS resolution error', () => {
      const message = 'All connection attempts failed: nodename nor servname provided, or not known'
      const result = translateApiError(message, mockT)

      expect(mockT).toHaveBeenCalledWith('apiErrors.connectionFailedDnsError', {})
      expect(result).toBe('apiErrors.connectionFailedDnsError')
    })
  })

  describe('generic connection failed', () => {
    it('should translate generic connection error', () => {
      const message = 'All connection attempts failed'
      const result = translateApiError(message, mockT)

      expect(mockT).toHaveBeenCalledWith('apiErrors.connectionFailed', {})
      expect(result).toBe('apiErrors.connectionFailed')
    })

    it('should translate connection error with additional info', () => {
      const message = 'All connection attempts failed: timeout after 30 seconds'
      const result = translateApiError(message, mockT)

      // Should match the generic pattern, not DNS pattern
      expect(mockT).toHaveBeenCalledWith('apiErrors.connectionFailed', {})
      expect(result).toBe('apiErrors.connectionFailed')
    })
  })

  describe('unmatched messages', () => {
    it('should return original message if no pattern matches', () => {
      const message = 'Unknown error occurred'
      const result = translateApiError(message, mockT)

      expect(mockT).not.toHaveBeenCalled()
      expect(result).toBe('Unknown error occurred')
    })

    it('should return original message for empty string', () => {
      const result = translateApiError('', mockT)

      expect(mockT).not.toHaveBeenCalled()
      expect(result).toBe('')
    })

    it('should return original message for partial matches', () => {
      const message = 'Cron interval is fine'
      const result = translateApiError(message, mockT)

      expect(mockT).not.toHaveBeenCalled()
      expect(result).toBe('Cron interval is fine')
    })
  })

  describe('pattern priority', () => {
    it('should match DNS error before generic connection error', () => {
      const message = 'All connection attempts failed: nodename nor servname provided, or not known'
      const result = translateApiError(message, mockT)

      // DNS pattern should be matched, not generic connection pattern
      expect(mockT).toHaveBeenCalledWith('apiErrors.connectionFailedDnsError', {})
      expect(result).toBe('apiErrors.connectionFailedDnsError')
    })
  })
})
