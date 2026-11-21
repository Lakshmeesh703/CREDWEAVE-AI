import { useEffect, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'

import {
  ApiError, request, createBusiness, fetchBusiness, fetchBusinesses, fetchLenderQueue, fetchRecords, fetchSources, fetchSummary,
  setUploadConsent, updateBusiness, uploadEvidence, type Business, type BusinessDetails,
  type DataSource, type LenderQueueItem, type RecordKind, type RecordsSummary,
} from '../lib/api'
import type { PortalUser } from '../lib/portal'
import { LenderSharing } from './LenderSharing'

import { FileDropzone } from './FileDropzone'
import { OwnerProgress } from './OwnerProgress'
import { EmptyState, ErrorState, LoadingSkeleton, PageHeader, StatusBadge } from './ui'

const inputClass = 'cw-input mt-1 block w-full'
const buttonClass = 'cw-button'
const cardClass = 'cw-panel'

function ProfileFields({ business }: { business?: Business }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <label className="text-sm font-semibold">Business name<input name="name" defaultValue={business?.name} maxLength={160} required className={inputClass} /></label>
      <label className="text-sm font-semibold">Sector<input name="sector" defaultValue={business?.sector} maxLength={100} required className={inputClass} /></label>
      <label className="text-sm font-semibold">City<input name="city" defaultValue={business?.city} maxLength={100} required className={inputClass} /></label>
      <label className="text-sm font-semibold">Months in operation<input name="operating_months" defaultValue={business?.operating_months ?? 0} type="number" min={0} max={2147483647} required className={inputClass} /></label>
    </div>
  )
}

function readDetails(form: FormData): BusinessDetails {
  return {
    name: String(form.get('name')).trim(),
    sector: String(form.get('sector')).trim(),
    city: String(form.get('city')).trim(),
    operating_months: Number(form.get('operating_months')),
  }
}

