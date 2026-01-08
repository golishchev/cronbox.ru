import { useState, useEffect } from 'react'
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
import cronstrue from 'cronstrue'

interface CronExpressionBuilderProps {
  value: string
  onChange: (value: string) => void
}

type ScheduleType = 'preset' | 'custom' | 'advanced'

interface PresetSchedule {
  label: string
  value: string
  category: 'frequent' | 'daily' | 'weekly' | 'monthly'
}

const PRESET_SCHEDULES: PresetSchedule[] = [
  // Frequent
  { label: 'Every minute', value: '* * * * *', category: 'frequent' },
  { label: 'Every 5 minutes', value: '*/5 * * * *', category: 'frequent' },
  { label: 'Every 10 minutes', value: '*/10 * * * *', category: 'frequent' },
  { label: 'Every 15 minutes', value: '*/15 * * * *', category: 'frequent' },
  { label: 'Every 30 minutes', value: '*/30 * * * *', category: 'frequent' },
  { label: 'Every hour', value: '0 * * * *', category: 'frequent' },
  { label: 'Every 2 hours', value: '0 */2 * * *', category: 'frequent' },
  { label: 'Every 6 hours', value: '0 */6 * * *', category: 'frequent' },
  { label: 'Every 12 hours', value: '0 */12 * * *', category: 'frequent' },
  // Daily
  { label: 'Every day at midnight', value: '0 0 * * *', category: 'daily' },
  { label: 'Every day at 6am', value: '0 6 * * *', category: 'daily' },
  { label: 'Every day at 9am', value: '0 9 * * *', category: 'daily' },
  { label: 'Every day at noon', value: '0 12 * * *', category: 'daily' },
  { label: 'Every day at 6pm', value: '0 18 * * *', category: 'daily' },
  // Weekly
  { label: 'Every Monday at 9am', value: '0 9 * * 1', category: 'weekly' },
  { label: 'Every Friday at 5pm', value: '0 17 * * 5', category: 'weekly' },
  { label: 'Weekdays at 9am', value: '0 9 * * 1-5', category: 'weekly' },
  { label: 'Weekends at noon', value: '0 12 * * 0,6', category: 'weekly' },
  // Monthly
  { label: '1st of month at midnight', value: '0 0 1 * *', category: 'monthly' },
  { label: '1st of month at 9am', value: '0 9 1 * *', category: 'monthly' },
  { label: '15th of month at noon', value: '0 12 15 * *', category: 'monthly' },
  { label: 'Last day of month at midnight', value: '0 0 L * *', category: 'monthly' },
]

const DAYS_OF_WEEK = [
  { value: '0', label: 'Sun' },
  { value: '1', label: 'Mon' },
  { value: '2', label: 'Tue' },
  { value: '3', label: 'Wed' },
  { value: '4', label: 'Thu' },
  { value: '5', label: 'Fri' },
  { value: '6', label: 'Sat' },
]

export function CronExpressionBuilder({ value, onChange }: CronExpressionBuilderProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [scheduleType, setScheduleType] = useState<ScheduleType>('preset')
  const [selectedCategory, setSelectedCategory] = useState<'frequent' | 'daily' | 'weekly' | 'monthly'>('frequent')

  // Custom schedule state
  const [frequency, setFrequency] = useState<'minutes' | 'hours' | 'daily' | 'weekly' | 'monthly'>('daily')
  const [interval, setInterval] = useState(1)
  const [hour, setHour] = useState(9)
  const [minute, setMinute] = useState(0)
  const [selectedDays, setSelectedDays] = useState<string[]>(['1']) // Monday default
  const [dayOfMonth, setDayOfMonth] = useState(1)

  // Advanced state
  const [advancedExpression, setAdvancedExpression] = useState(value)

  const getCronDescription = (cron: string): string => {
    try {
      return cronstrue.toString(cron, { use24HourTimeFormat: true })
    } catch {
      return 'Invalid cron expression'
    }
  }

  const buildCustomExpression = (): string => {
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
      <Label>Cron Schedule *</Label>
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
          Builder
        </Button>
      </div>
      <p className="text-sm text-muted-foreground">
        {getCronDescription(value)}
      </p>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Schedule Builder</DialogTitle>
            <DialogDescription>
              Configure when your task should run
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
                Presets
              </Button>
              <Button
                type="button"
                variant={scheduleType === 'custom' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setScheduleType('custom')}
              >
                <Calendar className="h-4 w-4 mr-2" />
                Custom
              </Button>
              <Button
                type="button"
                variant={scheduleType === 'advanced' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setScheduleType('advanced')}
              >
                <Settings2 className="h-4 w-4 mr-2" />
                Advanced
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
                      className="cursor-pointer capitalize"
                      onClick={() => setSelectedCategory(cat)}
                    >
                      {cat}
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
                      <span>{preset.label}</span>
                      <code className="text-xs bg-muted px-2 py-1 rounded ml-4">
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
                  <Label>Frequency</Label>
                  <Select value={frequency} onValueChange={(v) => setFrequency(v as typeof frequency)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="minutes">Every X minutes</SelectItem>
                      <SelectItem value="hours">Every X hours</SelectItem>
                      <SelectItem value="daily">Daily</SelectItem>
                      <SelectItem value="weekly">Weekly</SelectItem>
                      <SelectItem value="monthly">Monthly</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {(frequency === 'minutes' || frequency === 'hours') && (
                  <div className="space-y-2">
                    <Label>Every</Label>
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        min={1}
                        max={frequency === 'minutes' ? 59 : 23}
                        value={interval}
                        onChange={(e) => setInterval(parseInt(e.target.value) || 1)}
                        className="w-20"
                      />
                      <span className="text-muted-foreground">{frequency}</span>
                    </div>
                  </div>
                )}

                {frequency === 'hours' && (
                  <div className="space-y-2">
                    <Label>At minute</Label>
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
                    <Label>Time</Label>
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
                    <Label>Days</Label>
                    <div className="flex flex-wrap gap-2">
                      {DAYS_OF_WEEK.map((day) => (
                        <Button
                          key={day.value}
                          type="button"
                          variant={selectedDays.includes(day.value) ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => toggleDay(day.value)}
                        >
                          {day.label}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}

                {frequency === 'monthly' && (
                  <div className="space-y-2">
                    <Label>Day of month</Label>
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
                  <p className="text-sm font-medium">Preview</p>
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
                  <Label>Cron Expression</Label>
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
                  <p className="font-medium">Format: minute hour day-of-month month day-of-week</p>
                  <div className="grid grid-cols-5 gap-2 text-xs">
                    <div>
                      <p className="font-medium">Minute</p>
                      <p>0-59</p>
                    </div>
                    <div>
                      <p className="font-medium">Hour</p>
                      <p>0-23</p>
                    </div>
                    <div>
                      <p className="font-medium">Day</p>
                      <p>1-31</p>
                    </div>
                    <div>
                      <p className="font-medium">Month</p>
                      <p>1-12</p>
                    </div>
                    <div>
                      <p className="font-medium">Weekday</p>
                      <p>0-6 (Sun-Sat)</p>
                    </div>
                  </div>
                  <p className="mt-2">
                    Special chars: * (any), */n (every n), n-m (range), n,m (list)
                  </p>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setIsOpen(false)}>
              Cancel
            </Button>
            {scheduleType !== 'preset' && (
              <Button type="button" onClick={handleApply}>
                Apply
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
