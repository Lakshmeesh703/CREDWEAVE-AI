import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchVerificationHistory, fetchVerifiedEvidence, reconcileVerifiedEvidence } from '../lib/api'
import { VerifiedEvidencePage } from './VerifiedEvidencePage'

vi.mock('../lib/api', () => ({
  fetchVerificationHistory: vi.fn(),
  fetchVerifiedEvidence: vi.fn(),
  reconcileVerifiedEvidence: vi.fn(),
}))

const current = {
  event_id: 2,
  status: 'SIMULATED_SOURCE_VERIFIED' as const,
  method: 'simulated_fixture',
  verified_at: '2025-01-01T09:00:00Z',
  findings: [{ code: 'DEMO_MOCK_SOURCE', reason: 'Seeded by the mock source.' }],
  limitations: ['Synthetic demo only. No institution was contacted.'],
  supporting_evidence: [],
}

function open(canReconcile = false) {
  render(<MemoryRouter initialEntries={['/businesses/sample/verified-evidence']}><Routes>
    <Route path="/businesses/:id/verified-evidence" element={<VerifiedEvidencePage canReconcile={canReconcile} />} />
  </Routes></MemoryRouter>)
}

describe('Verified Evidence Gateway', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fetchVerifiedEvidence).mockResolvedValue({
      counts: { SIMULATED_SOURCE_VERIFIED: 1 }, next_offset: null, items: [{
        provenance_id: 'provenance', record_id: 'record', record_type: 'transaction', source_id: 'source',
        source_type: 'SIMULATED', source_provider: 'Mock bank', original_source_reference: 'DEMO-1',
        uploaded_at: null, file_sha256: null, consent_reference: null, result: current,
      }],
    })
  })

  it('labels simulated evidence and shows append-only history to a read-only viewer', async () => {
    vi.mocked(fetchVerificationHistory).mockResolvedValue({ items: [current], next_after: null })
    open()
    fireEvent.click(await screen.findByRole('button', { name: 'DEMO-1' }))
    expect(screen.getByRole('dialog', { name: 'Verification details' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'transaction DEMO-1' })).toBeInTheDocument()
    expect(screen.getByText('Synthetic demo only. No institution was contacted.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Compare supporting records' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Show verification history' }))
    const history = await screen.findByRole('list', { name: 'Verification history' })
    expect(within(history).getByText('Simulated source verification')).toBeInTheDocument()
    expect(fetchVerificationHistory).toHaveBeenCalledWith('sample', 'provenance', 0)
  })

  it('allows the owner to reconcile and filter the records by status', async () => {
    vi.mocked(reconcileVerifiedEvidence).mockResolvedValue({ records_updated: 2 })
    open(true)
    await screen.findByRole('button', { name: 'DEMO-1' })
    fireEvent.click(screen.getByRole('button', { name: 'Compare supporting records' }))
    expect(await screen.findByText('2 records received updated results.')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('combobox', { name: 'Verification status' }),
      { target: { value: 'SIMULATED_SOURCE_VERIFIED' } })
    await screen.findByRole('button', { name: 'DEMO-1' })
    expect(fetchVerifiedEvidence).toHaveBeenLastCalledWith('sample', 0, 'SIMULATED_SOURCE_VERIFIED')

    const tile = screen.getByRole('button', { name: 'Simulated source verification 1' })
    expect(tile).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(tile)
    await screen.findByRole('button', { name: 'DEMO-1' })
    expect(tile).toHaveAttribute('aria-pressed', 'false')
    expect(fetchVerifiedEvidence).toHaveBeenLastCalledWith('sample', 0, undefined)
  })
})
