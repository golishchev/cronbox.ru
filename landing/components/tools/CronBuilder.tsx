'use client'

import { useState, useEffect, useCallback } from 'react'
import cronstrue from 'cronstrue/i18n'

interface PresetSchedule {
  label: string
  value: string
  category: 'frequent' | 'daily' | 'weekly' | 'monthly'
}

const PRESET_SCHEDULES: PresetSchedule[] = [
  // Frequent
  { label: 'Каждую минуту', value: '* * * * *', category: 'frequent' },
  { label: 'Каждые 5 минут', value: '*/5 * * * *', category: 'frequent' },
  { label: 'Каждые 10 минут', value: '*/10 * * * *', category: 'frequent' },
  { label: 'Каждые 15 минут', value: '*/15 * * * *', category: 'frequent' },
  { label: 'Каждые 30 минут', value: '*/30 * * * *', category: 'frequent' },
  { label: 'Каждый час', value: '0 * * * *', category: 'frequent' },
  { label: 'Каждые 2 часа', value: '0 */2 * * *', category: 'frequent' },
  { label: 'Каждые 6 часов', value: '0 */6 * * *', category: 'frequent' },
  { label: 'Каждые 12 часов', value: '0 */12 * * *', category: 'frequent' },
  // Daily
  { label: 'Ежедневно в полночь', value: '0 0 * * *', category: 'daily' },
  { label: 'Ежедневно в 6:00', value: '0 6 * * *', category: 'daily' },
  { label: 'Ежедневно в 9:00', value: '0 9 * * *', category: 'daily' },
  { label: 'Ежедневно в 12:00', value: '0 12 * * *', category: 'daily' },
  { label: 'Ежедневно в 18:00', value: '0 18 * * *', category: 'daily' },
  // Weekly
  { label: 'Понедельник в 9:00', value: '0 9 * * 1', category: 'weekly' },
  { label: 'Пятница в 17:00', value: '0 17 * * 5', category: 'weekly' },
  { label: 'Будни в 9:00', value: '0 9 * * 1-5', category: 'weekly' },
  { label: 'Выходные в 12:00', value: '0 12 * * 0,6', category: 'weekly' },
  // Monthly
  { label: '1-е число в полночь', value: '0 0 1 * *', category: 'monthly' },
  { label: '1-е число в 9:00', value: '0 9 1 * *', category: 'monthly' },
  { label: '15-е число в 12:00', value: '0 12 15 * *', category: 'monthly' },
]

const DAYS_OF_WEEK = [
  { key: '0', label: 'Вс' },
  { key: '1', label: 'Пн' },
  { key: '2', label: 'Вт' },
  { key: '3', label: 'Ср' },
  { key: '4', label: 'Чт' },
  { key: '5', label: 'Пт' },
  { key: '6', label: 'Сб' },
]

const CATEGORY_LABELS = {
  frequent: 'Частые',
  daily: 'Ежедневно',
  weekly: 'Еженедельно',
  monthly: 'Ежемесячно',
}

type ScheduleType = 'preset' | 'custom' | 'advanced'
type Frequency = 'minutes' | 'hours' | 'daily' | 'weekly' | 'monthly'

