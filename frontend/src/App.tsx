import { lazy, Suspense, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes, useParams } from 'react-router-dom'

import { LoadingSkeleton } from './components/ui'
import { HealthStatus } from './components/HealthStatus'
import { VerifiedEvidencePage } from './components/VerifiedEvidencePage'
import { EvidenceDnaPage } from './components/EvidenceDnaPage'
import { AssessmentPage } from './components/AssessmentPage'
import { CreditPassportPage } from './components/CreditPassportPage'
import { ReviewWorkspacePage } from './components/ReviewWorkspacePage'
import { DashboardShell } from './components/DashboardShell'
import { OverviewPage } from './components/OverviewPage'
import { StageChooserPage } from './components/StageChooserPage'
import { ForgotPasswordPage, RecoverySetupPage } from './components/PasswordRecovery'
import { AdminPortal } from './components/AdminPortal'
import { AuthPage, DemoEntryPage, LandingPage } from './components/PortalEntry'
import { BusinessEvidencePortal, BusinessPortal, LenderSetupPage } from './components/BusinessPortal'
import { demoBuild, workspacePath, type PortalUser } from './lib/portal'
import {
  ApiError,
  request,
  createBusiness,
  fetchBusinesses,
  fetchHealth,
  fetchSummary,
  loadSyntheticDemo,
  type Business,
  type RecordsSummary,
  uploadEvidence,
} from './lib/api'

const TrustGraphPage = lazy(() => import('./components/TrustGraphPage').then((module) => ({ default: module.TrustGraphPage })))

const FinancialHealthPage = lazy(() => import('./components/FinancialHealthPage').then((module) => ({ default: module.FinancialHealthPage })))

const CashFlowTwinPage = lazy(() => import('./components/CashFlowTwinPage').then((module) => ({ default: module.CashFlowTwinPage })))

const LoanOptionsPage = lazy(() => import('./components/LoanOptionsPage').then((module) => ({ default: module.LoanOptionsPage })))

function ReviewWorkspace() {
  const [businesses, setBusinesses] = useState<Business[]>([])
  const [error, setError] = useState('')
  const [loadingDemo, setLoadingDemo] = useState(false)
  const [demoEnabled, setDemoEnabled] = useState(false)
  const [form, setForm] = useState({ name: '', sector: '', city: '', operating_months: 0, consent_status: 'pending' })
  const refresh = () => {
    void fetchBusinesses().then(setBusinesses).catch((err) => setError(err.message))
  }

  useEffect(refresh, [])
  useEffect(() => {
    void fetchHealth().then((health) => setDemoEnabled(health.synthetic_demo)).catch(() => setDemoEnabled(false))
  }, [])
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    try {
      await createBusiness(form)
      setForm({ name: '', sector: '', city: '', operating_months: 0, consent_status: 'pending' })
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create business.')
    }
  }
  const demo = async () => {
    setLoadingDemo(true)
    try { await loadSyntheticDemo(); refresh() } catch (err) { setError(err instanceof Error ? err.message : 'Could not load demo.') } finally { setLoadingDemo(false) }
  }

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-6 py-10">
      <Link to="/" className="mb-8 text-sm font-semibold text-teal hover:underline">
        ← Back to landing
      </Link>
      <h1 className="mt-8 text-4xl font-bold text-ink">Business onboarding</h1>
      <p className="mt-3 text-slate-600">Create a profile, then import evidence for that business. All demo records are synthetic.</p>
      {error && <p role="alert" className="mt-5 rounded-lg bg-rose-50 px-4 py-3 text-rose-700">{error}</p>}
      <form onSubmit={submit} className="mt-8 grid gap-3 rounded-xl bg-white p-5 shadow-sm md:grid-cols-5">
        {(['name', 'sector', 'city'] as const).map((field) => <input key={field} required value={form[field]} onChange={(e) => setForm({ ...form, [field]: e.target.value })} placeholder={field.replace('_', ' ')} className="rounded border border-slate-200 px-3 py-2" />)}
        <input required type="number" min="0" value={form.operating_months} onChange={(e) => setForm({ ...form, operating_months: Number(e.target.value) })} placeholder="operating months" className="rounded border border-slate-200 px-3 py-2" />
        <select value={form.consent_status} onChange={(e) => setForm({ ...form, consent_status: e.target.value })} className="rounded border border-slate-200 px-3 py-2"><option value="pending">Consent pending</option><option value="granted">Consent granted</option></select>
        <button className="rounded bg-teal px-4 py-2 font-semibold text-white md:col-span-5">Create business</button>
      </form>
      {demoEnabled && <button onClick={demo} disabled={loadingDemo} className="mt-4 rounded border border-teal px-4 py-2 font-semibold text-teal">{loadingDemo ? 'Loading synthetic demo...' : 'Load synthetic demo data'}</button>}
      <div className="mt-8 grid gap-4 md:grid-cols-2">
        {businesses.map((business) => <BusinessCard key={business.id} business={business} />)}
      </div>
      <div className="mt-8 max-w-md">
        <HealthStatus />
      </div>
    </main>
  )
}

