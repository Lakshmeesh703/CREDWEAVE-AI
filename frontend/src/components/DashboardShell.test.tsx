// Runtime validation coverage: dashboard navigation and accessible labels
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { DashboardShell } from './DashboardShell'

vi.mock('../lib/api', () => ({
  fetchBusinesses: vi.fn().mockResolvedValue([
    { id: 'demo-a', name: 'Sunrise Foods' },
    { id: 'demo-b', name: 'Riverbend Repairs' },
  ]),
}))

function CurrentPath() {
  return <p>{useLocation().pathname}</p>
}

describe('DashboardShell', () => {
  it('provides every dashboard menu item with an accessible primary navigation', () => {
    render(
      <MemoryRouter initialEntries={['/overview']}>
        <DashboardShell><h1>Dashboard</h1></DashboardShell>
      </MemoryRouter>,
    )

    const navigation = screen.getByRole('navigation', { name: 'Primary navigation' })
    const links = within(navigation).getAllByRole('link')
    expect(links.map((link) => link.textContent)).toEqual([
      'Overview',
      'Businesses',
      'Data Sources',
      'Verified Evidence Gateway',
      'Evidence DNA',
      'Trust Graph',
      'Financial Health',
      'Risk Insights',
      'CashFlow Twin',
      'Loan Options',
      'Credit Passport',
      'Reviewer Desk',
    ])

    expect(screen.getByRole('link', { name: 'CREDWEAVE AI overview' })).toBeInTheDocument()
    expect(screen.getByText('SYNTHETIC DEMO')).toBeInTheDocument()
  })

  it('keeps stage links scoped and switches businesses within the current stage', async () => {
    render(
      <MemoryRouter initialEntries={['/businesses/demo-a/assess']}>
        <DashboardShell><CurrentPath /></DashboardShell>
      </MemoryRouter>,
    )

    const picker = screen.getByRole('combobox', { name: 'Active business' })
    await within(picker).findByRole('option', { name: 'Riverbend Repairs' })
    expect(picker).toHaveValue('demo-a')
    expect(screen.getByRole('link', { name: 'Risk Insights' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Credit Passport' })).toHaveAttribute('href', '/businesses/demo-a/credit-passport')

    fireEvent.change(picker, { target: { value: 'demo-b' } })

    expect(screen.getByText('/businesses/demo-b/assess')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Credit Passport' })).toHaveAttribute('href', '/businesses/demo-b/credit-passport')
  })
})
