import { ArrowRight, ChartNoAxesCombined, FileCheck2, Network, ScanLine, ShieldCheck } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'

import { ApiError, request } from '../lib/api'
import { demoUrl, meetsPasswordRequirements, passwordRequirements, readRecoveryDetails, roleLabels, workspacePath, type PortalUser } from '../lib/portal'
import { AuthLayout, Brand, NetworkArt } from './AuthLayout'
import { ErrorState, PasswordField } from './ui'
import { RecoveryCodeCard, RecoveryFields } from './PasswordRecovery'

const registrationRoles = ['owner', 'lender'] as const
const portalRoles = [...registrationRoles, 'admin'] as const
const loginDescriptions: Record<(typeof portalRoles)[number], string> = {
  owner: 'Manage your businesses, uploaded evidence, and Credit Passports.',
  lender: 'Review businesses that have shared their evidence with you.',
  admin: 'Manage portal accounts and assign lender access.',
}

function authErrorMessage(error: unknown, register: boolean) {
  const status = error instanceof ApiError ? error.status : undefined
  if (status === 429) return 'Too many attempts. Please wait before trying again.'
  if (!register && status === 401) return 'Check your email and password and try again.'
  if (!register && status === 403) return 'Check whether your email needs confirmation before signing in.'
  if (!register && status === 409) return 'Choose the sign-in option for your account role and try again.'
  if (status === 422) return 'Check that your email and password meet the requirements.'
  return register
    ? 'Account registration is temporarily unavailable. Please try again later.'
    : 'Sign-in is temporarily unavailable. Please try again later.'
}

const pillars = [
  { title: 'Evidence DNA', text: 'Understand how complete your records are and where they agree.', icon: ScanLine },
  { title: 'Dynamic Trust Graph', text: 'Explore the links between counterparties, invoices, and payments.', icon: Network },
  { title: 'CashFlow Twin', text: 'Test how changes in receipts or costs affect repayment capacity.', icon: ChartNoAxesCombined },
  { title: 'Credit Passport', text: 'Share a dated evidence snapshot with a lender you choose.', icon: FileCheck2 },
]

export function LandingPage() {
  return <main className="min-h-screen bg-mist text-ink">
    <header className="border-b border-slate-200 bg-white">
      <nav aria-label="Main navigation" className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-5 py-4 sm:px-8">
        <Brand /><Link to="/login" className="cw-button-secondary">Login</Link>
      </nav>
    </header>
    <section className="bg-navy-950 bg-[radial-gradient(ellipse_at_top_right,_#154b48,_transparent_68%)] text-white">
      <div className="mx-auto grid max-w-7xl items-center gap-8 px-5 py-14 sm:px-8 lg:grid-cols-[1.2fr_.8fr] lg:py-24">
        <div>
          <h1 className="max-w-3xl text-4xl font-bold leading-[1.1] tracking-tight sm:text-5xl lg:text-6xl">Beyond Credit Scores. <span className="text-emerald-300">Building Verifiable Financial Trust.</span></h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-slate-300 sm:text-lg">Bring business records together, understand cash flow, and share traceable evidence for human lender review.</p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link to="/register" className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-emerald-300 px-4 text-sm font-bold text-navy-950 hover:bg-emerald-200">Register <ArrowRight size={17} aria-hidden="true" /></Link>
            <Link to="/demo" className="inline-flex min-h-11 items-center rounded-xl border border-white/30 px-4 text-sm font-semibold hover:bg-white/10">Explore the synthetic demo</Link>
          </div>
        </div>
        <div className="mx-auto hidden w-full sm:block"><NetworkArt /></div>
      </div>
    </section>
    <div className="mx-auto max-w-7xl space-y-12 px-5 py-10 sm:px-8 sm:py-14">
      <section aria-label="Choose your workspace" className="grid gap-4 sm:grid-cols-2">
        <article className="cw-panel"><h2 className="text-xl font-bold">Business owners</h2><p className="mt-2 text-slate-600">Organize your evidence, explore cash flow, and prepare a Credit Passport.</p><Link to="/register?role=owner" className="mt-4 inline-block font-bold text-teal hover:underline">Open a business owner account</Link></article>
        <article className="cw-panel"><h2 className="text-xl font-bold">Lenders</h2><p className="mt-2 text-slate-600">Review shared records, source checks, and affordability scenarios in one workspace.</p><div className="mt-4 flex flex-wrap gap-4 text-sm font-bold text-teal"><Link to="/login?role=lender" className="hover:underline">Lender sign-in</Link><Link to="/register?role=lender" className="hover:underline">Request lender access</Link></div></article>
      </section>
      <section><h2 className="text-2xl font-bold tracking-tight">How it works</h2>
        <ol className="mt-4 grid gap-4 sm:grid-cols-3">{[
          ['Collect evidence', 'Upload bank statements, invoices, and supplier records.'],
          ['Review the checks', 'Inspect supporting records, gaps, and cash flow scenarios.'],
          ['Share for review', 'Grant a selected lender access to your Credit Passport.'],
        ].map(([title, detail], index) => <li className="cw-panel" key={title}><span className="mb-3 grid h-8 w-8 place-items-center rounded-full bg-emerald-100 font-bold text-teal">{index + 1}</span><h3 className="font-bold">{title}</h3><p className="mt-1 text-sm text-slate-600">{detail}</p></li>)}</ol>
      </section>
      <section><h2 className="text-2xl font-bold tracking-tight">Tools for evidence-led review</h2><div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {pillars.map(({ title, text, icon: Icon }) => <article key={title} className="cw-panel"><Icon aria-hidden="true" className="text-teal" size={24} /><h3 className="mt-3 font-bold">{title}</h3><p className="mt-2 text-sm text-slate-600">{text}</p></article>)}
      </div></section>
      <p className="flex items-start gap-3 border-t border-slate-200 pt-5 text-sm text-slate-600"><ShieldCheck aria-hidden="true" size={21} className="shrink-0 text-teal" />You choose which lender gets access. CREDWEAVE AI provides evidence and affordability illustrations for human review.</p>
    </div>
  </main>
}

