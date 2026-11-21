import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import cytoscape, { type Core, type ElementDefinition } from 'cytoscape'

import { fetchTrustGraph, type TrustGraph, type TrustGraphEdge, type TrustGraphNode } from '../lib/api'

import { EvidenceDrawer } from './EvidenceDrawer'
import { EmptyState, ErrorState, LoadingSkeleton, MetricCard, PageHeader } from './ui'

const colors: Record<string, string> = {
  Business: '#0f766e',
  Counterparty: '#2563eb',
  Invoice: '#d97706',
  Transaction: '#7c3aed',
}

function EvidenceDetails({ selected, nodes }: { selected: TrustGraphNode | TrustGraphEdge | null; nodes: TrustGraphNode[] }) {
  if (!selected) return <p className="text-sm text-slate-500">Click a node or edge to inspect linked evidence.</p>
  const record = selected as Record<string, unknown>
  const relatedRecords = selected.type === 'Counterparty'
    ? nodes.filter((node) => node.counterparty_id === record.counterparty_id)
    : []
  return (
    <div className="space-y-2 text-sm text-slate-600">
      <p><strong className="text-ink">Type:</strong> {String(record.type ?? 'Edge')}</p>
      <p><strong className="text-ink">Label:</strong> {String(record.label ?? record.type)}</p>
      {record.amount_inr !== undefined && <p><strong className="text-ink">Amount:</strong> ₹{String(record.amount_inr)}</p>}
      {record.date !== undefined && <p><strong className="text-ink">Date:</strong> {String(record.date)}</p>}
      {record.verification_status !== undefined && <p><strong className="text-ink">Verification:</strong> {String(record.verification_status)}</p>}
      <p><strong className="text-ink">Source IDs:</strong> {selected.source_ids.join(', ') || 'Business-level record'}</p>
      {record.record_ids !== undefined && <p><strong className="text-ink">Records:</strong> {String(record.record_ids)}</p>}
      {selected.type === 'Counterparty' && <section className="border-t border-slate-200 pt-3">
        <h3 className="font-semibold text-ink">Related invoice and transaction records</h3>
        {relatedRecords.length === 0
          ? <p className="mt-2 text-xs">No linked transaction or invoice records in the available sources.</p>
          : <ul className="mt-2 space-y-2">{relatedRecords.map((item) => <li key={item.id} className="rounded bg-slate-50 p-2 text-xs">
            <strong className="text-ink">{item.type}: {item.label}</strong>
            {item.amount_inr !== undefined && <span className="block">Amount: ₹{String(item.amount_inr)}</span>}
            {item.date !== undefined && <span className="block">Date: {String(item.date)}</span>}
            <span className="block">Source IDs: {item.source_ids.join(', ')}</span>
          </li>)}</ul>}
      </section>}
    </div>
  )
}

