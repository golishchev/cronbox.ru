import { describe, it, expect } from 'vitest'
import { render, screen } from '@/test/test-utils'
import { Alert, AlertTitle, AlertDescription } from '../alert'
import { Skeleton, DashboardSkeleton, TableSkeleton } from '../skeleton'
import { Switch } from '../switch'
import { Textarea } from '../textarea'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../table'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../card'
import { Toast, ToastProvider, ToastViewport, ToastTitle, ToastDescription, ToastClose, ToastAction } from '../toast'
import { Toaster } from '../toaster'

describe('UI Components', () => {
  describe('Alert', () => {
    it('should render alert with title and description', () => {
      render(
        <Alert>
          <AlertTitle>Alert Title</AlertTitle>
          <AlertDescription>Alert description text</AlertDescription>
        </Alert>
      )

      expect(screen.getByText('Alert Title')).toBeInTheDocument()
      expect(screen.getByText('Alert description text')).toBeInTheDocument()
    })

    it('should render destructive alert variant', () => {
      render(
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>Something went wrong</AlertDescription>
        </Alert>
      )

      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })

  describe('Skeleton', () => {
    it('should render basic skeleton', () => {
      render(<Skeleton className="w-20 h-20" />)

      const skeleton = document.querySelector('.animate-pulse')
      expect(skeleton).toBeInTheDocument()
    })

    it('should render dashboard skeleton', () => {
      render(<DashboardSkeleton />)

      // Should render multiple skeleton elements
      const skeletons = document.querySelectorAll('.animate-pulse')
      expect(skeletons.length).toBeGreaterThan(0)
    })

    it('should render table skeleton', () => {
      render(<TableSkeleton />)

      const skeletons = document.querySelectorAll('.animate-pulse')
      expect(skeletons.length).toBeGreaterThan(0)
    })
  })

  describe('Switch', () => {
    it('should render switch', () => {
      render(<Switch />)

      expect(screen.getByRole('switch')).toBeInTheDocument()
    })

    it('should render checked switch', () => {
      render(<Switch checked />)

      expect(screen.getByRole('switch')).toHaveAttribute('data-state', 'checked')
    })

    it('should render disabled switch', () => {
      render(<Switch disabled />)

      expect(screen.getByRole('switch')).toBeDisabled()
    })
  })

  describe('Textarea', () => {
    it('should render textarea', () => {
      render(<Textarea placeholder="Enter text" />)

      expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument()
    })

    it('should render textarea with value', () => {
      render(<Textarea value="Test value" readOnly />)

      expect(screen.getByDisplayValue('Test value')).toBeInTheDocument()
    })
  })

  describe('Table', () => {
    it('should render table with content', () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>Task 1</TableCell>
              <TableCell>Active</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )

      expect(screen.getByText('Name')).toBeInTheDocument()
      expect(screen.getByText('Status')).toBeInTheDocument()
      expect(screen.getByText('Task 1')).toBeInTheDocument()
      expect(screen.getByText('Active')).toBeInTheDocument()
    })
  })

  describe('Card', () => {
    it('should render card with all parts', () => {
      render(
        <Card>
          <CardHeader>
            <CardTitle>Card Title</CardTitle>
            <CardDescription>Card description</CardDescription>
          </CardHeader>
          <CardContent>
            <p>Card content</p>
          </CardContent>
          <CardFooter>
            <button>Action</button>
          </CardFooter>
        </Card>
      )

      expect(screen.getByText('Card Title')).toBeInTheDocument()
      expect(screen.getByText('Card description')).toBeInTheDocument()
      expect(screen.getByText('Card content')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument()
    })
  })

  describe('Toast', () => {
    it('should render toast components', () => {
      render(
        <ToastProvider>
          <Toast>
            <ToastTitle>Toast title</ToastTitle>
            <ToastDescription>Toast description</ToastDescription>
            <ToastAction altText="action">Action</ToastAction>
            <ToastClose />
          </Toast>
          <ToastViewport />
        </ToastProvider>
      )

      expect(screen.getByText('Toast title')).toBeInTheDocument()
      expect(screen.getByText('Toast description')).toBeInTheDocument()
    })
  })

  describe('Toaster', () => {
    it('should render toaster component', () => {
      render(<Toaster />)

      // Toaster renders a ToastViewport
      expect(document.querySelector('ol')).toBeInTheDocument()
    })
  })
})
