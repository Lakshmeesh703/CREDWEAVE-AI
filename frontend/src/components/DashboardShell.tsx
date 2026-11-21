import { Activity, Building2, ChartSpline, ChevronRight, ClipboardCheck, FileBadge, Files, KeyRound, LayoutDashboard, ListChecks, Menu, Network, ScanLine, ShieldCheck, SlidersHorizontal, X } from 'lucide-react'
import { Fragment, useEffect, useState, type ReactNode } from 'react'
import { Link, matchPath, NavLink, useLocation, useNavigate } from 'react-router-dom'

import { fetchBusinesses, type Business } from '../lib/api'
import { businessStagePath, businessStages } from '../lib/businessRoutes'
import { demoBuild, portalUrl, roleLabels, workspacePath, type PortalUser } from '../lib/portal'

const navIcons = {
  Overview: LayoutDashboard, Businesses: Building2, Accounts: ShieldCheck, 'Lender setup': ListChecks,
  'Password recovery': KeyRound, 'Data Sources': Files, 'Verified Evidence Gateway': ScanLine, 'Evidence DNA': ClipboardCheck,
  'Trust Graph': Network, 'Financial Health': Activity, 'Risk Insights': ListChecks, 'CashFlow Twin': ChartSpline, 'Loan Options': SlidersHorizontal,
  'Credit Passport': FileBadge, 'Reviewer Desk': ClipboardCheck,
}

