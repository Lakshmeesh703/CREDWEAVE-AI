import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { ApiError, fetchStressPresets, runStressTest, type StressTest, type StressTestRequest } from '../lib/api'
import { EmptyState, ErrorState, LoadingSkeleton, MetricCard, PageHeader } from './ui'

const baseline: StressTestRequest = {
  revenue_shock_pct: 0, expense_shock_pct: 0, payment_delay_days: 0,
  duration_months: 6, selected_loan_emi: '0', seasonal_weaker_months: 0,
}

export function CashFlowTwinPage() {
  const { id = '' } = useParams()
  const [draft, setDraft] = useState(baseline)
  const [request, setRequest] = useState(baseline)
  const [presets, setPresets] = useState<Awaited<ReturnType<typeof fetchStressPresets>>['presets']>({})
  const [data, setData] = useState<StressTest>()
  const [error, setError] = useState('')
  const [empty, setEmpty] = useState(false)
  const [busy, setBusy] = useState(true)

  useEffect(() => {
    let active = true
    void fetchStressPresets(id).then(({ presets: choices }) => { if (active) setPresets(choices) }).catch(() => {})
    return () => { active = false }
  }, [id])

  useEffect(() => {
    let active = true
    setBusy(true)
    setError('')
    setEmpty(false)
    setData(undefined)
    void runStressTest(id, request).then((result) => { if (active) setData(result) })
      .catch((err: unknown) => {
        if (!active) return
        if (err instanceof ApiError && err.status === 422 && err.message.includes('Upload operating transactions')) setEmpty(true)
        else setError(err instanceof ApiError && err.status === 422 ? 'Check your scenario inputs and try again.' : 'Could not calculate this scenario. Please try again.')
      }).finally(() => { if (active) setBusy(false) })
    return () => { active = false }
  }, [id, request])

  function applyScenario(next: StressTestRequest) {
    setDraft(next)
    setRequest({ ...next })
  }

  return <main className="space-y-5">
    <PageHeader title="CashFlow Twin" description="Explore how changes to receipts, expenses, and payment timing could affect cash available for repayment."
      action={<Link className="cw-button-secondary" to={`/businesses/${id}/loan-options`}>Continue to Loan Options</Link>} />
    <section className="cw-panel">
      <h2 className="text-lg font-bold">Scenario presets</h2>
      <div className="mt-3 flex flex-wrap gap-2">
        {Object.entries(presets).map(([key, { label, ...preset }]) => <button type="button" key={key} className="cw-button-secondary"
          onClick={() => applyScenario({ ...baseline, ...preset })}>{label}</button>)}
        <button type="button" className="cw-button-secondary" onClick={() => applyScenario({ ...baseline, payment_delay_days: 30 })}>Delayed payments</button>
        <button type="button" className="cw-button-secondary" onClick={() => applyScenario(baseline)}>Reset to baseline</button>
      </div>
      <form className="mt-6 border-t border-slate-200 pt-5" onSubmit={(event) => { event.preventDefault(); setRequest({ ...draft }) }}>
        <h2 className="text-lg font-bold">Scenario inputs</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {([
            ['revenue_shock_pct', 'Inflow change (%)', -100, 100],
            ['expense_shock_pct', 'Expense change (%)', -100, 500],
            ['payment_delay_days', 'Payment delay (days)', 0, 365],
            ['duration_months', 'Scenario duration (months)', 1, 24],
            ['seasonal_weaker_months', 'Weaker months', 0, 24],
          ] as const).map(([key, label, min, max]) => <label key={key} className="grid gap-1 text-sm font-semibold">{label}
            <input type="number" min={min} max={max} required className="cw-input w-full" value={Number.isNaN(draft[key]) ? '' : draft[key]}
              onChange={(event) => setDraft({ ...draft, [key]: event.target.valueAsNumber })} />
          </label>)}
          <label className="grid gap-1 text-sm font-semibold">Loan EMI (₹)
            <input type="number" min="0" max="999999999999.99" step=".01" required className="cw-input w-full" value={draft.selected_loan_emi}
              onChange={(event) => setDraft({ ...draft, selected_loan_emi: event.target.value })} />
          </label>
        </div>
        <button className="cw-button mt-4" disabled={busy}>{busy ? 'Calculating…' : 'Recalculate scenario'}</button>
      </form>
    </section>
    {busy && <LoadingSkeleton>Calculating cash flow from business records…</LoadingSkeleton>}
    {error && <ErrorState>{error}</ErrorState>}
    {empty && <EmptyState action={<Link className="cw-button-secondary" to={`/businesses/${id}`}>Open Data Sources</Link>}>Upload operating transactions to run a cash flow scenario.</EmptyState>}
    {data && <>
      <dl className="grid gap-3 sm:grid-cols-3">
        <MetricCard label="Minimum cash after EMI" value={`₹${data.metrics.minimum_net_cash_after_emi_inr}`} />
        <MetricCard label="Receipts delayed beyond horizon" value={`₹${data.metrics.receipts_delayed_beyond_horizon_inr}`} />
        <MetricCard label="Payment timing shift" value={`${data.scenario.payment_delay_months} month(s)`} />
      </dl>
      <section className="cw-panel min-w-0">
        <h2 className="text-lg font-bold">Observed and scenario cash flow</h2>
        <div className="mt-4 h-72 min-w-0">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.monthly} accessibilityLayer><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="month_number" /><YAxis width={58} />
              <Tooltip formatter={(value) => `₹${value}`} /><Legend />
              <Line dataKey="base_inflows_inr" stroke="#64748b" name="Observed inflow" isAnimationActive={false} />
              <Line dataKey="projected_inflows_inr" stroke="var(--cw-chart-inflow)" name="Scenario inflow" isAnimationActive={false} />
              <Line dataKey="net_cash_after_emi_inr" stroke="var(--cw-chart-net)" name="Scenario cash after EMI" isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-4 overflow-x-auto" role="region" aria-label="Month-by-month scenario" tabIndex={0}>
          <table className="cw-table"><caption className="sr-only">Monthly comparison, amounts in INR</caption>
            <thead><tr>{['Month', 'Observed inflow', 'Scenario inflow', 'Scenario outflow', 'Before EMI', 'After EMI', 'EMI coverage'].map((heading) => <th key={heading} scope="col">{heading}</th>)}</tr></thead>
            <tbody>{data.monthly.map((item) => <tr key={item.month_number}><th scope="row">{item.month_number}</th><td>₹{item.base_inflows_inr}</td><td>₹{item.projected_inflows_inr}</td><td>₹{item.projected_outflows_inr}</td><td>₹{item.net_cash_before_emi_inr}</td><td className={Number(item.net_cash_after_emi_inr) < 0 ? 'font-bold text-rose-800' : ''}>₹{item.net_cash_after_emi_inr}</td><td>{item.emi_coverage_ratio ?? 'Unavailable'}</td></tr>)}</tbody>
          </table>
        </div>
      </section>
      <section className="cw-panel"><h2 className="font-bold">Scenario assumptions</h2><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">{[...new Set([...data.assumptions, ...data.warnings])].map((item) => <li key={item}>{item}</li>)}</ul></section>
    </>}
  </main>
}