export function DemoEntryPage() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <Link to="/" className="font-semibold text-teal">← Home</Link>
      <h1 className="mt-6 text-4xl font-bold">Synthetic demo</h1>
      <p className="mt-4 text-slate-600">Explore two fictional businesses in an isolated workshop. The local jury launcher serves this demo at a separate address.</p>
      <a href={demoUrl} className="mt-6 inline-block rounded-lg bg-teal px-5 py-3 font-semibold text-white">Open synthetic demo</a>
    </main>
  )
}

export function AuthPage({ register, onLogin, activeUser, onSignOut }: {
  register: boolean
  onLogin: (user: PortalUser) => void
  activeUser?: PortalUser | null
  onSignOut?: () => Promise<void>
}) {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const selectedRole = portalRoles.find((role) => role === searchParams.get('role')) ?? 'owner'
  const authPath = register ? '/register' : '/login'
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [retryAt, setRetryAt] = useState(0)
  const [recoveryCode, setRecoveryCode] = useState('')
  const [confirmationRequired, setConfirmationRequired] = useState(false)
  const activeLoginRole = activeUser?.role === 'lender_pending' ? 'lender' : activeUser?.role

  useEffect(() => {
    if (!retryAt) return
    const timer = window.setTimeout(() => setRetryAt(0), Math.max(0, retryAt - Date.now()))
    return () => window.clearTimeout(timer)
  }, [retryAt])

  async function openWorkspace() {
    const account = await request<PortalUser>('/api/me')
    onLogin(account)
    navigate(workspacePath(account.role), { replace: true })
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy || retryAt || activeUser) return
    const data = new FormData(event.currentTarget)
    const password = String(data.get('password') ?? '')
    if (register && !meetsPasswordRequirements(password)) {
      setError(passwordRequirements)
      return
    }
    setBusy(true)
    setError('')
    try {
      const credentials = { email: data.get('email'), password }
      const result = await request<{ recovery_code?: string; confirmation_required?: boolean }>(register ? '/api/auth/register' : '/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(register
          ? { ...credentials, account_type: selectedRole, recovery: readRecoveryDetails(data) }
          : { ...credentials, role: selectedRole }),
      })
      if (result.confirmation_required) {
        setConfirmationRequired(true)
      } else if (result.recovery_code) {
        setRecoveryCode(result.recovery_code)
      } else {
        await openWorkspace()
      }
    } catch (err) {
      setError(authErrorMessage(err, register))
      if (err instanceof ApiError && err.status === 429 && err.retryAfter) {
        const now = Date.now()
        const time = /^\d+$/.test(err.retryAfter) ? now + Number(err.retryAfter) * 1000 : Date.parse(err.retryAfter)
        if (time > now && time - now <= 2_147_483_647) setRetryAt(time)
      }
    } finally {
      setBusy(false)
    }
  }

  if (register && selectedRole === 'admin') return <Navigate to="/login?role=admin" replace />
  if (!register && activeUser && activeLoginRole === selectedRole) return <Navigate to={workspacePath(activeUser.role)} replace />

  if (confirmationRequired) return <AuthLayout>
    <h1 className="text-3xl font-bold">Check your email</h1>
    <p className="my-4 text-sm text-slate-600">If registration can continue, you’ll receive a confirmation link. Open it before signing in. You can set up password recovery in your account after signing in.</p>
    <Link className="cw-button" to={`/login?role=${selectedRole}`}>Back to sign-in</Link>
  </AuthLayout>

  if (recoveryCode) return (
    <AuthLayout>
      <h1 className="text-3xl font-bold">Your account is ready</h1>
      <RecoveryCodeCard code={recoveryCode}>
        <button type="button" onClick={() => void openWorkspace().catch(() => setError('Please sign in to open your workspace.'))}
          className="rounded-lg bg-teal px-4 py-2.5 font-bold text-white">Continue to workspace</button>
        {error && <p role="alert" className="mt-3 text-sm text-rose-700">{error} <Link className="underline" to="/login">Sign in</Link></p>}
      </RecoveryCodeCard>
    </AuthLayout>
  )

  return (
    <AuthLayout>
        <h1 className="text-3xl font-bold">{register ? 'Create your account' : 'Sign in to CREDWEAVE AI'}</h1>
        <nav aria-label={register ? 'Account registration options' : 'Sign-in workspaces'} className={`mt-6 grid ${register ? 'grid-cols-2' : 'grid-cols-3'} gap-1 rounded-lg bg-slate-100 p-1`}>
          {(register ? registrationRoles : portalRoles).map((role) => (
            <Link key={role} to={`${authPath}?role=${role}`} aria-current={selectedRole === role ? 'page' : undefined}
              className={`rounded-md px-2 py-2 text-center text-sm font-semibold ${selectedRole === role ? 'bg-white text-teal shadow-sm' : 'text-slate-600 hover:bg-white/60'}`}>
              {roleLabels[role]}
            </Link>
          ))}
        </nav>
        <p className="mt-4 text-sm text-slate-600">{!register ? loginDescriptions[selectedRole] : selectedRole === 'lender'
          ? 'Register a dedicated account and give its account ID to a CREDWEAVE AI admin so they can grant lender access.'
          : 'Create an account to manage your business and prepare a Credit Passport.'}</p>
        {activeUser ? <div className="mt-6 space-y-4">
          <p className="text-sm text-slate-700">You’re signed in as {roleLabels[activeUser.role]}. Sign out to switch accounts.</p>
          {error && <ErrorState>{error}</ErrorState>}
          <button type="button" disabled={busy} className="cw-button"
            onClick={() => {
              setBusy(true)
              setError('')
              void onSignOut?.().catch(() => setError('Could not sign out. Please try again.')).finally(() => setBusy(false))
            }}>Sign out to switch accounts</button>
        </div> : <form onSubmit={submit} className="mt-6 grid gap-4">
          <label className="grid gap-1.5 text-sm font-semibold">Email<input className="cw-input" name="email" type="email" autoComplete="email" required /></label>
          <PasswordField name="password" minLength={register ? 15 : 1} aria-describedby={register ? 'registration-password-rules' : undefined} autoComplete={register ? 'new-password' : 'current-password'} required />
          {register && <p id="registration-password-rules" className="text-sm text-slate-600">{passwordRequirements}</p>}
          {register && <RecoveryFields />}
          {!register && selectedRole !== 'admin' && <Link to="/forgot-password" className="justify-self-start text-sm font-semibold text-teal hover:underline">Forgot password?</Link>}
          {error && <ErrorState>{error}</ErrorState>}
          {retryAt > 0 && <p role="status" className="text-sm text-slate-600">Try again after {new Date(retryAt).toLocaleTimeString()}.</p>}
          <button disabled={busy || retryAt > 0} className="cw-button">{busy ? 'Please wait…' : register ? 'Register' : 'Login'}</button>
        </form>}
        {!activeUser && selectedRole !== 'admin' && <Link className="mt-5 inline-block text-sm font-semibold text-teal hover:underline" to={`${register ? '/login' : '/register'}?role=${selectedRole}`}>{register ? 'Already registered? Sign in' : 'Register or learn how to get access'}</Link>}
    </AuthLayout>
  )
}