function BusinessCard({ business }: { business: Business }) {
  return <Link to={`/businesses/${business.id}`} className="rounded-xl bg-white p-5 shadow-sm transition hover:ring-2 hover:ring-teal">
    <div className="flex items-start justify-between"><h2 className="text-xl font-bold text-ink">{business.name}</h2><span className="rounded-full bg-amber-50 px-2 py-1 text-xs text-amber-700">{business.consent_status}</span></div>
    <p className="mt-2 text-slate-600">{business.sector} · {business.city} · {business.operating_months} months</p>
    <p className="mt-4 text-sm font-semibold text-teal">Open profile →</p>
  </Link>
}

function BusinessProfile() {
  const { id = '' } = useParams()
  const [summary, setSummary] = useState<RecordsSummary>()
  const [message, setMessage] = useState('')
  useEffect(() => { fetchSummary(id).then(setSummary).catch((err) => setMessage(err.message)) }, [id])
  const importFile = async (kind: 'transactions' | 'invoices' | 'obligations', file?: File) => {
    if (!file) return
    try { const result = await uploadEvidence(id, kind, file); setMessage(`${result.accepted_rows} rows imported successfully.`); setSummary(await fetchSummary(id)) } catch (err) { setMessage(err instanceof Error ? err.message : 'Import failed.') }
  }
  return       <main className="mx-auto min-h-screen max-w-4xl px-6 py-10"><Link to="/review" className="text-sm font-semibold text-teal hover:underline">← Businesses</Link><h1 className="mt-8 text-4xl font-bold text-ink">Evidence intake</h1><p className="mt-3 text-slate-600">Upload strict UTF-8 CSV files or an obligations JSON file. Maximum size: 2 MB.</p>{message && <p role="status" className="mt-5 rounded-lg bg-slate-100 px-4 py-3 text-slate-700">{message}</p>}<div className="mt-8 grid gap-4 md:grid-cols-3">{(['transactions', 'invoices', 'obligations'] as const).map((kind) => <label key={kind} className="cursor-pointer rounded-xl bg-white p-5 shadow-sm"><span className="font-semibold capitalize text-ink">{kind}</span><span className="mt-2 block text-sm text-slate-500">Choose file</span><input type="file" accept={kind === 'obligations' ? '.csv,.json' : '.csv'} onChange={(e) => importFile(kind, e.target.files?.[0])} className="mt-4 block w-full text-sm" /></label>)}</div>{summary && <div className="mt-8 rounded-xl bg-teal/10 p-5"><p className="font-semibold text-teal">{summary.synthetic ? 'Synthetic demo data present' : 'Evidence summary'}</p><div className="mt-3 grid grid-cols-2 gap-3 text-sm md:grid-cols-5">{Object.entries(summary.counts).map(([name, count]) => <div key={name}><span className="block text-slate-500">{name}</span><strong className="text-xl text-ink">{count}</strong></div>)}</div><div className="mt-5 flex flex-wrap gap-3"><Link to={`/businesses/${id}/evidence-dna`} className="rounded bg-teal px-4 py-2 font-semibold text-white">View Evidence DNA</Link><Link to={`/businesses/${id}/trust-graph`} className="rounded border border-teal px-4 py-2 font-semibold text-teal">Trust Graph</Link><Link to={`/businesses/${id}/financial-health`} className="rounded border border-teal px-4 py-2 font-semibold text-teal">Financial Health</Link><Link to={`/businesses/${id}/assess`} className="rounded border border-teal px-4 py-2 font-semibold text-teal">Risk Assessment</Link><Link to={`/businesses/${id}/cashflow-twin`} className="rounded border border-teal px-4 py-2 font-semibold text-teal">CashFlow Twin</Link><Link to={`/businesses/${id}/loan-options`} className="rounded border border-teal px-4 py-2 font-semibold text-teal">Loan Options</Link>  <Link to={`/businesses/${id}/credit-passport`} className="rounded border border-teal px-4 py-2 font-semibold text-teal">Credit Passport</Link><Link to={`/businesses/${id}/review`} className="rounded bg-ink px-4 py-2 font-semibold text-white">Human Review</Link></div></div>}</main>
}