function parseCronExpression(cron: string): Date[] {
  const parts = cron.trim().split(/\s+/)
  if (parts.length !== 5) return []

  const [minutePart, hourPart, dayPart, monthPart, weekdayPart] = parts
  const now = new Date()
  const results: Date[] = []

  // Simple parser for common patterns
  const parseField = (field: string, max: number, offset = 0): number[] => {
    if (field === '*') return Array.from({ length: max }, (_, i) => i + offset)
    if (field.includes('/')) {
      const [, step] = field.split('/')
      const stepNum = parseInt(step)
      return Array.from({ length: Math.ceil(max / stepNum) }, (_, i) => i * stepNum + offset)
    }
    if (field.includes(',')) {
      return field.split(',').map((v) => parseInt(v))
    }
    if (field.includes('-')) {
      const [start, end] = field.split('-').map((v) => parseInt(v))
      return Array.from({ length: end - start + 1 }, (_, i) => i + start)
    }
    return [parseInt(field)]
  }

  try {
    const minutes = parseField(minutePart, 60, 0)
    const hours = parseField(hourPart, 24, 0)
    const days = dayPart === '*' ? null : parseField(dayPart, 31, 1)
    const months = monthPart === '*' ? null : parseField(monthPart, 12, 1)
    const weekdays = weekdayPart === '*' ? null : parseField(weekdayPart, 7, 0)

    // Generate next 5 runs
    const current = new Date(now)
    current.setSeconds(0)
    current.setMilliseconds(0)

    for (let i = 0; i < 1000 && results.length < 5; i++) {
      current.setMinutes(current.getMinutes() + 1)

      const m = current.getMinutes()
      const h = current.getHours()
      const d = current.getDate()
      const mo = current.getMonth() + 1
      const wd = current.getDay()

      if (!minutes.includes(m)) continue
      if (!hours.includes(h)) continue
      if (months && !months.includes(mo)) continue
      if (days && weekdays) {
        if (!days.includes(d) && !weekdays.includes(wd)) continue
      } else if (days && !days.includes(d)) continue
      else if (weekdays && !weekdays.includes(wd)) continue

      results.push(new Date(current))
    }
  } catch {
    return []
  }

  return results
}

