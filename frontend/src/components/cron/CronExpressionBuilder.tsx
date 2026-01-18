import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Calendar, Clock, Settings2 } from 'lucide-react'
import cronstrue from 'cronstrue/i18n'

interface CronExpressionBuilderProps {
  value: string
  onChange: (value: string) => void
}

type ScheduleType = 'preset' | 'custom' | 'advanced'

interface PresetSchedule {
  labelKey: string
  value: string
  category: 'frequent' | 'daily' | 'weekly' | 'monthly'
}

const PRESET_SCHEDULES: PresetSchedule[] = [
  // Frequent
  { labelKey: 'presetEveryMinute', value: '* * * * *', category: 'frequent' },
  { labelKey: 'presetEvery5Minutes', value: '*/5 * * * *', category: 'frequent' },
  { labelKey: 'presetEvery10Minutes', value: '*/10 * * * *', category: 'frequent' },
  { labelKey: 'presetEvery15Minutes', value: '*/15 * * * *', category: 'frequent' },
  { labelKey: 'presetEvery30Minutes', value: '*/30 * * * *', category: 'frequent' },
  { labelKey: 'presetEveryHour', value: '0 * * * *', category: 'frequent' },
  { labelKey: 'presetEvery2Hours', value: '0 */2 * * *', category: 'frequent' },
  { labelKey: 'presetEvery6Hours', value: '0 */6 * * *', category: 'frequent' },
  { labelKey: 'presetEvery12Hours', value: '0 */12 * * *', category: 'frequent' },
  // Daily
  { labelKey: 'presetDailyMidnight', value: '0 0 * * *', category: 'daily' },
  { labelKey: 'presetDaily6am', value: '0 6 * * *', category: 'daily' },
  { labelKey: 'presetDaily9am', value: '0 9 * * *', category: 'daily' },
  { labelKey: 'presetDailyNoon', value: '0 12 * * *', category: 'daily' },
  { labelKey: 'presetDaily6pm', value: '0 18 * * *', category: 'daily' },
  // Weekly
  { labelKey: 'presetMonday9am', value: '0 9 * * 1', category: 'weekly' },
  { labelKey: 'presetFriday5pm', value: '0 17 * * 5', category: 'weekly' },
  { labelKey: 'presetWeekdays9am', value: '0 9 * * 1-5', category: 'weekly' },
  { labelKey: 'presetWeekendsNoon', value: '0 12 * * 0,6', category: 'weekly' },
  // Monthly
  { labelKey: 'presetFirstOfMonthMidnight', value: '0 0 1 * *', category: 'monthly' },
  { labelKey: 'presetFirstOfMonth9am', value: '0 9 1 * *', category: 'monthly' },
  { labelKey: 'preset15thNoon', value: '0 12 15 * *', category: 'monthly' },
  { labelKey: 'presetLastDayMidnight', value: '0 0 L * *', category: 'monthly' },
]

const DAYS_OF_WEEK_KEYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']