function App() {
  return <BrowserRouter basename={demoBuild ? '/demo' : '/'}><Suspense fallback={<div className="mx-auto max-w-xl p-6"><LoadingSkeleton>Opening workspace…</LoadingSkeleton></div>}>{demoBuild ? <DemoRoutes /> : <PortalRoutes />}</Suspense></BrowserRouter>
}

function PortalRoutes() {
  const [user, setUser] = useState<PortalUser | null>()
  const [error, setError] = useState('')
  useEffect(() => {
    const expired = () => setUser(null)
    window.addEventListener('credweave:session-expired', expired)
    void request<PortalUser>('/api/me').then(setUser).catch((err: Error) => {
      if (!(err instanceof ApiError && err.status === 401)) setError('We could not check your session. Please try signing in again.')
      setUser(null)
    })
    return () => window.removeEventListener('credweave:session-expired', expired)
  }, [])

  async function signOut() {
    await request('/api/auth/logout', { method: 'POST' })
    setUser(null)
  }

  function protectedPage(page: (account: PortalUser) => React.ReactNode, allowed?: PortalUser['role'][]) {
    if (user === undefined) return <main className="p-6" role="status">Checking your session…</main>
    if (!user) {
      const signIn = allowed?.length === 1 && allowed[0] === 'admin' ? '/login?role=admin'
        : allowed?.length === 1 && allowed[0] === 'lender_pending' ? '/login?role=lender' : '/login'
      return <Navigate to={signIn} replace />
    }
    const roles = allowed ?? ['owner', 'lender']
    if (!roles.includes(user.role)) return <Navigate to={workspacePath(user.role)} replace />
    return <DashboardShell user={user} onSignOut={signOut}>{page(user)}</DashboardShell>
  }

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/demo" element={<DemoEntryPage />} />
      <Route path="/login" element={<><AuthPage key="login" register={false} activeUser={user} onSignOut={signOut}
        onLogin={(account) => { setUser(account); setError('') }} />{error && <p className="mx-auto max-w-md px-6 text-sm text-rose-700" role="alert">{error}</p>}</>} />
      <Route path="/register" element={user ? <Navigate to={workspacePath(user.role)} replace /> : <AuthPage key="register" register onLogin={setUser} />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/account/recovery" element={protectedPage(() => <RecoverySetupPage />, ['owner', 'lender', 'lender_pending'])} />
      <Route path="/lender-setup" element={protectedPage((account) => <LenderSetupPage user={account} onRoleChange={setUser} />, ['lender_pending'])} />
      <Route path="/admin" element={protectedPage(() => <AdminPortal />, ['admin'])} />
      <Route path="/businesses" element={protectedPage((account) => <BusinessPortal user={account} onRoleChange={setUser} />)} />
      <Route path="/businesses/:id" element={protectedPage((account) => <BusinessEvidencePortal user={account} />)} />
      <Route path="/businesses/:id/verified-evidence" element={protectedPage((account) => <VerifiedEvidencePage canReconcile={account.role === 'owner'} />)} />
      <Route path="/businesses/:id/evidence-dna" element={protectedPage(() => <EvidenceDnaPage />)} />
      <Route path="/businesses/:id/trust-graph" element={protectedPage(() => <TrustGraphPage />)} />
      <Route path="/businesses/:id/financial-health" element={protectedPage(() => <FinancialHealthPage />)} />
      <Route path="/businesses/:id/assess" element={protectedPage(() => <AssessmentPage />, ['owner'])} />
      <Route path="/businesses/:id/cashflow-twin" element={protectedPage(() => <CashFlowTwinPage />)} />
      <Route path="/businesses/:id/loan-options" element={protectedPage(() => <LoanOptionsPage />)} />
      <Route path="/businesses/:id/credit-passport" element={protectedPage((account) => <CreditPassportPage canAssess={account.role === 'owner'} demo={false} />)} />
      <Route path="/businesses/:id/review" element={protectedPage((account) => <ReviewWorkspacePage demo={false} canReview={account.role === 'lender'} />)} />
      <Route path="*" element={<main className="p-8"><h1 className="text-2xl font-bold">Page not found</h1><Link to={user ? workspacePath(user.role) : '/'} className="mt-3 inline-block text-teal">Return to CREDWEAVE AI</Link></main>} />
    </Routes>
  )
}

