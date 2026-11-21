import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { fetchFinancialSummary, type FinancialMetric, type FinancialSummary } from '../lib/api'

import { EmptyState, ErrorState, LoadingSkeleton, PageHeader } from './ui'

const labels: Record<string, string> = {
  total_inflows: 'Operating inflows',
  total_outflows: 'Operating outflows',
  net_operating_cash_flow: 'Net cash flow',
  expense_to_inflow_ratio: 'Expense / inflow',
  cash_flow_volatility: 'Cash-flow volatility',
  positive_months: 'Positive months',
  negative_months: 'Negative months',
  revenue_growth: 'Inflow growth proxy',
  supplier_concentration: 'Top supplier share',
  monthly_debt_obligations: 'Monthly obligations',
}

function MetricCard({ name, metric }: { name: string; metric: FinancialMetric }) {
  return <article className="cw-panel min-w-0">
    <p className="text-sm text-slate-500">{labels[name] ?? name}</p>
    <p className="mt-1 text-2xl font-bold text-ink">{metric.value === null ? 'Not available' : `${metric.value} ${metric.unit === 'INR' || metric.unit === 'INR per month' ? '₹' : metric.unit}`}</p>
    <p className="mt-2 text-xs text-slate-500">Formula: {metric.formula}</p>
    <p className="mt-1 text-xs text-slate-500">Coverage: {metric.data_coverage}</p>
    {metric.caveats.map((caveat) => <p key={caveat} className="mt-1 text-xs text-amber-700">{caveat}</p>)}
  </article>
}

export function FinancialHealthPage() {
  const { id = '' } = useParams()
  const [data, setData] = useState<FinancialSummary>()
  const [error, setError] = useState('')
  const [range, setRange] = useState('all')

  useEffect(() => {
    let active = true
    void fetchFinancialSummary(id).then((result) => { if (active) setData(result) })
      .catch(() => { if (active) setError('Could not load financial health for this business.') })
    return () => { active = false }
  }, [id])

  if (error) return <main className="mx-auto max-w-5xl px-6 py-10"><ErrorState>{error}</ErrorState></main>
  if (!data) return <main className="mx-auto max-w-5xl px-6 py-10"><LoadingSkeleton>Loading financial health…</LoadingSkeleton></main>

  const months = range === 'all' ? data.monthly : data.monthly.slice(-Number(range))
  return <main className="space-y-5">
    <PageHeader title="Financial Health" description={`Cash flow observed in the uploaded records for ${data.business_name}.`}
      action={<Link to={`/businesses/${id}/cashflow-twin`} className="cw-button-secondary">Open CashFlow Twin</Link>} />
    <div className="cw-panel text-sm text-slate-600">
      <p><strong className="text-ink">Operating classification.</strong> Eligible credits are operating inflows and may include receipts other than sales. Eligible debits are operating outflows.</p>
      <p className="mt-2">{data.coverage.date_window ?? 'No transaction window'} · {data.coverage.excluded_transaction_count} records excluded from operating totals.</p>
      <p className="mt-2">Use a single statement for UPI payments already recorded by your bank. Evidence checks surface possible overlaps for review.</p>
    </div>
    <section className="cw-panel min-w-0">
      <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-bold">Monthly cash flow</h2>
        {data.monthly.length > 0 && <label className="grid gap-1 text-sm font-semibold">Chart date range
          <select className="cw-input" value={range} onChange={(event) => setRange(event.target.value)}>
            <option value="all">All observed months</option><option value="3">Last 3 months</option><option value="6">Last 6 months</option><option value="12">Last 12 months</option>
          </select>
        </label>}
      </div>
      {!months.length ? <div className="mt-3"><EmptyState>Upload operating transactions to see monthly cash flow.</EmptyState></div> : <>
        <div className="mt-4 h-72"><ResponsiveContainer width="100%" height="100%">
          <LineChart data={months} accessibilityLayer><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="month" minTickGap={24} /><YAxis width={60} />
            <Tooltip formatter={(value) => `₹${value}`} /><Legend />
            <Line dataKey="inflows_inr" stroke="var(--cw-chart-inflow)" name="Inflows" isAnimationActive={false} />
            <Line dataKey="outflows_inr" stroke="var(--cw-chart-outflow)" name="Outflows" isAnimationActive={false} />
            <Line dataKey="net_cash_flow_inr" stroke="var(--cw-chart-net)" name="Net cash flow" isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer></div>
        <details className="mt-4"><summary className="cursor-pointer font-semibold text-teal">View monthly values</summary>
          <div className="mt-3 overflow-x-auto" tabIndex={0} role="region" aria-label="Monthly cash flow values"><table className="cw-table"><caption className="sr-only">Monthly cash flow in INR</caption>
            <thead><tr>{['Month', 'Inflows', 'Outflows', 'Net cash flow'].map((label) => <th scope="col" key={label}>{label}</th>)}</tr></thead>
            <tbody>{months.map((month) => <tr key={month.month}><th scope="row">{month.month}</th><td>₹{month.inflows_inr}</td><td>₹{month.outflows_inr}</td><td>₹{month.net_cash_flow_inr}</td></tr>)}</tbody>
          </table></div>
        </details>
      </>}
    </section>
    <section className="space-y-3"><h2 className="text-xl font-bold">Full-history metrics</h2>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{Object.entries(data.metrics).filter(([name]) => data.monthly.length > 0 || name === 'monthly_debt_obligations').map(([name, metric]) => <MetricCard key={name} name={name} metric={metric} />)}</div>
      <Link className="inline-block font-semibold text-teal hover:underline" to={`/businesses/${id}?records=obligations#processed-records`}>View recorded obligations</Link>
    </section>
    <section className="grid gap-4 md:grid-cols-2"><div className="cw-panel"><h2 className="text-lg font-bold text-ink">Seasonality</h2><p className="mt-2 text-sm text-slate-600">{data.seasonality.warning ?? `Seasonality classification: ${data.seasonality.label}.`}</p><p className="mt-2 text-xs text-slate-500">{data.seasonality.method}</p></div><div className="cw-panel"><h2 className="text-lg font-bold text-ink">Limitations</h2><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">{data.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div></section>
    <p className="mt-4 text-xs text-slate-500">Rule {data.rule_version} · Date window: {data.date_window.start ?? 'n/a'} to {data.date_window.end ?? 'n/a'} · Metrics are descriptive evidence, not lending decisions.</p>
  </main>
}
