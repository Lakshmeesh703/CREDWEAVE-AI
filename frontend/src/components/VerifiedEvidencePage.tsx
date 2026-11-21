import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import {
  fetchVerificationHistory, fetchVerifiedEvidence, reconcileVerifiedEvidence,
  type GatewayFilters, type GatewayRecord, type VerificationEvent, type VerificationStatus,
} from '../lib/api'

import { EvidenceDrawer } from './EvidenceDrawer'

const labels: Record<VerificationStatus, string> = {
  UNVERIFIED: 'Unverified',
  PARTIALLY_SUPPORTED: 'Partially supported',
  SOURCE_VERIFIED: 'Institutional source verified',
  REQUIRES_REVIEW: 'Requires review',
  SIMULATED_SOURCE_VERIFIED: 'Simulated source verification',
}
const statuses = Object.keys(labels) as VerificationStatus[]
const palette: Record<VerificationStatus, { dot: string; badge: string }> = {
  UNVERIFIED: { dot: 'bg-slate-400', badge: 'bg-slate-100 text-slate-700' },
  PARTIALLY_SUPPORTED: { dot: 'bg-teal', badge: 'bg-teal/10 text-teal' },
  SOURCE_VERIFIED: { dot: 'bg-emerald-600', badge: 'bg-emerald-100 text-emerald-800' },
  REQUIRES_REVIEW: { dot: 'bg-amber-500', badge: 'bg-amber-100 text-amber-900' },
  SIMULATED_SOURCE_VERIFIED: { dot: 'bg-violet-500', badge: 'bg-violet-100 text-violet-800' },
}
const statusGrid = 'grid grid-cols-[repeat(auto-fit,minmax(min(100%,10rem),1fr))] gap-3'
const statusCard = 'flex min-h-24 flex-col justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3.5 text-left'
const control = 'inline-flex min-h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm font-semibold text-slate-700 hover:border-teal/40 hover:text-teal disabled:opacity-50'

function StatusLabel({ status }: { status: VerificationStatus }) {
  return <span className="flex items-center gap-2 text-xs font-semibold leading-snug text-slate-600">
    <span aria-hidden="true" className={`h-2 w-2 shrink-0 rounded-full ${palette[status].dot}`} />
    {labels[status]}
  </span>
}

function MetricValue({ count }: { count: number }) {
  return <span className="text-2xl font-bold leading-none tracking-tight tabular-nums text-ink">{count.toLocaleString()}</span>
}

export function GatewayStatusCounts({ counts }: { counts: Partial<Record<VerificationStatus, number>> }) {
  return (
    <dl className={`mt-3 ${statusGrid}`}>
      {statuses.filter((status) => counts[status] !== undefined).map((status) => <div key={status} className={statusCard}>
        <dt><StatusLabel status={status} /></dt>
        <dd><MetricValue count={counts[status] ?? 0} /></dd>
      </div>)}
    </dl>
  )
}

function EventDetails({ event, inHistory = false }: { event: VerificationEvent; inHistory?: boolean }) {
  return (
    <div className="space-y-3 text-sm leading-relaxed text-slate-700">
      {inHistory && <p className="font-semibold text-ink">{labels[event.status]}</p>}
      <p className="text-xs font-medium text-slate-500"><span className="capitalize">{event.method.replace(/_/g, ' ')}</span> · <time dateTime={event.verified_at}>{new Date(event.verified_at).toLocaleString()}</time></p>
      <ul className="list-disc space-y-1 pl-5 marker:text-teal">
        {event.findings.map((item) => <li key={item.code}>{item.reason}</li>)}
      </ul>
      {event.supporting_evidence.length > 0 && <div className="rounded-lg bg-slate-50 px-3 py-2.5">
        <p className="text-xs font-bold text-slate-600">Supporting records</p>
        <ul className="mt-1 space-y-1 break-all font-mono text-xs">
          {event.supporting_evidence.map((ref) => <li key={ref.record_id}>{ref.record_id} · Source {ref.source_id}</li>)}
        </ul>
      </div>}
      {event.limitations.map((item) => <p key={item} className="border-l-2 border-slate-200 pl-3 text-xs text-slate-600">{item}</p>)}
    </div>
  )
}

