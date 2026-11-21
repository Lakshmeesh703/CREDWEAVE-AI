import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { ApiError, fetchLoanOptions, type LoanOptions } from '../lib/api'
import { EmptyState, ErrorState, LoadingSkeleton, PageHeader, StatusBadge } from './ui'

const tenures = [6, 12, 18, 24]
const initial = { principal_inr: '200000', annual_interest_rate_pct: 18, origination_fee_inr: '0', tenure_months: tenures, scenario_preset: 'normal' } satisfies Parameters<typeof fetchLoanOptions>[1]

export function LoanOptionsPage() {
  const { id = '' } = useParams()
  const [draft, setDraft] = useState<Parameters<typeof fetchLoanOptions>[1]>(initial)
  const [payload, setPayload] = useState(draft)
  const [data, setData] = useState<LoanOptions>()
  const [error, setError] = useState('')
  const [empty, setEmpty] = useState(false)
  const [busy, setBusy] = useState(true)

  useEffect(() => {
    let active = true
    setBusy(true)
    setError('')
    setEmpty(false)
    setData(undefined)
    void fetchLoanOptions(id, payload).then((options) => { if (active) setData(options) })
      .catch((err: unknown) => {
        if (!active) return
        if (err instanceof ApiError && err.status === 422 && err.message.includes('Upload operating transactions')) setEmpty(true)
        else setError(err instanceof ApiError && err.status === 422 ? 'Check your loan inputs and try again.' : 'Could not compare loan options. Please try again.')
      }).finally(() => { if (active) setBusy(false) })
    return () => { active = false }
  }, [id, payload])

  return <main className="space-y-5">
    <PageHeader title="Loan Options" description="Compare illustrative repayment terms using cash flow from the selected business. A lender makes the credit decision."
      action={<Link className="cw-button-secondary" to={`/businesses/${id}/cashflow-twin`}>CashFlow Twin</Link>} />
    <form className="cw-panel" onSubmit={(event) => { event.preventDefault(); setPayload({ ...draft }) }}>
      <h2 className="text-lg font-bold">Loan and scenario inputs</h2>
      <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <label className="grid gap-1 text-sm font-semibold">Principal (₹)<input type="number" min=".01" max="999999999999.99" step=".01" required className="cw-input w-full" value={draft.principal_inr} onChange={(event) => setDraft({ ...draft, principal_inr: event.target.value })} /></label>
        <label className="grid gap-1 text-sm font-semibold">Annual interest (%)<input type="number" min="0" max="100" step=".01" required className="cw-input w-full" value={Number.isNaN(draft.annual_interest_rate_pct) ? '' : draft.annual_interest_rate_pct} onChange={(event) => setDraft({ ...draft, annual_interest_rate_pct: event.target.valueAsNumber })} /></label>
        <label className="grid gap-1 text-sm font-semibold">Origination fee (₹)<input type="number" min="0" max="999999999999.99" step=".01" required className="cw-input w-full" value={draft.origination_fee_inr} onChange={(event) => setDraft({ ...draft, origination_fee_inr: event.target.value })} /></label>
        <label className="grid gap-1 text-sm font-semibold">Cash flow scenario<select className="cw-input w-full" value={draft.scenario_preset} onChange={(event) => setDraft({ ...draft, scenario_preset: event.target.value === 'combined_crisis' ? 'combined_crisis' : 'normal' })}>
          <option value="normal">Observed cash flow</option><option value="combined_crisis">Combined crisis</option>
        </select></label>
      </div>
      <fieldset className="mt-4"><legend className="text-sm font-bold">Terms to compare</legend><div className="mt-2 flex flex-wrap gap-2">
        {tenures.map((tenure) => <label key={tenure} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm">
          <input type="checkbox" checked={draft.tenure_months.includes(tenure)} onChange={(event) => setDraft({
            ...draft, tenure_months: event.target.checked ? [...draft.tenure_months, tenure] : draft.tenure_months.filter((value) => value !== tenure),
          })} />{tenure} months
        </label>)}
      </div></fieldset>
      <button disabled={busy || !draft.tenure_months.length} className="cw-button mt-4">{busy ? 'Comparing…' : 'Compare options'}</button>
      {!draft.tenure_months.length && <p className="mt-2 text-sm text-slate-600">Choose at least one term.</p>}
    </form>
    {busy && <LoadingSkeleton>Calculating repayment options…</LoadingSkeleton>}
    {error && <ErrorState>{error}</ErrorState>}
    {empty && <EmptyState action={<Link className="cw-button-secondary" to={`/businesses/${id}`}>Open Data Sources</Link>}>Upload operating transactions before comparing terms.</EmptyState>}
    {data && <>
      <section className="cw-panel text-sm text-slate-600" aria-label="Calculation assumptions">
        <p className="font-bold text-ink">₹{data.requested_principal_inr} principal · {data.annual_interest_rate_pct}% annual interest · ₹{data.origination_fee_inr} origination fee</p>
        <p className="mt-2">{data.provenance.scenario_scope}</p>
        <ul className="mt-2 list-disc space-y-1 pl-5">{data.assumptions.map((item) => <li key={item}>{item}</li>)}</ul>
      </section>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{data.options.map((option) => <article key={option.tenure_months} className="cw-panel">
        <h2 className="font-bold">{option.tenure_months} months</h2><p className="my-2 break-words text-2xl font-bold">₹{option.emi_inr}<span className="text-sm font-medium text-slate-600"> / month</span></p>
        <p className="mb-2 text-sm text-slate-600">₹{option.total_repayment_inr} total repayment</p><StatusBadge tone="warning">{option.affordability_status.replace(/_/g, ' ')}</StatusBadge>
      </article>)}</div>
      <section className="cw-panel min-w-0">
        <h2 className="text-lg font-bold">Repayment comparison</h2>
        <div className="mt-4 h-64"><ResponsiveContainer width="100%" height="100%">
          <BarChart data={data.options} accessibilityLayer><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="tenure_months" tickFormatter={(months) => `${months} mo`} /><YAxis width={58} />
            <Tooltip formatter={(value) => `₹${value}`} /><Legend /><Bar dataKey="emi_inr" fill="var(--cw-chart-inflow)" name="Monthly EMI" isAnimationActive={false} /><Bar dataKey="interest_cost_inr" fill="var(--cw-chart-outflow)" name="Total interest" isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer></div>
        <div className="mt-4 overflow-x-auto" role="region" aria-label="Loan comparison table" tabIndex={0}>
          <table className="cw-table"><thead><tr>{['Term', 'EMI', 'Interest', 'Total repayment', 'Cash after EMI', 'Minimum coverage', 'Rationale'].map((heading) => <th key={heading} scope="col">{heading}</th>)}</tr></thead>
            <tbody>{data.options.map((option) => <tr key={option.tenure_months}><th scope="row">{option.tenure_months} months</th>
              <td>₹{option.emi_inr}</td><td>₹{option.interest_cost_inr}</td><td>₹{option.total_repayment_inr}</td><td>₹{option.minimum_post_emi_cash_inr}</td><td>{option.minimum_dscr ?? 'Unavailable'}</td><td className="min-w-44">{option.affordability_rationale}</td>
            </tr>)}</tbody>
          </table>
        </div>
      </section>
    </>}
  </main>
}
