import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Loader2, Plus, Trash2 } from 'lucide-react'
import type { ChainStep, CreateChainStepRequest, StepCondition } from '@/types/chains'
import type { HttpMethod } from '@/types'

interface ChainStepFormProps {
  step?: ChainStep
  stepOrder: number
  onSubmit: (data: CreateChainStepRequest) => Promise<void>
  onCancel: () => void
}

const HTTP_METHODS: HttpMethod[] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD']

const CONDITION_OPERATORS = [
  'status_code_equals',
  'status_code_in',
  'status_code_not_in',
  'equals',
  'not_equals',
  'contains',
  'not_contains',
  'regex',
  'exists',
  'not_exists',
] as const

type ConditionOperator = typeof CONDITION_OPERATORS[number]

export function ChainStepForm({ step, stepOrder, onSubmit, onCancel }: ChainStepFormProps) {
  const { t } = useTranslation()
  const isEditing = !!step

  const [name, setName] = useState(step?.name ?? '')
  const [url, setUrl] = useState(step?.url ?? '')
  const [method, setMethod] = useState<HttpMethod>(step?.method ?? 'GET')
  const [timeoutSeconds, setTimeoutSeconds] = useState(step?.timeout_seconds ?? 30)
  const [retryCount, setRetryCount] = useState(step?.retry_count ?? 0)
  const [retryDelaySeconds, setRetryDelaySeconds] = useState(step?.retry_delay_seconds ?? 60)
  const [headers, setHeaders] = useState(JSON.stringify(step?.headers ?? {}, null, 2))
  const [body, setBody] = useState(step?.body ?? '')
  const [continueOnFailure, setContinueOnFailure] = useState(step?.continue_on_failure ?? false)

  // Condition state
  const [hasCondition, setHasCondition] = useState(!!step?.condition)
  const [conditionOperator, setConditionOperator] = useState<ConditionOperator>(
    (step?.condition?.operator as ConditionOperator) ?? 'status_code_equals'
  )
  const [conditionField, setConditionField] = useState(step?.condition?.field ?? '')
  const [conditionValue, setConditionValue] = useState(
    Array.isArray(step?.condition?.value)
      ? step.condition.value.join(', ')
      : String(step?.condition?.value ?? '')
  )

  // Extract variables state
  const [extractVariables, setExtractVariables] = useState<Array<{ key: string; path: string }>>(
    step?.extract_variables
      ? Object.entries(step.extract_variables).map(([key, path]) => ({ key, path }))
      : []
  )

  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const addExtractVariable = () => {
    setExtractVariables([...extractVariables, { key: '', path: '' }])
  }

  const removeExtractVariable = (index: number) => {
    setExtractVariables(extractVariables.filter((_, i) => i !== index))
  }

  const updateExtractVariable = (index: number, field: 'key' | 'path', value: string) => {
    const updated = [...extractVariables]
    updated[index][field] = value
    setExtractVariables(updated)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validate
    if (!name.trim()) {
      setError(t('chains.stepNameRequired'))
      return
    }
    if (!url.trim()) {
      setError(t('chains.stepUrlRequired'))
      return
    }

    let parsedHeaders: Record<string, string> = {}
    try {
      parsedHeaders = headers.trim() ? JSON.parse(headers) : {}
    } catch {
      setError(t('taskForm.invalidHeadersJson'))
      return
    }

    // Build condition
    // When editing, send null explicitly to clear condition; when creating, use undefined
    let condition: StepCondition | null | undefined
    if (hasCondition && conditionValue.trim()) {
      const needsField = ['equals', 'not_equals', 'contains', 'not_contains', 'regex', 'exists', 'not_exists'].includes(conditionOperator)

      let parsedValue: string | number | number[] | string[] = conditionValue.trim()

      // Parse value based on operator
      if (['status_code_in', 'status_code_not_in'].includes(conditionOperator)) {
        parsedValue = conditionValue.split(',').map(v => parseInt(v.trim())).filter(n => !isNaN(n))
      } else if (conditionOperator === 'status_code_equals') {
        parsedValue = parseInt(conditionValue.trim()) || 200
      }

      condition = {
        operator: conditionOperator,
        value: parsedValue,
      }

      if (needsField && conditionField.trim()) {
        condition.field = conditionField.trim()
      }
    } else if (isEditing) {
      // Explicitly set to null when editing to allow clearing the condition
      condition = null
    }

    // Build extract variables
    const extractVarsRecord: Record<string, string> = {}
    for (const ev of extractVariables) {
      if (ev.key.trim() && ev.path.trim()) {
        extractVarsRecord[ev.key.trim()] = ev.path.trim()
      }
    }

    setIsLoading(true)

    try {
      const data: CreateChainStepRequest = {
        step_order: stepOrder,
        name: name.trim(),
        url: url.trim(),
        method,
        headers: parsedHeaders,
        body: body.trim() || undefined,
        timeout_seconds: timeoutSeconds,
        retry_count: retryCount,
        retry_delay_seconds: retryDelaySeconds,
        continue_on_failure: continueOnFailure,
        condition,
        // When editing, always send the value (even empty) to allow clearing
        // When creating, only send if there are variables
        extract_variables: isEditing ? extractVarsRecord : (Object.keys(extractVarsRecord).length > 0 ? extractVarsRecord : undefined),
      }

      await onSubmit(data)
    } catch {
      // Error handled in parent
    } finally {
      setIsLoading(false)
    }
  }

  const needsConditionField = ['equals', 'not_equals', 'contains', 'not_contains', 'regex', 'exists', 'not_exists'].includes(conditionOperator)

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="name">{t('chains.stepName')} *</Label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('chains.stepNamePlaceholder')}
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="method">{t('taskForm.method')}</Label>
          <Select value={method} onValueChange={(v) => setMethod(v as HttpMethod)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {HTTP_METHODS.map((m) => (
                <SelectItem key={m} value={m}>{m}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="url">{t('taskForm.url')} *</Label>
        <Input
          id="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder={t('chains.stepUrlPlaceholder')}
          required
        />
        <p className="text-xs text-muted-foreground">{t('chains.urlVariablesHelp')}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="timeout">{t('taskForm.timeoutSeconds')}</Label>
          <Input
            id="timeout"
            type="number"
            min={1}
            max={300}
            value={timeoutSeconds}
            onChange={(e) => setTimeoutSeconds(parseInt(e.target.value) || 30)}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="retries">{t('taskForm.retryCount')}</Label>
          <Input
            id="retries"
            type="number"
            min={0}
            max={10}
            value={retryCount}
            onChange={(e) => setRetryCount(parseInt(e.target.value) || 0)}
          />
        </div>

        {retryCount > 0 && (
          <div className="space-y-2">
            <Label htmlFor="retryDelay">{t('taskForm.retryDelaySeconds')}</Label>
            <Input
              id="retryDelay"
              type="number"
              min={1}
              max={3600}
              value={retryDelaySeconds}
              onChange={(e) => setRetryDelaySeconds(parseInt(e.target.value) || 60)}
            />
          </div>
        )}
      </div>

      <div className="flex items-center space-x-2">
        <Checkbox
          id="continueOnFailure"
          checked={continueOnFailure}
          onCheckedChange={(checked) => setContinueOnFailure(checked === true)}
        />
        <div className="grid gap-1.5 leading-none">
          <Label htmlFor="continueOnFailure" className="cursor-pointer">
            {t('chains.continueOnFailure')}
          </Label>
          <p className="text-xs text-muted-foreground">
            {t('chains.continueOnFailureHelp')}
          </p>
        </div>
      </div>

      <Accordion type="single" collapsible className="w-full">
        <AccordionItem value="headers">
          <AccordionTrigger>{t('chains.headers')}</AccordionTrigger>
          <AccordionContent>
            <div className="space-y-2">
              <textarea
                value={headers}
                onChange={(e) => setHeaders(e.target.value)}
                placeholder={t('taskForm.headersPlaceholder')}
                className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono"
              />
              <p className="text-xs text-muted-foreground">{t('chains.headersVariablesHelp')}</p>
            </div>
          </AccordionContent>
        </AccordionItem>

        {(method === 'POST' || method === 'PUT' || method === 'PATCH') && (
          <AccordionItem value="body">
            <AccordionTrigger>{t('chains.body')}</AccordionTrigger>
            <AccordionContent>
              <div className="space-y-2">
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  placeholder='{"key": "{{variable}}"}'
                  className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono"
                />
                <p className="text-xs text-muted-foreground">{t('chains.bodyVariablesHelp')}</p>
              </div>
            </AccordionContent>
          </AccordionItem>
        )}

        <AccordionItem value="condition">
          <AccordionTrigger>{t('chains.executionCondition')}</AccordionTrigger>
          <AccordionContent>
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="hasCondition"
                  checked={hasCondition}
                  onCheckedChange={(checked) => setHasCondition(checked === true)}
                />
                <Label htmlFor="hasCondition" className="cursor-pointer">
                  {t('chains.enableCondition')}
                </Label>
              </div>

              {hasCondition && (
                <div className="space-y-4 pl-6">
                  <div className="space-y-2">
                    <Label>{t('chains.conditionOperator')}</Label>
                    <Select value={conditionOperator} onValueChange={(v) => setConditionOperator(v as ConditionOperator)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {CONDITION_OPERATORS.map((op) => (
                          <SelectItem key={op} value={op}>
                            {t(`chains.condition_${op}`)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {needsConditionField && (
                    <div className="space-y-2">
                      <Label>{t('chains.conditionField')}</Label>
                      <Input
                        value={conditionField}
                        onChange={(e) => setConditionField(e.target.value)}
                        placeholder="$.data.status"
                      />
                      <p className="text-xs text-muted-foreground">{t('chains.conditionFieldHelp')}</p>
                    </div>
                  )}

                  <div className="space-y-2">
                    <Label>{t('chains.conditionValue')}</Label>
                    <Input
                      value={conditionValue}
                      onChange={(e) => setConditionValue(e.target.value)}
                      placeholder={
                        ['status_code_in', 'status_code_not_in'].includes(conditionOperator)
                          ? '200, 201, 202'
                          : conditionOperator === 'status_code_equals'
                          ? '200'
                          : 'value'
                      }
                    />
                    <p className="text-xs text-muted-foreground">{t('chains.conditionValueHelp')}</p>
                  </div>
                </div>
              )}
            </div>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="extract">
          <AccordionTrigger>{t('chains.extractVariables')}</AccordionTrigger>
          <AccordionContent>
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">{t('chains.extractVariablesHelp')}</p>

              {extractVariables.map((ev, index) => (
                <div key={index} className="flex items-center gap-2">
                  <Input
                    value={ev.key}
                    onChange={(e) => updateExtractVariable(index, 'key', e.target.value)}
                    placeholder={t('chains.variableName')}
                    className="flex-1"
                  />
                  <span className="text-muted-foreground">=</span>
                  <Input
                    value={ev.path}
                    onChange={(e) => updateExtractVariable(index, 'path', e.target.value)}
                    placeholder="$.data.id"
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removeExtractVariable(index)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}

              <Button type="button" variant="outline" size="sm" onClick={addExtractVariable}>
                <Plus className="mr-2 h-4 w-4" />
                {t('chains.addVariable')}
              </Button>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          {t('common.cancel')}
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isEditing ? t('chains.updateStep') : t('chains.addStep')}
        </Button>
      </div>
    </form>
  )
}