export function BusinessPortal({ user, onRoleChange }: { user: PortalUser; onRoleChange: (account: PortalUser) => void }) {
  const navigate = useNavigate()
  const isLender = user.role === 'lender'
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('')
  const [selectedId, setSelectedId] = useState('')
  const [queue, setQueue] = useState<LenderQueueItem[]>()
  const [showRegister, setShowRegister] = useState(false)
  const [businesses, setBusinesses] = useState<Business[]>()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let active = true
    const load = isLender
      ? fetchLenderQueue().then((items) => { if (active) { setQueue(items); setBusinesses(items.map((item) => item.business)) } })
      : fetchBusinesses().then((items) => { if (active) setBusinesses(items) })
    void load.catch(() => { if (active) setError('Could not load your businesses. Please refresh and try again.') })
    return () => { active = false }
  }, [isLender])

  async function register(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const details = readDetails(new FormData(event.currentTarget))
    if (!details.name || !details.sector || !details.city) {
      setError('Enter the business name, sector, and city.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const business = await createBusiness({
        ...details, consent_status: 'pending', source_upload_consent: false,
      })
      navigate(`/businesses/${business.id}#upload-consent`)
    } catch (err) {
      setError(err instanceof ApiError && err.status === 422 ? 'Check the business details and try again.' : 'Could not register this business. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  async function requestLenderAccess() {
    setBusy(true)
    setError('')
    try {
      onRoleChange(await request<PortalUser>('/api/me/lender-access', { method: 'POST' }))
    } catch (err) {
      setError(err instanceof ApiError && err.status === 409
        ? 'Use a dedicated account for lender access if this account owns a business.'
        : 'Could not request lender access. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  function openRegistration() {
    if (showRegister && businesses?.length !== 0) {
      setShowRegister(false)
      return
    }
    setShowRegister(true)
    window.requestAnimationFrame(() => document.querySelector<HTMLInputElement>('#business-registration input')?.focus())
  }

  const active = businesses?.find((business) => business.id === selectedId) ?? businesses?.[0]
  const visible = businesses?.filter((business) => {
    const status = queue?.find((entry) => entry.business.id === business.id)?.review_status
    return (!filter || status === filter) && `${business.name} ${business.sector} ${business.city}`.toLowerCase().includes(query.trim().toLowerCase())
  })
  const statuses: Record<string, string> = { no_passport: 'Passport not ready', awaiting_review: 'Awaiting review', pending: 'Pending', needs_more_information: 'Needs more information', reviewed: 'Reviewed' }

  return (
    <main className="space-y-6">
      <PageHeader title={isLender ? 'Businesses shared with you' : 'Your businesses'}
        description={isLender ? 'Lender review queue for businesses that have granted you access.' : 'Manage your business evidence and see what to do next.'}
        action={!isLender && <button className="cw-button" type="button" onClick={openRegistration} aria-expanded={showRegister || businesses?.length === 0}>{showRegister && businesses?.length !== 0 ? 'Close registration' : 'Add business'}</button>} />
      {error && <ErrorState>{error}</ErrorState>}
      {!businesses && !error && <LoadingSkeleton>Loading businesses…</LoadingSkeleton>}
      {businesses?.length === 0 && <EmptyState>{isLender ? 'No owner has shared a business with you yet.' : 'Register your first business to start collecting evidence.'}</EmptyState>}
      {!isLender && active && <section className="space-y-3">
        {businesses && businesses.length > 1 && <label className="grid max-w-md gap-1 text-sm font-semibold">Active business
          <select className="cw-input" value={active.id} onChange={(event) => setSelectedId(event.target.value)}>
            {businesses.map((business) => <option key={business.id} value={business.id}>{business.name}</option>)}
          </select>
        </label>}
        <OwnerProgress key={active.id} business={active} />
      </section>}
      {!user.demo && <details className={cardClass}><summary className="cursor-pointer font-semibold">{isLender ? 'Your lender account ID' : 'Your account ID'}</summary>
        <code className="mt-2 block break-all text-sm">{user.id}</code>
        <p className="mt-1 text-sm text-slate-600">{isLender ? 'Give this ID to a business owner so they can grant you access.' : 'Use this ID when an administrator needs to locate your account.'}</p>
      </details>}
      {user.role === 'owner' && businesses?.length === 0 && (
        <section className={cardClass}>
          <h2 className="font-bold">Registered as a lender?</h2>
          <p className="mt-2 text-sm text-slate-600">Send this account for lender approval to open the lender workspace after an Admin approves it.</p>
          <button type="button" disabled={busy} className={buttonClass + ' mt-3'} onClick={() => void requestLenderAccess()}>Request lender access</button>
        </section>
      )}
      {businesses && businesses.length > 0 && <section aria-label={isLender ? 'Lender review queue' : 'Business directory'} className="space-y-3">
        <div className="flex flex-wrap items-end gap-3">
          <label className="grid min-w-0 max-w-full gap-1 text-sm font-semibold">Search businesses
            <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} className="cw-input" />
          </label>
          {isLender && <label className="grid min-w-0 max-w-full gap-1 text-sm font-semibold">Review status
            <select className="cw-input" value={filter} onChange={(event) => setFilter(event.target.value)}>
              <option value="">All statuses</option>{Object.entries(statuses).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>}
        </div>
        {visible?.length === 0 && <EmptyState>No businesses match these filters.</EmptyState>}
        <div className="grid gap-3 md:grid-cols-2">{visible?.map((business) => {
          const entry = queue?.find((item) => item.business.id === business.id)
          const path = `/businesses/${business.id}`
          return <article className={cardClass} key={business.id}>
            <h2 className="break-words text-lg font-bold">{business.name}</h2>
            <p className="mt-1 text-sm text-slate-600">{business.sector} · {business.city}</p>
            {entry && <p className="mt-3"><StatusBadge>{statuses[entry.review_status]}</StatusBadge></p>}
            <Link className="mt-3 inline-flex min-h-10 items-center text-sm font-bold text-teal hover:underline"
              to={entry?.assessment_id ? path + '/review' : path}>{entry?.assessment_id ? 'Open lender review' : 'Open business'}<span className="sr-only"> {business.name}</span> →</Link>
          </article>
        })}</div>
      </section>}
      {user.role === 'owner' && (showRegister || businesses?.length === 0) && <form onSubmit={register} className={cardClass + ' max-w-2xl space-y-4'} id="business-registration">
        <h2 className="text-xl font-bold">Register a business</h2>
        <p className="text-sm text-slate-600">Enter the business profile. You can choose whether to consent to evidence processing on the next screen.</p>
        <ProfileFields />
        <button disabled={busy || !businesses} className={buttonClass}>{busy ? 'Registering…' : 'Register business'}</button>
      </form>}
    </main>
  )
}

export function LenderSetupPage({ user, onRoleChange }: { user: PortalUser; onRoleChange: (account: PortalUser) => void }) {
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [checking, setChecking] = useState(false)

  async function checkApproval() {
    setMessage('')
    setError('')
    setChecking(true)
    try {
      const account = await request<PortalUser>('/api/me')
      if (account.role === 'lender_pending') setMessage('Your request is still pending approval.')
      else onRoleChange(account)
    } catch {
      setError('Could not check your approval status. Please try again.')
    } finally {
      setChecking(false)
    }
  }

  return (
    <main className={cardClass + ' max-w-2xl'}>
      <h1 className="text-3xl font-bold">Lender access pending</h1>
      <p className="mt-3 text-slate-600">Your lender registration is saved. Share your account ID with your CREDWEAVE AI admin so they can review and approve access.</p>
      <p className="mt-5 text-sm font-semibold">Your account ID</p>
      <code className="mt-1 block break-all rounded bg-slate-100 px-3 py-2">{user.id}</code>
      {message && <p role="status" className="mt-4 text-sm text-slate-600">{message}</p>}
      {error && <p role="alert" className="mt-4 text-sm text-rose-700">{error}</p>}
      <button type="button" disabled={checking} className={buttonClass + ' mt-5'} onClick={() => void checkApproval()}>
        {checking ? 'Checking…' : 'Check approval status'}
      </button>
    </main>
  )
}

const recordOptions: { kind: RecordKind; label: string; columns: [string, string][] }[] = [
  { kind: 'transactions', label: 'Transactions', columns: [['transaction_date', 'Date'], ['external_ref', 'Reference'], ['direction', 'Direction'], ['payment_channel', 'Channel'], ['amount_inr', 'Amount (INR)']] },
  { kind: 'invoices', label: 'Invoices', columns: [['invoice_no', 'Invoice'], ['issued_at', 'Issued'], ['direction', 'Direction'], ['status', 'Status'], ['total_inr', 'Total (INR)']] },
  { kind: 'counterparties', label: 'Suppliers and counterparties', columns: [['name', 'Name'], ['type', 'Type'], ['identifier_masked', 'Masked identifier']] },
  { kind: 'obligations', label: 'Obligations', columns: [['description', 'Description'], ['monthly_payment_inr', 'Monthly payment (INR)']] },
]

function RecordViewer({ id, revision }: { id: string; revision: number }) {
  const [params] = useSearchParams()
  const requestedIndex = recordOptions.findIndex((option) => option.kind === params.get('records'))
  const [index, setIndex] = useState(Math.max(0, requestedIndex))
  const [offset, setOffset] = useState(0)
  const [result, setResult] = useState<Awaited<ReturnType<typeof fetchRecords>>>()
  const [error, setError] = useState('')
  const { kind, columns } = recordOptions[index]
  useEffect(() => {
    let current = true
    setResult(undefined)
    setError('')
    void fetchRecords(id, kind, offset)
      .then((value) => { if (current) setResult(value) })
      .catch((err: Error) => { if (current) setError(err.message) })
    return () => { current = false }
  }, [id, kind, offset, revision])
  return (
    <section id="processed-records" className={cardClass}>
      <label className="block max-w-xs font-semibold">Browse processed records<select className={inputClass} value={index} onChange={(event) => { setIndex(Number(event.target.value)); setOffset(0) }}>
        {recordOptions.map((item, i) => <option key={item.kind} value={i}>{item.label}</option>)}
      </select></label>
      {error && <p role="alert" className="mt-3 text-rose-700">{error}</p>}
      {!result && !error && <p role="status" className="mt-3">Loading records…</p>}
      {result?.items.length === 0 && <p className="mt-3 text-slate-600">No records of this type have been imported.</p>}
      {result && result.items.length > 0 && <div className="mt-4 overflow-x-auto">
        <table className="cw-table"><thead><tr>{columns.map(([key, label]) => <th key={key} scope="col" className="px-2 py-1">{label}</th>)}</tr></thead>
          <tbody>{result.items.map((item) => <tr key={item.id} className="border-t">{columns.map(([key]) => <td key={key} className="px-2 py-2">{item[key] ?? '—'}</td>)}</tr>)}</tbody>
        </table>
      </div>}
      {result && (offset > 0 || result.next_offset !== null) && <div className="mt-3 flex gap-3">
        <button type="button" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 25))} className={buttonClass}>Previous</button>
        <button type="button" disabled={result.next_offset === null} onClick={() => setOffset(result.next_offset ?? offset)} className={buttonClass}>Next</button>
      </div>}
    </section>
  )
}

