import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchBusinesses, fetchHealth } from '../lib/api'
import { OverviewPage } from './OverviewPage'

vi.mock('../lib/api', () => ({
  fetchBusinesses: vi.fn(),
  fetchHealth: vi.fn(),
  loadSyntheticDemo: vi.fn(),
}))

const businesses = [
  {
    id: 'demo-a',
    name: 'Business A - Sunrise Foods',
    sector: 'Packaged foods',
    operating_months: 42,
    city: 'Pune',
    consent_status: 'granted',
    created_at: '2026-01-01T09:00:00',
  },
  {
    id: 'demo-b',
    name: 'Business B - Riverbend Repairs',
    sector: 'Appliance repair',
    operating_months: 30,
    city: 'Jaipur',
    consent_status: 'granted',
    created_at: '2026-01-01T09:00:00',
  },
]

describe('OverviewPage demo shortcuts', () => {
  beforeEach(() => {
    vi.mocked(fetchBusinesses).mockResolvedValue(businesses)
    vi.mocked(fetchHealth).mockResolvedValue({
      status: 'ok',
      service: 'credweave-ai-api',
      version: '0.1.0',
      synthetic_demo: true,
    })
  })

  it('links directly to each named synthetic business Evidence DNA view', async () => {
    render(<MemoryRouter><OverviewPage /></MemoryRouter>)

    const businessA = await screen.findByRole('link', { name: 'Business A — stronger evidence' })
    const businessB = screen.getByRole('link', { name: 'Business B — evidence gaps' })

    await waitFor(() => expect(businessA).toHaveAttribute('href', '/businesses/demo-a/evidence-dna'))
    expect(businessB).toHaveAttribute('href', '/businesses/demo-b/evidence-dna')
  })
})
