import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EvidenceDnaPage } from './EvidenceDnaPage'

describe('EvidenceDnaPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('keeps completeness, consistency, and confidence separate', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      business_id: 'b-1',
      business_name: 'Synthetic Shop',
      rule_version: 'evidence-dna.v1',
      evidence_completeness: { score: 80, denominator: 10, expected_periods: ['2025-07'] },
      evidence_consistency: { score: 70, denominator: 5, matched: 4 },
      verification_status: { 'uploaded-only': 1, 'cross-source-consistent': 4, 'externally-verified': 0, disputed: 0, unavailable: 0 },
      assessment_confidence: { label: 'moderate', rationale: 'Some gaps remain.' },
      claim_to_evidence: { reported_amount_inr: '100000', observed_monthly_credit_inr: { '2025-07': '98000' }, status: 'compared', explanation: 'Comparison only.' },
      findings: [],
      limitations: ['Synthetic only.'],
      provenance: { data_scope: 'business-scoped records only', synthetic: true, source_ids: [], rule_version: 'evidence-dna.v1' },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    render(<MemoryRouter initialEntries={['/businesses/b-1/evidence-dna']}><Routes><Route path="/businesses/:id/evidence-dna" element={<EvidenceDnaPage />} /></Routes></MemoryRouter>)

    expect(await screen.findByText('Evidence DNA')).toBeInTheDocument()
    expect(screen.getByText('Evidence completeness')).toBeInTheDocument()
    expect(screen.getByText('Evidence consistency')).toBeInTheDocument()
    expect(screen.getByText('Assessment confidence')).toBeInTheDocument()
  })
})