export function CronBuilder() {
  const [expression, setExpression] = useState('0 9 * * *')
  const [scheduleType, setScheduleType] = useState<ScheduleType>('preset')
  const [selectedCategory, setSelectedCategory] = useState<keyof typeof CATEGORY_LABELS>('frequent')

  // Custom schedule state
  const [frequency, setFrequency] = useState<Frequency>('daily')
  const [interval, setInterval] = useState(5)
  const [hour, setHour] = useState(9)
  const [minute, setMinute] = useState(0)
  const [selectedDays, setSelectedDays] = useState<string[]>(['1'])
  const [dayOfMonth, setDayOfMonth] = useState(1)

  const getCronDescription = useCallback((cron: string): string => {
    try {
      return cronstrue.toString(cron, { use24HourTimeFormat: true, locale: 'ru' })
    } catch {
      return 'Некорректное выражение'
    }
  }, [])

  const buildCustomExpression = useCallback((): string => {
    switch (frequency) {
      case 'minutes':
        return `*/${interval} * * * *`
      case 'hours':
        return `${minute} */${interval} * * *`
      case 'daily':
        return `${minute} ${hour} * * *`
      case 'weekly':
        if (selectedDays.length === 0) return `${minute} ${hour} * * 1`
        return `${minute} ${hour} * * ${selectedDays.sort().join(',')}`
      case 'monthly':
        return `${minute} ${hour} ${dayOfMonth} * *`
      default:
        return '0 9 * * *'
    }
  }, [frequency, interval, minute, hour, selectedDays, dayOfMonth])

  useEffect(() => {
    if (scheduleType === 'custom') {
      setExpression(buildCustomExpression())
    }
  }, [scheduleType, buildCustomExpression])

  const toggleDay = (day: string) => {
    setSelectedDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
    )
  }

  const handlePresetSelect = (preset: PresetSchedule) => {
    setExpression(preset.value)
  }

  const filteredPresets = PRESET_SCHEDULES.filter((p) => p.category === selectedCategory)
  const nextRuns = parseCronExpression(expression)
  const isValid = getCronDescription(expression) !== 'Некорректное выражение'

  const copyToClipboard = () => {
    navigator.clipboard.writeText(expression)
  }

  return (
    <div className="space-y-8">
      {/* Main Expression Display */}
      <div className="bg-gray-900 dark:bg-gray-800 rounded-2xl p-6 text-center">
        <label className="block text-sm text-gray-400 mb-2">Cron-выражение</label>
        <div className="flex items-center justify-center gap-3">
          <input
            type="text"
            value={expression}
            onChange={(e) => {
              setExpression(e.target.value)
              setScheduleType('advanced')
            }}
            className="bg-transparent text-3xl sm:text-4xl font-mono text-white text-center border-none outline-none w-full"
            spellCheck={false}
          />
          <button
            onClick={copyToClipboard}
            className="p-2 text-gray-400 hover:text-white transition-colors"
            title="Скопировать"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </button>
        </div>
        <p className={`mt-4 text-lg ${isValid ? 'text-green-400' : 'text-red-400'}`}>
          {getCronDescription(expression)}
        </p>
      </div>

      {/* Schedule Type Tabs */}
      <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700 pb-4">
        <button
          onClick={() => setScheduleType('preset')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            scheduleType === 'preset'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          Готовые шаблоны
        </button>
        <button
          onClick={() => setScheduleType('custom')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            scheduleType === 'custom'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          Конструктор
        </button>
        <button
          onClick={() => setScheduleType('advanced')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            scheduleType === 'advanced'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          Ручной ввод
        </button>
      </div>

      {/* Preset Schedules */}
      {scheduleType === 'preset' && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {(Object.keys(CATEGORY_LABELS) as Array<keyof typeof CATEGORY_LABELS>).map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  selectedCategory === cat
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                }`}
              >
                {CATEGORY_LABELS[cat]}
              </button>
            ))}
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {filteredPresets.map((preset) => (
              <button
                key={preset.value}
                onClick={() => handlePresetSelect(preset)}
                className={`flex items-center justify-between p-4 rounded-xl border transition-colors ${
                  expression === preset.value
                    ? 'border-blue-600 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-700'
                }`}
              >
                <span className="font-medium text-gray-900 dark:text-white">{preset.label}</span>
                <code className="text-sm px-2 py-1 rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                  {preset.value}
                </code>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Custom Schedule Builder */}
      {scheduleType === 'custom' && (
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Частота
            </label>
            <select
              value={frequency}
              onChange={(e) => setFrequency(e.target.value as Frequency)}
              className="w-full p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            >
              <option value="minutes">Каждые N минут</option>
              <option value="hours">Каждые N часов</option>
              <option value="daily">Ежедневно</option>
              <option value="weekly">Еженедельно</option>
              <option value="monthly">Ежемесячно</option>
            </select>
          </div>

          {(frequency === 'minutes' || frequency === 'hours') && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Интервал
              </label>
              <div className="flex items-center gap-3">
                <span className="text-gray-600 dark:text-gray-400">Каждые</span>
                <input
                  type="number"
                  min={1}
                  max={frequency === 'minutes' ? 59 : 23}
                  value={interval}
                  onChange={(e) => {
                    const val = e.target.value
                    if (val === '') {
                      setInterval(0)
                    } else {
                      setInterval(parseInt(val) || 0)
                    }
                  }}
                  onBlur={(e) => {
                    const val = parseInt(e.target.value)
                    if (!val || val < 1) setInterval(1)
                  }}
                  className="w-20 p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                />
                <span className="text-gray-600 dark:text-gray-400">
                  {frequency === 'minutes' ? 'минут' : 'часов'}
                </span>
              </div>
            </div>
          )}

          {frequency === 'hours' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                На какой минуте
              </label>
              <select
                value={minute}
                onChange={(e) => setMinute(parseInt(e.target.value))}
                className="w-24 p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              >
                {[0, 15, 30, 45].map((m) => (
                  <option key={m} value={m}>
                    :{m.toString().padStart(2, '0')}
                  </option>
                ))}
              </select>
            </div>
          )}

          {(frequency === 'daily' || frequency === 'weekly' || frequency === 'monthly') && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Время
              </label>
              <div className="flex items-center gap-2">
                <select
                  value={hour}
                  onChange={(e) => setHour(parseInt(e.target.value))}
                  className="w-20 p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                >
                  {Array.from({ length: 24 }, (_, i) => (
                    <option key={i} value={i}>
                      {i.toString().padStart(2, '0')}
                    </option>
                  ))}
                </select>
                <span className="text-xl text-gray-600 dark:text-gray-400">:</span>
                <select
                  value={minute}
                  onChange={(e) => setMinute(parseInt(e.target.value))}
                  className="w-20 p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                >
                  {[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55].map((m) => (
                    <option key={m} value={m}>
                      {m.toString().padStart(2, '0')}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {frequency === 'weekly' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Дни недели
              </label>
              <div className="flex flex-wrap gap-2">
                {DAYS_OF_WEEK.map((day) => (
                  <button
                    key={day.key}
                    onClick={() => toggleDay(day.key)}
                    className={`w-12 h-12 rounded-xl font-medium transition-colors ${
                      selectedDays.includes(day.key)
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                    }`}
                  >
                    {day.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {frequency === 'monthly' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                День месяца
              </label>
              <select
                value={dayOfMonth}
                onChange={(e) => setDayOfMonth(parseInt(e.target.value))}
                className="w-24 p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              >
                {Array.from({ length: 31 }, (_, i) => (
                  <option key={i + 1} value={i + 1}>
                    {i + 1}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {/* Advanced Mode - Syntax Help */}
      {scheduleType === 'advanced' && (
        <div className="space-y-4">
          <div className="grid grid-cols-5 gap-4 text-center">
            {[
              { label: 'Минута', range: '0-59' },
              { label: 'Час', range: '0-23' },
              { label: 'День', range: '1-31' },
              { label: 'Месяц', range: '1-12' },
              { label: 'День недели', range: '0-6' },
            ].map((field, i) => (
              <div key={i} className="p-3 rounded-xl bg-gray-50 dark:bg-gray-800">
                <div className="font-medium text-gray-900 dark:text-white">{field.label}</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">{field.range}</div>
              </div>
            ))}
          </div>
          <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800">
            <p className="font-medium text-gray-900 dark:text-white mb-2">Специальные символы:</p>
            <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
              <li><code className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">*</code> — любое значение</li>
              <li><code className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">,</code> — список значений (1,3,5)</li>
              <li><code className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">-</code> — диапазон (1-5)</li>
              <li><code className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">/</code> — шаг (*/15 = каждые 15)</li>
            </ul>
          </div>
        </div>
      )}

      {/* Next Runs */}
      {isValid && nextRuns.length > 0 && (
        <div className="p-6 rounded-xl bg-gray-50 dark:bg-gray-800">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
            Следующие 5 запусков
          </h3>
          <ul className="space-y-2">
            {nextRuns.map((date, i) => (
              <li key={i} className="flex items-center gap-3 text-gray-600 dark:text-gray-400">
                <span className="w-6 h-6 flex items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400 text-sm font-medium">
                  {i + 1}
                </span>
                <span>
                  {date.toLocaleDateString('ru-RU', {
                    weekday: 'short',
                    day: 'numeric',
                    month: 'short',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* CTA */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-blue-600 to-blue-700 text-center">
        <h3 className="text-xl font-bold text-white mb-2">
          Запустите эту задачу в CronBox
        </h3>
        <p className="text-blue-100 mb-4">
          Автоматически выполняйте HTTP-запросы по расписанию без сервера
        </p>
        <a
          href={`https://cp.cronbox.ru/#/register?cron=${encodeURIComponent(expression)}`}
          className="inline-flex items-center px-6 py-3 bg-white text-blue-600 font-semibold rounded-lg hover:bg-blue-50 transition-colors"
        >
          Начать бесплатно
          <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
        </a>
      </div>
    </div>
  )
}