function DemoRoutes() {
  return (
      <Routes>
        <Route path="/" element={<DashboardShell><OverviewPage /></DashboardShell>} />
        <Route path="/overview" element={<DashboardShell><OverviewPage /></DashboardShell>} />
        <Route path="/review" element={<DashboardShell><ReviewWorkspace /></DashboardShell>} />
        <Route path="/businesses" element={<DashboardShell><ReviewWorkspace /></DashboardShell>} />
        <Route path="/data-sources" element={<DashboardShell><StageChooserPage /></DashboardShell>} />
        <Route path="/verified-evidence" element={<DashboardShell><StageChooserPage /></DashboardShell>} />
        <Route path="/evidence-dna" element={<DashboardShell><StageChooserPage /></DashboardShell>} />
        <Route path="/trust-graph" element={<DashboardShell><StageChooserPage /></DashboardShell>} />
        <Route path="/financial-health" element={<DashboardShell><StageChooserPage /></DashboardShell>} />
        <Route path="/risk-insights" element={<DashboardShell><StageChooserPage /></DashboardShell>} />
        <Route path="/cashflow-twin" element={<DashboardShell><StageChooserPage /></DashboardShell>} />
        <Route path="/loan-options" element={<DashboardShell><StageChooserPage /></DashboardShell>} />
        <Route path="/credit-passport" element={<DashboardShell><StageChooserPage /></DashboardShell>} />
        <Route path="/reviewer-desk" element={<DashboardShell><StageChooserPage /></DashboardShell>} />
        <Route path="/businesses/:id" element={<DashboardShell><BusinessProfile /></DashboardShell>} />
        <Route path="/businesses/:id/verified-evidence" element={<DashboardShell><VerifiedEvidencePage canReconcile /></DashboardShell>} />
        <Route path="/businesses/:id/evidence-dna" element={<DashboardShell><EvidenceDnaPage /></DashboardShell>} />
        <Route path="/businesses/:id/trust-graph" element={<DashboardShell><TrustGraphPage /></DashboardShell>} />
        <Route path="/businesses/:id/financial-health" element={<DashboardShell><FinancialHealthPage /></DashboardShell>} />
        <Route path="/businesses/:id/assess" element={<DashboardShell><AssessmentPage /></DashboardShell>} />
        <Route path="/businesses/:id/cashflow-twin" element={<DashboardShell><CashFlowTwinPage /></DashboardShell>} />
        <Route path="/businesses/:id/loan-options" element={<DashboardShell><LoanOptionsPage /></DashboardShell>} />
        <Route path="/businesses/:id/credit-passport" element={<DashboardShell><CreditPassportPage /></DashboardShell>} />
        <Route path="/businesses/:id/review" element={<DashboardShell><ReviewWorkspacePage /></DashboardShell>} />
      </Routes>
  )
}

export default App
