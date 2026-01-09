import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@/test/test-utils'
import { CronExpressionBuilder } from '../CronExpressionBuilder'

describe('CronExpressionBuilder', () => {
  const defaultProps = {
    value: '*/5 * * * *',
    onChange: vi.fn(),
  }

  it('should render input with current value', () => {
    render(<CronExpressionBuilder {...defaultProps} />)

    const input = screen.getByPlaceholderText('*/5 * * * *')
    expect(input).toHaveValue('*/5 * * * *')
  })

  it('should render builder button', () => {
    render(<CronExpressionBuilder {...defaultProps} />)

    expect(screen.getByText('Builder')).toBeInTheDocument()
  })

  it('should display cron description', () => {
    render(<CronExpressionBuilder {...defaultProps} />)

    // cronstrue library converts to human readable format
    expect(screen.getByText(/every 5 minutes/i)).toBeInTheDocument()
  })

  it('should call onChange when input value changes', async () => {
    const onChange = vi.fn()
    const { user } = render(<CronExpressionBuilder value="" onChange={onChange} />)

    const input = screen.getByPlaceholderText('*/5 * * * *')
    await user.type(input, '0 * * * *')

    expect(onChange).toHaveBeenCalled()
  })

  it('should open builder dialog when button clicked', async () => {
    const { user } = render(<CronExpressionBuilder {...defaultProps} />)

    await user.click(screen.getByText('Builder'))

    expect(screen.getByText('Schedule Builder')).toBeInTheDocument()
  })

  it('should display preset tabs in builder dialog', async () => {
    const { user } = render(<CronExpressionBuilder {...defaultProps} />)

    await user.click(screen.getByText('Builder'))

    expect(screen.getByText('Presets')).toBeInTheDocument()
    expect(screen.getByText('Custom')).toBeInTheDocument()
    expect(screen.getByText('Advanced')).toBeInTheDocument()
  })

  it('should display category badges in preset mode', async () => {
    const { user } = render(<CronExpressionBuilder {...defaultProps} />)

    await user.click(screen.getByText('Builder'))

    expect(screen.getByText('Frequent')).toBeInTheDocument()
    expect(screen.getByText('Daily')).toBeInTheDocument()
    expect(screen.getByText('Weekly')).toBeInTheDocument()
    expect(screen.getByText('Monthly')).toBeInTheDocument()
  })

  it('should show frequent presets by default', async () => {
    const { user } = render(<CronExpressionBuilder {...defaultProps} />)

    await user.click(screen.getByText('Builder'))

    // Check for preset buttons by their cron expressions which are visible
    expect(screen.getByText('* * * * *')).toBeInTheDocument()
    expect(screen.getByText('*/5 * * * *')).toBeInTheDocument()
    expect(screen.getByText('0 * * * *')).toBeInTheDocument()
  })

  it('should switch to daily presets when daily clicked', async () => {
    const { user } = render(<CronExpressionBuilder {...defaultProps} />)

    await user.click(screen.getByText('Builder'))
    await user.click(screen.getByText('Daily'))

    expect(screen.getByText('Daily at midnight')).toBeInTheDocument()
    expect(screen.getByText('Daily at 9 AM')).toBeInTheDocument()
    expect(screen.getByText('Daily at noon')).toBeInTheDocument()
  })

  it('should call onChange when preset selected', async () => {
    const onChange = vi.fn()
    const { user } = render(<CronExpressionBuilder value="*/5 * * * *" onChange={onChange} />)

    await user.click(screen.getByText('Builder'))
    await user.click(screen.getByText('Every hour'))

    expect(onChange).toHaveBeenCalledWith('0 * * * *')
  })

  it('should close dialog when preset selected', async () => {
    const { user } = render(<CronExpressionBuilder {...defaultProps} />)

    await user.click(screen.getByText('Builder'))
    expect(screen.getByText('Schedule Builder')).toBeInTheDocument()

    await user.click(screen.getByText('Every hour'))

    // Dialog should close
    expect(screen.queryByText('Schedule Builder')).not.toBeInTheDocument()
  })

  it('should switch to custom mode', async () => {
    const { user } = render(<CronExpressionBuilder {...defaultProps} />)

    await user.click(screen.getByText('Builder'))
    await user.click(screen.getByText('Custom'))

    expect(screen.getByText('Frequency')).toBeInTheDocument()
  })

  it('should switch to advanced mode', async () => {
    const { user } = render(<CronExpressionBuilder {...defaultProps} />)

    await user.click(screen.getByText('Builder'))
    await user.click(screen.getByText('Advanced'))

    expect(screen.getByText('Cron Expression')).toBeInTheDocument()
    expect(screen.getByText(/Format:/)).toBeInTheDocument()
  })

  it('should show apply button only in custom and advanced modes', async () => {
    const { user } = render(<CronExpressionBuilder {...defaultProps} />)

    await user.click(screen.getByText('Builder'))

    // In preset mode, no Apply button
    expect(screen.queryByText('Apply')).not.toBeInTheDocument()

    await user.click(screen.getByText('Custom'))
    expect(screen.getByText('Apply')).toBeInTheDocument()

    await user.click(screen.getByText('Advanced'))
    expect(screen.getByText('Apply')).toBeInTheDocument()
  })

  it('should close dialog when cancel clicked', async () => {
    const { user } = render(<CronExpressionBuilder {...defaultProps} />)

    await user.click(screen.getByText('Builder'))
    expect(screen.getByText('Schedule Builder')).toBeInTheDocument()

    await user.click(screen.getByText('Cancel'))

    expect(screen.queryByText('Schedule Builder')).not.toBeInTheDocument()
  })

  it('should display invalid expression message for invalid cron', () => {
    render(<CronExpressionBuilder value="invalid" onChange={vi.fn()} />)

    expect(screen.getByText('Invalid expression')).toBeInTheDocument()
  })
})