export function BusinessEvidencePortal({ user }: { user: PortalUser }) {
  const { id = '' } = useParams()
  const { hash } = useLocation()
  const [business, setBusiness] = useState<Business>()
  const [summary, setSummary] = useState<RecordsSummary>()
  const [sources, setSources] = useState<DataSource[]>([])
  const [revision, setRevision] = useState(0)
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const load = async () => {
    const [profile, records, imports] = await Promise.all([fetchBusiness(id), fetchSummary(id), fetchSources(id)])
    setBusiness(profile)
    setSummary(records)
    setSources(imports)
  }
  useEffect(() => {
    void Promise.all([fetchBusiness(id), fetchSummary(id), fetchSources(id)]).then(([profile, records, imports]) => {
      setBusiness(profile); setSummary(records); setSources(imports)
    }).catch((err: unknown) => setError(err instanceof ApiError && [403, 404].includes(err.status)
      ? 'This business is unavailable or you no longer have access.' : 'Could not load this business. Please try again.'))
  }, [id])

  useEffect(() => {
    if (business && /^#[a-z-]+$/.test(hash)) document.getElementById(hash.slice(1))?.scrollIntoView?.()
  }, [business, hash])

  async function perform(action: string, work: () => Promise<string>) {
    setBusy(action)
    setError('')
    setMessage('')
    try {
      setMessage(await work())
      await load().catch(() => setError('Your change was saved, but the latest records could not be loaded. Refresh this page.'))
      setRevision((value) => value + 1)
      return true
    } catch (err) {
      setError(err instanceof ApiError && [403, 409, 413, 422].includes(err.status) && !err.message.startsWith('API returned')
        ? err.message : 'Could not complete this action. Please try again.')
      return false
    } finally {
      setBusy('')
    }
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const details = readDetails(data)
    if (!details.name || !details.sector || !details.city) { setError('Enter the business name, sector, and city.'); return }
    await perform('profile', async () => {
      setBusiness(await updateBusiness(id, details))
      return 'Business profile saved.'
    })
  }

  if (!business) return <main>{error ? <ErrorState>{error}</ErrorState> : <LoadingSkeleton>Loading business…</LoadingSkeleton>}</main>
  const canUpload = business.source_upload_consent ?? business.consent_status === 'granted'
  return (
    <main className="space-y-6">
      <PageHeader title={business.name} description={`${business.sector} · ${business.city} · ${business.operating_months} months in operation`}
        action={<Link className="cw-button-secondary" to={`/businesses/${id}/verified-evidence`}>Open Evidence Gateway</Link>} />
      {error && <p role="alert" className="rounded-lg bg-rose-50 p-4 text-rose-700">{error}</p>}
      {message && <p role="status" className="rounded-lg bg-emerald-50 p-4 text-teal">{message}</p>}
      {user.role === 'owner' && <>
        <section id="upload-consent" className={cardClass + ' scroll-mt-4'}>
          <h2 className="text-xl font-bold">Evidence processing consent</h2>
          <p className="my-3 text-sm text-slate-600">Allow CREDWEAVE AI to import and analyze files you choose for this business. Lender sharing requires a separate grant.</p>
          <button type="button" disabled={Boolean(busy)} className={canUpload ? 'cw-button-secondary' : buttonClass}
            onClick={() => void perform('consent', async () => {
              setBusiness(await setUploadConsent(id, !canUpload))
              return canUpload ? 'Consent withdrawn for future uploads.' : 'Consent saved. You can upload evidence.'
            })}>{busy === 'consent' ? 'Saving…' : canUpload ? 'Withdraw upload consent' : 'Allow evidence processing'}</button>
        </section>
        <form onSubmit={saveProfile} className={cardClass + ' space-y-4'}>
          <h2 className="text-xl font-bold">Business profile</h2>
          <ProfileFields business={business} />
          <button className={buttonClass} disabled={Boolean(busy)}>{busy === 'profile' ? 'Saving…' : 'Save business profile'}</button>
        </form>
        <section id="upload-evidence" className={cardClass + ' scroll-mt-4'}>
          <h2 className="text-xl font-bold">Upload evidence</h2>
          <p className="mt-2 text-sm text-slate-600">Files must use the documented UTF-8 format and be at most 2 MiB. Use masked supplier and account identifiers.</p>
          {!canUpload && <p className="mt-2 text-sm text-amber-900">Allow evidence processing above to enable uploads.</p>}
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {([
              ['transactions', 'Bank statements', 'Includes UPI entries recorded in the statement.'],
              ['invoices', 'Invoices and supplier bills', 'Use one row per invoice.'],
              ['suppliers', 'Supplier directory', 'Use masked supplier identifiers.'],
              ['obligations', 'Payment obligations', 'Include recurring payment amounts.'],
            ] as const).map(([kind, title, description]) => (
              <FileDropzone key={kind} title={title} description={description} allowJson={kind === 'obligations'}
                disabled={!canUpload || Boolean(busy)} uploading={busy === kind}
                onUpload={(file) => perform(kind, async () => {
                  const result = await uploadEvidence(id, kind, file)
                  return `${result.accepted_rows} rows imported.${result.requires_review ? ` ${result.requires_review} transactions need review.` : ''}`
                })} />
            ))}
          </div>
          <details className="mt-4 text-sm"><summary className="cursor-pointer font-semibold text-teal">CSV headers</summary>
            <ul className="mt-2 space-y-2 break-all text-slate-600">
              <li>Transactions <code>external_ref,transaction_date,amount_inr,direction,payment_channel,description,currency</code></li>
              <li>Transactions can alternatively use <code>debit_inr,credit_inr</code> in place of <code>amount_inr,direction</code>. Optional columns include <code>balance_inr,source_provider</code>.</li>
              <li>Invoices <code>invoice_no,issued_at,due_at,total_inr,direction,status</code></li>
              <li>Supplier records use <code>direction=payable</code> on invoices. Both formats support <code>counterparty_name,counterparty_type,identifier_masked</code>.</li>
              <li>Supplier directory <code>counterparty_name,identifier_masked</code></li>
              <li>Obligations <code>monthly_payment_inr,description</code></li>
            </ul>
          </details>
        </section>
      </>}
      <section className={cardClass}>
        <h2 className="text-xl font-bold">Import history</h2>
        {summary && <p className="mt-2 text-sm text-slate-600">{Object.entries(summary.counts).map(([label, count]) => `${count} ${label}`).join(' · ')}</p>}
        {sources.length ? <ul className="mt-3 divide-y">{sources.map((source) => <li key={source.id} className="flex flex-wrap justify-between gap-2 py-3 text-sm"><strong className="break-all">{source.source_label}</strong><span>{source.synthetic ? 'Synthetic' : 'User upload'} · {source.kind} · {source.parsing_status} · {new Date(source.imported_at).toLocaleDateString()}</span></li>)}</ul> : <p className="mt-3 text-sm text-slate-600">No evidence files have been imported.</p>}
      </section>
      <RecordViewer id={id} revision={revision} />
      <Link to={`/businesses/${id}/verified-evidence`} className="inline-block font-semibold text-teal hover:underline">Open Verified Evidence Gateway →</Link>
      {user.role === 'owner' && <LenderSharing businessId={id} />}
    </main>
  )
}