export function TrustGraphPage() {
  const { id = '' } = useParams()
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | undefined>(undefined)
  const [data, setData] = useState<TrustGraph>()
  const [selected, setSelected] = useState<TrustGraphNode | TrustGraphEdge | null>(null)
  const [filter, setFilter] = useState('all')
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [edgeType, setEdgeType] = useState('')
  const [expandedList, setExpandedList] = useState(false)
  const edgeTypes = Array.from(new Set(data?.edges.map((edge) => edge.type)))
  const visible = useMemo(() => {
    if (!data) return { nodes: [], edges: [] }
    const term = search.trim().toLowerCase()
    const matching = new Set(data.nodes.filter((node) =>
      (filter === 'all' || node.type === filter) && (!term || `${node.label} ${node.type} ${node.id}`.toLowerCase().includes(term)),
    ).map((node) => node.id))
    const scoped = filter !== 'all' || Boolean(term)
    const edges = data.edges.filter((edge) => (!edgeType || edge.type === edgeType)
      && (!scoped || matching.has(edge.source) || matching.has(edge.target)))
    const connected = new Set(edges.flatMap((edge) => [edge.source, edge.target]))
    return { nodes: data.nodes.filter((node) => connected.has(node.id) || (!edgeType && matching.has(node.id))), edges }
  }, [data, edgeType, filter, search])

  useEffect(() => {
    let active = true
    void fetchTrustGraph(id).then((result) => { if (active) setData(result) })
      .catch(() => { if (active) setError('Could not load the trust graph for this business.') })
    return () => { active = false }
  }, [id])

  useEffect(() => {
    if (!data || !containerRef.current) return
    const flagged = new Set(data.anomalies.flatMap((item) => item.record_ids))
    const elements: ElementDefinition[] = [
      ...visible.nodes.map((node) => ({ data: { ...node, color: colors[node.type] }, classes: flagged.has(node.id) || flagged.has(node.id.split(':').slice(1).join(':')) ? 'attention' : '' })),
      ...visible.edges.map((edge) => ({ data: edge, classes: Array.isArray(edge.record_ids) && edge.record_ids.some((record) => flagged.has(String(record))) ? 'attention' : '' })),
    ]
    cyRef.current?.destroy()
    const cy = cytoscape({
      container: containerRef.current,
      elements,
      minZoom: 0.12,
      maxZoom: 4,
      style: [
        { selector: 'node', style: { label: 'data(label)', 'background-color': 'data(color)', color: '#0f172a', 'font-size': '9px', 'text-wrap': 'wrap', 'text-max-width': '90px' } },
        { selector: 'edge', style: { label: 'data(type)', width: 2, 'line-color': '#94a3b8', 'target-arrow-color': '#94a3b8', 'target-arrow-shape': 'triangle', 'font-size': '8px', color: '#475569' } },
        { selector: 'node.attention', style: { 'border-color': '#b45309', 'border-width': 3 } },
        { selector: 'edge.attention', style: { 'line-color': '#b45309', 'line-style': 'dashed', 'target-arrow-color': '#b45309' } },
      ],
      layout: { name: visible.nodes.length > 160 ? 'grid' : 'cose', animate: false, fit: true, padding: 30 },
    })
    cy.on('tap', 'node', (event) => setSelected(event.target.data() as TrustGraphNode))
    cy.on('tap', 'edge', (event) => setSelected(event.target.data() as TrustGraphEdge))
    cyRef.current = cy
    return () => { cy.destroy(); cyRef.current = undefined }
  }, [data, visible])

  if (error) return <main className="mx-auto max-w-5xl px-6 py-10"><ErrorState>{error}</ErrorState></main>
  if (!data) return <main className="mx-auto max-w-5xl px-6 py-10"><LoadingSkeleton>Loading Dynamic Trust Graph…</LoadingSkeleton></main>

  return (
    <main className="space-y-5">
      <PageHeader title="Dynamic Trust Graph" description="Explore relationships observed in invoices, transactions, and counterparties."
        action={<Link to={`/businesses/${id}/evidence-dna`} className="cw-button-secondary">Evidence DNA</Link>} />
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="Nodes" value={data.metrics.node_count ?? data.nodes.length} />
        <MetricCard label="Edges" value={data.metrics.edge_count ?? data.edges.length} />
        <MetricCard label="Top supplier share" value={data.metrics.top_supplier_share_percent == null ? 'Unavailable' : `${data.metrics.top_supplier_share_percent}%`} />
        <MetricCard label="Review findings" value={data.metrics.anomaly_count ?? data.anomalies.length} />
      </dl>
      {data.nodes.length <= 1 ? <EmptyState>Upload invoices, linked payments, or supplier records to explore relationships.</EmptyState> : <section className="cw-panel min-w-0">
        <div className="flex flex-wrap items-end gap-3">
          <label className="grid max-w-full gap-1 text-sm font-semibold">Search graph<input className="cw-input" type="search" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
          <label className="grid gap-1 text-sm font-semibold">Entity type
            <select className="cw-input" value={filter} onChange={(event) => setFilter(event.target.value)}>
              <option value="all">All entities</option>{Object.keys(colors).map((type) => <option key={type}>{type}</option>)}
            </select>
          </label>
          <label className="grid max-w-full gap-1 text-sm font-semibold">Relationship type
            <select className="cw-input max-w-full" value={edgeType} onChange={(event) => setEdgeType(event.target.value)}>
              <option value="">All relationships</option>{edgeTypes.map((type) => <option key={type} value={type}>{type.replace(/_/g, ' ')}</option>)}
            </select>
          </label>
          <button type="button" className="cw-button-secondary" onClick={() => cyRef.current?.fit(undefined, 28)}>Zoom to fit</button>
        </div>
        <ul aria-label="Graph legend" className="mt-4 flex flex-wrap gap-3 text-xs font-semibold">
          {Object.entries(colors).map(([type, color]) => <li key={type} className="flex items-center gap-1.5"><span aria-hidden="true" className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />{type}</li>)}
          {data.anomalies.length > 0 && <li className="text-amber-900">Amber borders and dashed links flag records for review.</li>}
        </ul>
        <div ref={containerRef} aria-label="Interactive trust graph" className="mt-3 h-[340px] overflow-hidden rounded-xl border bg-slate-50 sm:h-[500px]" />
        {visible.nodes.length === 0 && <p className="mt-3 text-sm text-slate-600">No graph records match these filters.</p>}
        <details className="mt-4" onToggle={(event) => setExpandedList(event.currentTarget.open)}>
          <summary className="cursor-pointer font-bold text-teal">Browse nodes and relationships ({visible.nodes.length} nodes, {visible.edges.length} links)</summary>
          {expandedList && <ul className="mt-3 max-h-72 divide-y overflow-y-auto rounded-lg border text-sm" aria-label="Graph records">
            {visible.nodes.map((node) => <li key={node.id}><button type="button" className="min-h-11 w-full break-all px-3 text-left hover:bg-emerald-50" onClick={() => setSelected(node)}>{node.type} · {node.label}</button></li>)}
            {visible.edges.map((edge) => <li key={edge.id}><button type="button" className="min-h-11 w-full break-all px-3 text-left hover:bg-emerald-50" onClick={() => setSelected(edge)}>{edge.type.replace(/_/g, ' ')} · {edge.source} → {edge.target}</button></li>)}
          </ul>}
        </details>
      </section>}
      {selected && <EvidenceDrawer title="Evidence details" onClose={() => setSelected(null)}>
        <div className="cw-panel break-words"><EvidenceDetails selected={selected} nodes={data.nodes} /></div>
        {selected.source_ids.map((source) => <Link className="mt-3 block break-all font-semibold text-teal hover:underline" to={`/businesses/${id}/verified-evidence?source=${encodeURIComponent(source)}` } key={source}>Open source {source}</Link>)}
      </EvidenceDrawer>}
      <section className="mt-6 rounded-xl bg-white p-5 shadow-sm"><h2 className="text-lg font-bold text-ink">Review findings</h2>{data.anomalies.length === 0 ? <p className="mt-3 text-sm text-slate-600">No graph findings for the available records.</p> : <ul className="mt-3 space-y-3">{data.anomalies.map((item, index) => <li key={`${item.code}-${index}`} className="rounded border border-slate-200 p-3 text-sm text-slate-600"><strong className="text-ink">{item.code}</strong><p className="mt-1">{item.message}</p><p className="mt-1 text-xs">Follow-up: {item.recommended_follow_up}</p></li>)}</ul>}</section>
      <p className="mt-4 text-xs text-slate-500">Rule {data.rule_version} · masked identifiers only · graph analytics do not establish authenticity or fraud.</p>
    </main>
  )
}