function RecordCard({ businessId, item }: { businessId: string; item: GatewayRecord }) {
  const [history, setHistory] = useState<VerificationEvent[]>([])
  const [cursor, setCursor] = useState<number | null>(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function loadHistory() {
    if (cursor === null) return
    setBusy(true)
    setError('')
    try {
      const page = await fetchVerificationHistory(businessId, item.provenance_id, cursor)
      setHistory((current) => [...current, ...page.items])
      setCursor(page.next_after)
    } catch {
      setError('Could not load verification history. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <article className="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 bg-slate-50/60 px-5 py-4">
        <div className="min-w-0">
          <p aria-hidden="true" className="text-xs font-semibold capitalize text-slate-500">{item.record_type}</p>
          <h3 className="mt-1 break-all text-base font-bold text-ink"><span className="sr-only">{item.record_type} </span>{item.record_reference ?? item.original_source_reference ?? item.record_id}</h3>
        </div>
        <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold ${palette[item.result.status].badge}`}>
          <span aria-hidden="true" className={`h-1.5 w-1.5 shrink-0 rounded-full ${palette[item.result.status].dot}`} />
          {labels[item.result.status]}
        </span>
      </header>
      <div className="space-y-4 p-5">
        <EventDetails event={item.result} />
        <details className="rounded-lg border border-slate-200 px-3 py-2.5 text-sm">
          <summary className="cursor-pointer font-semibold text-teal">Source provenance</summary>
          <dl className="mt-3 grid gap-3 break-all text-slate-700 sm:grid-cols-2">
            <div><dt className="font-semibold">Source type</dt><dd>{item.source_type.toLowerCase().replace(/_/g, ' ')}</dd></div>
            {item.source_id && <div><dt className="font-semibold">Source ID</dt><dd>{item.source_id}</dd></div>}
            {item.source_provider && <div><dt className="font-semibold">Provider as recorded</dt><dd>{item.source_provider}</dd></div>}
            {item.uploaded_at && <div><dt className="font-semibold">Uploaded</dt><dd>{new Date(item.uploaded_at).toLocaleString()}</dd></div>}
            {item.file_sha256 && <div className="sm:col-span-2"><dt className="font-semibold">Original file SHA-256</dt><dd className="font-mono">{item.file_sha256}</dd><dd className="mt-1 break-normal text-slate-600">The hash identifies file contents for comparison. It cannot establish that a transaction took place.</dd></div>}
            {item.consent_reference && <div><dt className="font-semibold">Consent reference</dt><dd>{item.consent_reference}</dd></div>}
          </dl>
        </details>
        {history.length > 0 && <ol aria-label="Verification history" className="ml-1 space-y-4 border-l border-teal/25 pl-4">
          {history.map((event) => <li key={event.event_id} className="relative before:absolute before:-left-[21px] before:top-2 before:h-2 before:w-2 before:rounded-full before:bg-teal"><EventDetails event={event} inHistory /></li>)}
        </ol>}
        {error && <p className="mt-3 text-sm text-rose-700" role="alert">{error}</p>}
        {cursor !== null && <button type="button" disabled={busy} className={control}
          onClick={() => void loadHistory()}>{busy ? 'Loading history…' : history.length ? 'Load more history' : 'Show verification history'}</button>}
      </div>
    </article>
  )
}

export function VerifiedEvidencePage({ canReconcile = false }: { canReconcile?: boolean }) {
  const { id = '' } = useParams()
  const [params] = useSearchParams()
  const incomingSearch = params.get('record') ?? params.get('source') ?? ''
  return <Gateway key={`${id}/${incomingSearch}`} id={id} canReconcile={canReconcile} initialSearch={incomingSearch} />
}

function Gateway({ id, canReconcile, initialSearch }: { id: string; canReconcile: boolean; initialSearch: string }) {
  const [page, setPage] = useState<Awaited<ReturnType<typeof fetchVerifiedEvidence>>>()
  const [counts, setCounts] = useState<Partial<Record<VerificationStatus, number>>>()
  const total = counts && statuses.reduce((sum, value) => sum + (counts[value] ?? 0), 0)
  const [selected, setSelected] = useState<GatewayRecord>()
  const [query, setQuery] = useState(initialSearch)
  const [search, setSearch] = useState(initialSearch)
  const [kind, setKind] = useState<GatewayFilters['kind']>()
  const [sort, setSort] = useState<GatewayFilters['sort']>()
  const [status, setStatus] = useState<VerificationStatus | ''>('')
  const [offset, setOffset] = useState(0)
  const [revision, setRevision] = useState(0)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let active = true
    setPage(undefined)
    setError('')
    const result = kind || search || sort
      ? fetchVerifiedEvidence(id, offset, status || undefined, { kind, search, sort })
      : fetchVerifiedEvidence(id, offset, status || undefined)
    void result
      .then((value) => {
        if (active) {
          setPage(value)
          setCounts(value.counts)
        }
      })
      .catch(() => { if (active) setError('The evidence gateway could not be loaded.') })
    return () => { active = false }
  }, [id, kind, offset, revision, search, sort, status])

  async function reconcile() {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const { records_updated } = await reconcileVerifiedEvidence(id)
      setNotice(records_updated === 0
        ? 'No verification results changed.'
        : `${records_updated} ${records_updated === 1 ? 'record' : 'records'} received updated results.`)
      setOffset(0)
      setRevision((value) => value + 1)
    } catch {
      setError('Could not compare supporting records. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  function filter(next: VerificationStatus | '') {
    setStatus(next)
    setOffset(0)
  }

  return (
    <main className="space-y-6">
      <header className="overflow-hidden rounded-2xl border border-white/10 bg-navy-950 bg-[radial-gradient(ellipse_at_top_right,_#14534f,_transparent_70%)] p-6 text-white shadow-sm sm:p-8">
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div>
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Verified Evidence Gateway</h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-300 sm:text-base">Inspect source provenance, verification findings, and the history behind each result.</p>
          </div>
          {canReconcile && <button type="button" onClick={() => void reconcile()} disabled={busy || !page}
            className="inline-flex min-h-11 items-center rounded-xl bg-emerald-300 px-4 py-2.5 text-sm font-bold text-navy-950 hover:bg-emerald-200 disabled:opacity-50">{busy ? 'Comparing…' : 'Compare supporting records'}</button>}
        </div>
      </header>

      {counts && Object.keys(counts).length > 0 && <section aria-label="Filter by verification status" className={statusGrid}>
        {statuses.filter((value) => counts[value] !== undefined).map((value) => <button type="button" key={value} aria-pressed={status === value}
          onClick={() => filter(status === value ? '' : value)}
          className={`${statusCard} shadow-sm hover:border-teal/50 hover:shadow-md ${status === value ? 'border-teal ring-1 ring-teal' : ''}`}>
          <StatusLabel status={value} />
          <MetricValue count={counts[value] ?? 0} />
        </button>)}
      </section>}

      <section aria-labelledby="verification-records" className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-200 pb-4">
          <div>
            <h2 id="verification-records" className="text-xl font-bold tracking-tight">Verification records</h2>
            {total !== undefined && <p className="mt-1 text-sm text-slate-600">
              {(page?.matching_count ?? (status ? counts?.[status] ?? 0 : total)).toLocaleString()} {status || kind || search ? 'matching records' : 'total records'}
            </p>}
          </div>
          <label className="grid gap-1 text-xs font-semibold text-slate-600">Verification status
            <select value={status} className={control} onChange={(event) => filter(event.target.value as VerificationStatus | '')}>
              <option value="">All statuses</option>
              {statuses.filter((value) => counts?.[value] !== undefined || status === value).map((value) => <option key={value} value={value}>{labels[value]}</option>)}
            </select>
          </label>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <form className="flex max-w-full flex-wrap items-end gap-2" onSubmit={(event) => { event.preventDefault(); setSearch(query.trim()); setOffset(0) }}>
            <label className="grid min-w-0 gap-1 text-xs font-semibold text-slate-600">Reference or source
              <input type="search" className="cw-input" maxLength={160} value={query} onChange={(event) => setQuery(event.target.value)} />
            </label>
            <button className="cw-button-secondary">Search</button>
          </form>
          <label className="grid gap-1 text-xs font-semibold text-slate-600">Record type
            <select className="cw-input" value={kind ?? ''} onChange={(event) => { setKind((event.target.value || undefined) as GatewayFilters['kind']); setOffset(0) }}>
              <option value="">All records</option><option value="transaction">Transactions</option><option value="invoice">Invoices</option><option value="obligation">Obligations</option>
            </select>
          </label>
          <label className="grid gap-1 text-xs font-semibold text-slate-600">Sort records
            <select className="cw-input" value={sort ?? 'recent'} onChange={(event) => { setSort(event.target.value as GatewayFilters['sort']); setOffset(0) }}>
              <option value="recent">Recently checked</option><option value="date">Latest record date</option><option value="amount">Highest amount</option><option value="reference">Reference A–Z</option>
            </select>
          </label>
        </div>
        {notice && <p role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-teal">{notice}</p>}
        {error && <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3">
          <p role="alert" className="text-sm text-rose-700">{error}</p>
          {!page && <button type="button" className={control} onClick={() => setRevision((value) => value + 1)}>Retry</button>}
        </div>}
        {!page && !error && <p role="status" className="rounded-xl border border-slate-200 bg-white px-5 py-6 text-sm text-slate-600">Loading verification records…</p>}
        {page?.items.length === 0 && <p className="rounded-xl border border-dashed border-slate-300 bg-white px-5 py-6 text-sm text-slate-600">{status || kind || search ? 'No records match the selected filters.' : 'Uploaded financial records will appear here.'}</p>}
        {page && page.items.length > 0 && <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white" tabIndex={0} role="region" aria-label="Verification record table">
          <table className="cw-table">
            <thead><tr>{['Reference', 'Source', 'Record date', 'Amount (INR)', 'Status', 'Review issues'].map((label) => <th key={label} scope="col">{label}</th>)}</tr></thead>
            <tbody>{page.items.map((item) => <tr key={item.provenance_id} className="hover:bg-slate-50">
              <td><button className="text-left font-bold text-teal hover:underline" type="button" onClick={() => setSelected(item)}>{item.record_reference ?? item.original_source_reference ?? item.record_id}</button>
                <span className="block text-xs capitalize text-slate-600">{item.record_type}</span></td>
              <td className="min-w-36 break-all">{item.source_label ?? item.source_type.toLowerCase().replace(/_/g, ' ')}</td>
              <td className="whitespace-nowrap">{item.record_date ?? '—'}</td>
              <td className="whitespace-nowrap tabular-nums">{item.amount_inr == null ? '—' : `₹${item.amount_inr}${item.record_type === 'obligation' ? ' / mo' : ''}`}</td>
              <td className="min-w-32"><span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${palette[item.result.status].badge}`}>{labels[item.result.status]}</span></td>
              <td className="tabular-nums">{item.result.status === 'REQUIRES_REVIEW' ? item.result.findings.length : 0}</td>
            </tr>)}</tbody>
          </table>
        </div>}
        {selected && <EvidenceDrawer title="Verification details" onClose={() => setSelected(undefined)}>
          <RecordCard key={selected.provenance_id} item={selected} businessId={id} />
          {selected.result.supporting_evidence.length > 0 && <ul className="mt-4 space-y-1 text-sm">{selected.result.supporting_evidence.map((ref) =>
            <li key={ref.record_id}><Link className="break-all font-semibold text-teal hover:underline" to={`?record=${encodeURIComponent(ref.record_id)}`} onClick={() => setSelected(undefined)}>Find supporting record {ref.record_id}</Link></li>)}</ul>}
        </EvidenceDrawer>}
        <Link className="inline-block text-sm font-semibold text-teal hover:underline" to={`/businesses/${id}/evidence-dna`}>Open Evidence DNA →</Link>
        {page && (offset > 0 || page.next_offset !== null) && <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4">
          <span className="text-sm tabular-nums text-slate-600">Showing {offset + 1}–{offset + page.items.length}</span>
          <div className="flex gap-2">
            <button type="button" className={control} disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 25))}>Previous</button>
            <button type="button" className={control} disabled={page.next_offset === null} onClick={() => setOffset(page.next_offset ?? offset)}>Next</button>
          </div>
        </div>}
      </section>
    </main>
  )
}
