import type { TFunction } from 'i18next'

interface ErrorPattern {
  pattern: RegExp
  key: string
  extractParams?: (match: RegExpMatchArray) => Record<string, string | number>
}

const errorPatterns: ErrorPattern[] = [
  {
    pattern: /Cron interval too frequent.*minimum (\d+) minute/i,
    key: 'apiErrors.cronIntervalTooFrequent',
    extractParams: (match) => ({ minutes: parseInt(match[1], 10) }),
  },
  {
    pattern: /Cron task limit reached.*allows (\d+) cron task/i,
    key: 'apiErrors.cronTaskLimitReached',
    extractParams: (match) => ({ limit: parseInt(match[1], 10) }),
  },
  {
    pattern: /All connection attempts failed.*nodename nor servname provided/i,
    key: 'apiErrors.connectionFailedDnsError',
  },
  {
    pattern: /All connection attempts failed/i,
    key: 'apiErrors.connectionFailed',
  },
]

/**
 * Translates API error messages using i18n.
 * Returns translated message if pattern matches, otherwise returns original message.
 */
export function translateApiError(message: string, t: TFunction): string {
  for (const { pattern, key, extractParams } of errorPatterns) {
    const match = message.match(pattern)
    if (match) {
      const params = extractParams ? extractParams(match) : {}
      return t(key, params)
    }
  }
  return message
}
