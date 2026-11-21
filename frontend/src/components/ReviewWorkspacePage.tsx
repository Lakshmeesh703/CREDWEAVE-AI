import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { ApiError, createReview, fetchReviewWorkspace, updateConsent, type ReviewRecord, type ReviewWorkspace } from '../lib/api'
import { GatewayStatusCounts } from './VerifiedEvidencePage'
import { EmptyState, ErrorState, LoadingSkeleton, PageHeader, StatusBadge } from './ui'

const checklistLabels: Record<string, string> = {
  identity_reviewed: 'Business identity reviewed',
  evidence_findings_reviewed: 'Evidence findings reviewed',
  scenario_comparison_reviewed: 'Normal and crisis scenarios compared',
  limitations_acknowledged: 'Limitations acknowledged',
  human_decision_pending: 'Human decision remains pending',
}

const statuses: Record<ReviewRecord['status'], string> = {
  pending: 'Pending', needs_more_information: 'Needs more information', reviewed: 'Reviewed',
}

export function ReviewWorkspacePage({ demo = true, canReview = true }: { demo?: boolean; canReview?: boolean }) {
  const { id = '' } = useParams()
  const [workspace, setWorkspace] = useState<ReviewWorkspace>()
  const [unavailable, setUnavailable] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [reviewer, setReviewer] = useState('')
  const [reason, setReason] = useState('')
  const [status, setStatus] = useState<ReviewRecord['status']>('pending')
  const [checklist, setChecklist] = useState<Record<string, boolean>>({})
  const [busy, setBusy] = useState(false)
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    let active = true
    void fetchReviewWorkspace(id).then((result) => {
      if (active) { setWorkspace(result); setUnavailable(false) }
    }).catch((err: unknown) => {
      if (!active) return
      if (err instanceof ApiError && [403, 404].includes(err.status)) {
        setWorkspace(undefined)
        setUnavailable(true)
      } else setError('Could not load the review workspace. Please try again.')
    })
    return () => { active = false }
  }, [id, revision])

  async function saveReview() {
    if (!workspace) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await createReview(id, {
        reviewer_name_or_alias: demo ? reviewer : undefined,
        assessment_id: workspace.passport.assessment_id, status, reason, checklist,
      })
      setChecklist({})
      setReason('')
      setNotice('Review recorded.')
      setRevision((value) => value + 1)
    } catch (err) {
      setError(err instanceof ApiError && err.status === 409 ? 'A newer passport is available. Reload it before recording a review.' : 'Could not save the review. Please try again.')
      if (err instanceof ApiError && [403, 404, 409].includes(err.status)) setRevision((value) => value + 1)
    } finally {
      setBusy(false)
    }
  }

  async function saveConsent(kind: keyof ReviewWorkspace['consent'], enabled: boolean) {
    if (!workspace) return
    setError('')
    setBusy(true)
    try {
      const consent = { ...workspace.consent, [kind]: enabled }
      const current = await updateConsent(id, { source_upload_consent: consent.source_upload, passport_sharing_consent: consent.passport_sharing })
      setWorkspace({ ...workspace, consent: current })
    } catch {
      setError('Could not update consent. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  if (!workspace) return <main className="space-y-4">
    <PageHeader title="Reviewer Desk" />
    {error ? <ErrorState>{error}</ErrorState> : unavailable
      ? <EmptyState action={<Link className="cw-button-secondary" to="/businesses">Return to businesses</Link>}>This review is unavailable. A Credit Passport may still need to be generated, or sharing may have changed.</EmptyState>
      : <LoadingSkeleton>Loading review workspace…</LoadingSkeleton>}
  </main>

  const { passport } = workspace
  const evidence = passport.snapshot.evidence_dna
  return <main className="space-y-5">
    <PageHeader title="Reviewer Desk" description={workspace.business.name} action={<>
      {demo && <StatusBadge tone="demo">SYNTHETIC DEMO</StatusBadge>}
      <Link to={`/businesses/${id}/credit-passport`} className="cw-button-secondary">Open Credit Passport</Link>
      <Link to={`/businesses/${id}/verified-evidence`} className="cw-button-secondary">Inspect evidence</Link>
    </>} />
    <div className="rounded-xl bg-amber-50 p-4 text-sm text-amber-900"><strong>Human review.</strong> Record review progress, observations, and any information you still need.</div>
    {error && <ErrorState>{error}</ErrorState>}
    {notice && <p role="status" className="rounded-xl bg-emerald-50 p-4 text-sm text-emerald-900">{notice}</p>}
    <section className="cw-panel"><h2 className="text-lg font-bold">Evidence quality</h2>
      <p className="mt-2 text-sm text-slate-600">Completeness {evidence.evidence_completeness.denominator ? `${evidence.evidence_completeness.score}/100` : 'not assessed'} · Consistency {evidence.evidence_consistency.denominator ? `${evidence.evidence_consistency.score}/100` : 'not assessed'}</p>
      {evidence.gateway_status_counts && <GatewayStatusCounts counts={evidence.gateway_status_counts} />}
    </section>
    {demo && <section className="cw-panel">
      <h2 className="text-lg font-bold">Synthetic demo consent controls</h2>
      <div className="mt-3 flex flex-wrap gap-4">
        {([['source_upload', 'Allow source upload'], ['passport_sharing', 'Allow passport sharing and export']] as const).map(([kind, label]) =>
          <label key={kind} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={workspace.consent[kind]} disabled={busy}
            onChange={(event) => void saveConsent(kind, event.target.checked)} />{label}</label>)}
      </div>
    </section>}
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="cw-panel min-w-0">
        <h2 className="text-lg font-bold">Evidence findings</h2>
        {!workspace.evidence_findings.length ? <p className="mt-3 text-sm text-slate-600">No findings in this snapshot.</p> : <ul className="mt-3 space-y-3">
          {workspace.evidence_findings.map((item, index) => <li key={`${item.code}-${index}`} className="rounded-lg border border-slate-200 p-3 text-sm">
            <strong>{item.code.replace(/_/g, ' ')}</strong><p className="mt-1 text-slate-600">{item.explanation}</p>
            {item.record_ids.slice(0, 3).map((record) => <Link key={record} className="mt-2 block break-all font-semibold text-teal hover:underline"
              to={`/businesses/${id}/verified-evidence?record=${encodeURIComponent(record)}`}>Inspect {record}</Link>)}
          </li>)}
        </ul>}
      </section>
      <section className="cw-panel min-w-0">
        <h2 className="text-lg font-bold">Scenario comparison</h2>
        <dl className="mt-3 grid gap-3 sm:grid-cols-2">
          {([['Normal operations', workspace.scenario_comparison.normal], ['Combined crisis', workspace.scenario_comparison.combined_crisis]] as const).map(([label, twin]) =>
            <div key={label} className="rounded-lg border border-slate-200 p-3">
              <dt className="font-bold">{label}</dt><dd className="mt-2 text-sm">Minimum cash after EMI {twin.metrics.minimum_net_cash_after_emi_inr == null ? 'unavailable' : `₹${twin.metrics.minimum_net_cash_after_emi_inr}`}</dd>
            </div>)}
        </dl>
      </section>
    </div>
    {canReview && <form className="cw-panel space-y-4" onSubmit={(event) => { event.preventDefault(); void saveReview() }}>
      <h2 className="text-lg font-bold">Record a review</h2>
      <fieldset className="grid gap-2 md:grid-cols-2"><legend className="mb-2 text-sm font-bold">Checklist</legend>
        {workspace.checklist_keys.map((key) => <label key={key} className="flex items-center gap-2 text-sm"><input type="checkbox"
          checked={Boolean(checklist[key])} onChange={(event) => setChecklist({ ...checklist, [key]: event.target.checked })} />{checklistLabels[key] ?? key}</label>)}
      </fieldset>
      <div className="grid gap-3 md:grid-cols-2">
        {demo && <label className="grid gap-1 text-sm font-semibold">Reviewer alias<input value={reviewer} maxLength={120} required className="cw-input w-full" onChange={(event) => setReviewer(event.target.value)} /></label>}
        <label className="grid gap-1 text-sm font-semibold">Review status<select className="cw-input w-full" value={status} onChange={(event) => setStatus(event.target.value as ReviewRecord['status'])}>
          {Object.entries(statuses).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select></label>
        <label className="grid gap-1 text-sm font-semibold md:col-span-2">Review notes<textarea className="cw-input w-full" value={reason} maxLength={4000} rows={4} required
          onChange={(event) => setReason(event.target.value)} placeholder="Add your rationale and any records you need to see." /></label>
      </div>
      <button className="cw-button" disabled={busy || !reason.trim() || (demo && !reviewer.trim())}>{busy ? 'Saving…' : 'Record manual review'}</button>
    </form>}
    <section className="cw-panel"><h2 className="text-lg font-bold">Review history</h2>
      {workspace.reviews.length ? <ul className="mt-3 divide-y divide-slate-200">{workspace.reviews.map((review) => <li key={review.id} className="py-3 text-sm">
        <StatusBadge>{statuses[review.status]}</StatusBadge> · {review.reviewer_name_or_alias} · {new Date(review.updated_at).toLocaleString()}
        <p className="mt-2 break-words text-slate-600">{review.reason}</p><p className="mt-1 text-xs text-slate-600">Rule version {review.rule_version}</p>
      </li>)}</ul> : <p className="mt-3 text-sm text-slate-600">No review entries yet.</p>}
    </section>
  </main>
}