export function CronExpressionBuilder({ value, onChange }: CronExpressionBuilderProps) {
  const { t, i18n } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const [scheduleType, setScheduleType] = useState<ScheduleType>('preset')
  const [selectedCategory, setSelectedCategory] = useState<'frequent' | 'daily' | 'weekly' | 'monthly'>('frequent')

  // Custom schedule state
  const [frequency, setFrequency] = useState<'minutes' | 'hours' | 'daily' | 'weekly' | 'monthly'>('daily')
  const [interval, setInterval] = useState<number | ''>(1)
  const [hour, setHour] = useState(9)
  const [minute, setMinute] = useState(0)
  const [selectedDays, setSelectedDays] = useState<string[]>(['1']) // Monday default
  const [dayOfMonth, setDayOfMonth] = useState(1)

  // Advanced state
  const [advancedExpression, setAdvancedExpression] = useState(value)

  const getCronDescription = (cron: string): string => {
    try {
      const locale = i18n.language === 'ru' ? 'ru' : 'en'
      return cronstrue.toString(cron, { use24HourTimeFormat: true, locale })
    } catch {
      return t('cronBuilder.invalidExpression')
    }
  }

  const buildCustomExpression = (): string => {
    const safeInterval = interval || 1
    switch (frequency) {
      case 'minutes':
        return `*/${safeInterval} * * * *`
      case 'hours':
        return `${minute} */${safeInterval} * * *`
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
  }

  const toggleDay = (day: string) => {
    setSelectedDays(prev =>
      prev.includes(day)
        ? prev.filter(d => d !== day)
        : [...prev, day]
    )
  }

  const handleApply = () => {
    let newValue = value

    if (scheduleType === 'preset') {
      // Value is already set by preset selection
    } else if (scheduleType === 'custom') {
      newValue = buildCustomExpression()
      onChange(newValue)
    } else if (scheduleType === 'advanced') {
      newValue = advancedExpression
      onChange(newValue)
    }

    setIsOpen(false)
  }

  const handlePresetSelect = (preset: PresetSchedule) => {
    onChange(preset.value)
    setIsOpen(false)
  }

  const filteredPresets = PRESET_SCHEDULES.filter(p => p.category === selectedCategory)

  // Update advanced expression when value changes
  useEffect(() => {
    setAdvancedExpression(value)
  }, [value])

  return (
    <div className="space-y-2">
      <Label>{t('cronBuilder.label')} *</Label>
      <div className="flex gap-2">
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="*/5 * * * *"
          className="font-mono"
          required
        />
        <Button
          type="button"
          variant="outline"
          onClick={() => setIsOpen(true)}
        >
          <Settings2 className="h-4 w-4 mr-2" />
          {t('cronBuilder.builder')}
        </Button>
      </div>
      <p className="text-sm text-muted-foreground">
        {getCronDescription(value)}
      </p>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t('cronBuilder.title')}</DialogTitle>
            <DialogDescription>
              {t('cronBuilder.description')}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6">
            {/* Schedule Type Tabs */}
            <div className="flex gap-2 border-b pb-4">
              <Button
                type="button"
                variant={scheduleType === 'preset' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setScheduleType('preset')}
              >
                <Clock className="h-4 w-4 mr-2" />
                {t('cronBuilder.presets')}
              </Button>
              <Button
                type="button"
                variant={scheduleType === 'custom' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setScheduleType('custom')}
              >
                <Calendar className="h-4 w-4 mr-2" />
                {t('cronBuilder.custom')}
              </Button>
              <Button
                type="button"
                variant={scheduleType === 'advanced' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setScheduleType('advanced')}
              >
                <Settings2 className="h-4 w-4 mr-2" />
                {t('cronBuilder.advanced')}
              </Button>
            </div>

            {/* Preset Schedules */}
            {scheduleType === 'preset' && (
              <div className="space-y-4">
                <div className="flex gap-2">
                  {(['frequent', 'daily', 'weekly', 'monthly'] as const).map((cat) => (
                    <Badge
                      key={cat}
                      variant={selectedCategory === cat ? 'default' : 'outline'}
                      className="cursor-pointer"
                      onClick={() => setSelectedCategory(cat)}
                    >
                      {t(`cronBuilder.${cat}`)}
                    </Badge>
                  ))}
                </div>
                <div className="grid gap-2 max-h-[300px] overflow-y-auto">
                  {filteredPresets.map((preset) => (
                    <Button
                      key={preset.value}
                      type="button"
                      variant={value === preset.value ? 'default' : 'outline'}
                      className="justify-between h-auto py-3"
                      onClick={() => handlePresetSelect(preset)}
                    >
                      <span>{t(`cronBuilder.${preset.labelKey}`)}</span>
                      <code className={`text-xs px-2 py-1 rounded ml-4 ${value === preset.value ? 'bg-primary-foreground/20 text-primary-foreground' : 'bg-muted text-foreground'}`}>
                        {preset.value}
                      </code>
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {/* Custom Schedule Builder */}
            {scheduleType === 'custom' && (
              <div className="space-y-6">
                <div className="space-y-2">
                  <Label>{t('cronBuilder.frequency')}</Label>
                  <Select value={frequency} onValueChange={(v) => setFrequency(v as typeof frequency)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="minutes">{t('cronBuilder.everyXMinutes')}</SelectItem>
                      <SelectItem value="hours">{t('cronBuilder.everyXHours')}</SelectItem>
                      <SelectItem value="daily">{t('cronBuilder.daily')}</SelectItem>
                      <SelectItem value="weekly">{t('cronBuilder.weekly')}</SelectItem>
                      <SelectItem value="monthly">{t('cronBuilder.monthly')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {(frequency === 'minutes' || frequency === 'hours') && (
                  <div className="space-y-2">
                    <Label>{t('cronBuilder.every')}</Label>
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        min={1}
                        max={frequency === 'minutes' ? 59 : 23}
                        value={interval}
                        onChange={(e) => {
                          const val = e.target.value
                          setInterval(val === '' ? '' : parseInt(val))
                        }}
                        onBlur={() => {
                          if (interval === '' || interval < 1) setInterval(1)
                        }}
                        className="w-20"
                      />
                      <span className="text-muted-foreground">{t(`cronBuilder.${frequency}`)}</span>
                    </div>
                  </div>
                )}

                {frequency === 'hours' && (
                  <div className="space-y-2">
                    <Label>{t('cronBuilder.atMinute')}</Label>
                    <Select value={minute.toString()} onValueChange={(v) => setMinute(parseInt(v))}>
                      <SelectTrigger className="w-24">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {[0, 15, 30, 45].map((m) => (
                          <SelectItem key={m} value={m.toString()}>:{m.toString().padStart(2, '0')}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                {(frequency === 'daily' || frequency === 'weekly' || frequency === 'monthly') && (
                  <div className="space-y-2">
                    <Label>{t('cronBuilder.time')}</Label>
                    <div className="flex items-center gap-2">
                      <Select value={hour.toString()} onValueChange={(v) => setHour(parseInt(v))}>
                        <SelectTrigger className="w-20">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {Array.from({ length: 24 }, (_, i) => (
                            <SelectItem key={i} value={i.toString()}>{i.toString().padStart(2, '0')}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <span>:</span>
                      <Select value={minute.toString()} onValueChange={(v) => setMinute(parseInt(v))}>
                        <SelectTrigger className="w-20">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55].map((m) => (
                            <SelectItem key={m} value={m.toString()}>{m.toString().padStart(2, '0')}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                )}

                {frequency === 'weekly' && (
                  <div className="space-y-2">
                    <Label>{t('cronBuilder.days')}</Label>
                    <div className="flex flex-wrap gap-2">
                      {DAYS_OF_WEEK_KEYS.map((dayKey, index) => (
                        <Button
                          key={index}
                          type="button"
                          variant={selectedDays.includes(index.toString()) ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => toggleDay(index.toString())}
                        >
                          {t(`cronBuilder.${dayKey}`)}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}

                {frequency === 'monthly' && (
                  <div className="space-y-2">
                    <Label>{t('cronBuilder.dayOfMonth')}</Label>
                    <Select value={dayOfMonth.toString()} onValueChange={(v) => setDayOfMonth(parseInt(v))}>
                      <SelectTrigger className="w-24">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Array.from({ length: 31 }, (_, i) => (
                          <SelectItem key={i + 1} value={(i + 1).toString()}>{i + 1}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                <div className="rounded-md bg-muted p-4">
                  <p className="text-sm font-medium">{t('cronBuilder.preview')}</p>
                  <code className="text-lg font-mono">{buildCustomExpression()}</code>
                  <p className="text-sm text-muted-foreground mt-2">
                    {getCronDescription(buildCustomExpression())}
                  </p>
                </div>
              </div>
            )}

            {/* Advanced Mode */}
            {scheduleType === 'advanced' && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>{t('cronBuilder.cronExpression')}</Label>
                  <Input
                    value={advancedExpression}
                    onChange={(e) => setAdvancedExpression(e.target.value)}
                    placeholder="* * * * *"
                    className="font-mono text-lg"
                  />
                </div>
                <div className="rounded-md bg-muted p-4">
                  <p className="text-sm text-muted-foreground">
                    {getCronDescription(advancedExpression)}
                  </p>
                </div>
                <div className="text-sm text-muted-foreground space-y-1">
                  <p className="font-medium">{t('cronBuilder.formatHelp')}</p>
                  <div className="grid grid-cols-5 gap-2 text-xs">
                    <div>
                      <p className="font-medium">{t('cronBuilder.minute')}</p>
                      <p>0-59</p>
                    </div>
                    <div>
                      <p className="font-medium">{t('cronBuilder.hour')}</p>
                      <p>0-23</p>
                    </div>
                    <div>
                      <p className="font-medium">{t('cronBuilder.day')}</p>
                      <p>1-31</p>
                    </div>
                    <div>
                      <p className="font-medium">{t('cronBuilder.month')}</p>
                      <p>1-12</p>
                    </div>
                    <div>
                      <p className="font-medium">{t('cronBuilder.weekday')}</p>
                      <p>0-6 ({t('cronBuilder.sun')}-{t('cronBuilder.sat')})</p>
                    </div>
                  </div>
                  <p className="mt-2">
                    {t('cronBuilder.specialChars')}
                  </p>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setIsOpen(false)}>
              {t('common.cancel')}
            </Button>
            {scheduleType !== 'preset' && (
              <Button type="button" onClick={handleApply}>
                {t('cronBuilder.apply')}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