export function DashboardShell({ children, user, onSignOut }: {
  children: ReactNode
  user?: PortalUser
  onSignOut?: () => Promise<void>
}) {
  const location = useLocation()
  const navigate = useNavigate()
  const match = matchPath('/businesses/:id/*', location.pathname)
  const businessId = match?.params.id
  const stagePath = match?.params['*'] ? `/${match.params['*']}` : ''
  const activeStage = businessStages.find((stage) => stage.suffix === stagePath)
    ?? businessStages[0]
  const [navPath, setNavPath] = useState('')
  const menuOpen = navPath === location.pathname
  const [signOutError, setSignOutError] = useState('')
  const [businesses, setBusinesses] = useState<Business[]>([])
  const [businessesError, setBusinessesError] = useState(false)
  const inBusiness = Boolean(businessId)

  useEffect(() => {
    if (!inBusiness) return
    let cancelled = false
    setBusinessesError(false)
    void fetchBusinesses()
      .then((items) => { if (!cancelled) setBusinesses(items) })
      .catch(() => { if (!cancelled) setBusinessesError(true) })
    return () => { cancelled = true }
  }, [inBusiness])

  const navItems = [
    ...(!user ? [{ label: 'Overview', to: '/overview' }] : []),
    { label: user?.role === 'admin' ? 'Accounts' : user?.role === 'lender_pending' ? 'Lender setup' : 'Businesses',
      to: user ? workspacePath(user.role) : '/businesses' },
    ...(user && user.role !== 'admin' ? [{ label: 'Password recovery', to: '/account/recovery' }] : []),
    ...(!user || businessId ? businessStages.filter((stage) => {
      if (!user) return true
      if (stage.suffix === '/assess') return user.role === 'owner'
      return true
    }) : []).map(({ label, to, suffix }) => ({
      label,
      to: businessId ? businessStagePath(businessId, suffix) : to,
    })),
  ]

  return (
    <div className="cw-dashboard min-h-screen bg-navy-950 text-slate-100 md:grid md:grid-cols-[248px_minmax(0,1fr)]">
      <a href="#dashboard-content" className="no-print sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:p-3 focus:font-bold focus:text-teal">Skip to workspace content</a>
      <aside className="no-print border-b border-white/10 bg-navy-950 px-4 py-4 md:min-h-screen md:border-b-0 md:border-r md:px-5 md:py-6">
        <div className="flex items-center justify-between gap-2">
          <Link to={user ? workspacePath(user.role) : "/overview"} className="flex items-center gap-3 rounded-lg px-2 py-2" aria-label={user ? "CREDWEAVE AI workspace" : "CREDWEAVE AI overview"}>
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-emerald-300 text-navy-950"><ShieldCheck aria-hidden="true" size={21} /></span>
            <span><strong className="block text-sm tracking-wide">CREDWEAVE AI</strong><small className="text-slate-400">Credit intelligence</small></span>
          </Link>
          <button type="button" className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-slate-600 px-3 text-sm font-semibold md:hidden"
            aria-controls="dashboard-navigation" aria-expanded={menuOpen} onClick={() => setNavPath(menuOpen ? '' : location.pathname)}>
            {menuOpen ? <X aria-hidden="true" size={17} /> : <Menu aria-hidden="true" size={17} />} Menu
          </button>
        </div>
        <nav aria-label="Primary navigation" id="dashboard-navigation" className={`mt-3 grid-cols-2 gap-1 sm:grid-cols-3 md:mt-8 md:flex md:flex-col ${menuOpen ? 'grid' : 'hidden'}`}>
          {navItems.map(({ label, to }) => {
            const Icon = navIcons[label as keyof typeof navIcons]
            return <NavLink key={to} to={to} end
              className={({ isActive }) => `flex min-h-10 items-center gap-2.5 rounded-lg px-2.5 py-2.5 text-xs font-semibold md:text-sm ${isActive ? 'bg-emerald-400/15 text-emerald-300' : 'text-slate-300 hover:bg-white/5 hover:text-white'}`}>
              {Icon && <Icon size={17} className="shrink-0" aria-hidden="true" />}{label}
            </NavLink>
          })}
        </nav>
      </aside>
      <div className="cw-dashboard-content min-w-0 bg-mist text-ink">
        <header className="no-print flex min-h-16 flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-5 py-3 md:px-8">
          <nav aria-label="Breadcrumb" className="flex min-w-0 flex-wrap items-center gap-1.5 text-sm">
            <Link className="font-bold text-teal hover:underline" to={user ? workspacePath(user.role) : '/overview'}>Workspace</Link>
            <ChevronRight size={15} aria-hidden="true" className="text-slate-500" />
            <span aria-current="page" className="font-semibold text-slate-700">{businessId ? activeStage.label : (location.pathname.split('/')[1] || 'overview').replace(/-/g, ' ')}</span>
          </nav>
          <div className="flex max-w-full flex-wrap items-center gap-2">
            {businessId && (
              <label className="flex min-w-0 max-w-full flex-col gap-1 text-xs font-semibold text-slate-600">
                Active business
                <select
                  value={businessId}
                  onChange={(event) => navigate(businessStagePath(event.target.value, activeStage.suffix))}
                  className="max-w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-ink"
                >
                  {!businesses.some((business) => business.id === businessId) && (
                    <option value={businessId}>{businessesError ? 'Could not load business list' : 'Current business'}</option>
                  )}
                  {businesses.map((business) => <option key={business.id} value={business.id}>{business.name}</option>)}
                </select>
              </label>
            )}
            {user ? <>
              <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700">{roleLabels[user.role]}</span>
              <button type="button" onClick={() => void onSignOut?.().catch((err: Error) => setSignOutError(err.message))} className="text-sm font-semibold text-teal hover:underline">Sign out</button>
            </> : <>
              <span className="rounded-full bg-amber-100 px-3 py-1.5 text-xs font-bold text-amber-800">SYNTHETIC DEMO</span>
              {demoBuild && <a href={portalUrl} className="text-sm font-semibold text-teal hover:underline">Open sign-in portal</a>}
            </>}
          </div>
        </header>
        <div id="dashboard-content" tabIndex={-1} className="cw-dashboard-body mx-auto min-h-[calc(100vh-65px)] max-w-[1440px] px-4 py-6 md:px-8 md:py-8">
          {signOutError && <p role="alert" className="mb-4 text-sm text-rose-700">{signOutError}</p>}
          <Fragment key={businessId}>{children}</Fragment>
        </div>
      </div>
    </div>
  )
}
