import { act, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchTrustGraph, type TrustGraph } from '../lib/api'
import { TrustGraphPage } from './TrustGraphPage'

const cytoscapeHarness = vi.hoisted(() => ({
  handlers: {} as Record<string, (event: { target: { data: () => unknown } }) => void>,
}))

vi.mock('cytoscape', () => ({
  default: vi.fn(() => ({
    on: (_event: string, selector: string, handler: (event: { target: { data: () => unknown } }) => void) => {
      cytoscapeHarness.handlers[selector] = handler
    },
    destroy: vi.fn(),
  })),
}))

vi.mock('../lib/api', () => ({
  fetchTrustGraph: vi.fn(),
}))

const supplier = {
  id: 'counterparty:supplier-a',
  type: 'Counterparty' as const,
  label: 'SYNTHETIC - Synthetic Grain Supplier',
  source_ids: ['source-upi'],
  counterparty_id: 'supplier-a',
  counterparty_type: 'supplier',
}

const payment = {
  id: 'transaction:payment-a',
  type: 'Transaction' as const,
  label: 'SYN-SUP-A-202507',
  source_ids: ['source-upi'],
  counterparty_id: 'supplier-a',
  amount_inr: '42000.00',
  date: '2025-07-16',
}

const graph: TrustGraph = {
  business_id: 'business-a',
  rule_version: 'trust-graph.v1',
  nodes: [supplier, payment],
  edges: [],
  anomalies: [],
  metrics: {
    node_count: 2,
    edge_count: 0,
    top_supplier_share_percent: '100.00',
    anomaly_count: 0,
  },
  provenance: {
    synthetic: true,
    business_id: 'business-a',
    source_ids: ['source-upi'],
    data_scope: 'business-scoped records only',
    networkx: '3.x',
    rule_version: 'trust-graph.v1',
  },
}

describe('TrustGraphPage', () => {
  beforeEach(() => {
    cytoscapeHarness.handlers = {}
    vi.mocked(fetchTrustGraph).mockResolvedValue(graph)
  })

  it('shows source-linked payment records when a supplier node is selected', async () => {
    render(
      <MemoryRouter initialEntries={['/businesses/business-a/trust-graph']}>
        <Routes>
          <Route path="/businesses/:id/trust-graph" element={<TrustGraphPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByRole('heading', { name: 'Dynamic Trust Graph' })
    await waitFor(() => expect(cytoscapeHarness.handlers.node).toBeDefined())
    act(() => cytoscapeHarness.handlers.node({ target: { data: () => supplier } }))

    expect(await screen.findByText('Type:')).toBeInTheDocument()
    expect(screen.getByText('Related invoice and transaction records')).toBeInTheDocument()
    expect(screen.getByText('Transaction: SYN-SUP-A-202507')).toBeInTheDocument()
    expect(screen.getByText('Amount: ₹42000.00')).toBeInTheDocument()
    expect(screen.getAllByText('Source IDs: source-upi')).toHaveLength(2)
  })
})
