import { useEffect, useState } from 'react'

import { request } from '../lib/api'
import { roleLabels, type Role } from '../lib/portal'

import { HealthStatus } from './HealthStatus'
import { EvidenceDrawer } from './EvidenceDrawer'
import { EmptyState, ErrorState, LoadingSkeleton, PageHeader, StatusBadge } from './ui'

type Account = { id: string; role: Role }
type AccountPage = { items: Account[]; next_after: string | null }

export function AdminPortal() {
  const [pending, setPending] = useState<Account>()
  const [page, setPage] = useState<AccountPage>()
  const [cursor, setCursor] = useState<string[]>([])
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const after = cursor[cursor.length - 1]

  useEffect(() => {
    let active = true
    setError('')
    setPage(undefined)
    void request<AccountPage>(`/api/admin/accounts${after ? `?after=${encodeURIComponent(after)}` : ''}`)
      .then((value) => { if (active) setPage(value) })
      .catch(() => { if (active) setError('Could not load the account directory.') })
    return () => { active = false }
  }, [after])

  async function update(account: Account) {
    const role = account.role === 'lender' ? 'owner' : 'lender'
    setBusy(account.id)
    setError('')
    setMessage('')
    try {
      const updated = await request<Account>(`/api/admin/accounts/${account.id}/role`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role }),
      })
      setPage((current) => current && { ...current, items: current.items.map((item) => item.id === updated.id ? updated : item) })
      setPending(undefined)
      setMessage(`Role updated to ${roleLabels[role]}.`)
    } catch {
      setError('Could not update the role. Check that this account is eligible for the change.')
    } finally {
      setBusy('')
    }
  }

  return (
    <main className="space-y-5">
      <PageHeader title="Account administration" description="Review portal account IDs and manage access for dedicated lenders." />
      <section className="cw-panel"><h2 className="mb-3 font-bold">System health</h2><HealthStatus /></section>
      {error && !pending && <ErrorState>{error}</ErrorState>}
      {message && <p role="status" className="rounded-lg bg-emerald-50 p-4 text-teal">{message}</p>}
      {!page && !error && <LoadingSkeleton>Loading accounts…</LoadingSkeleton>}
      {page && <section className="overflow-x-auto rounded-xl border border-slate-200 bg-white p-4">
        <table className="cw-table">
          <thead><tr><th scope="col" className="p-3">Account ID</th><th scope="col" className="p-3">Role</th><th scope="col" className="p-3">Action</th></tr></thead>
          <tbody>{page.items.map((account) => <tr className="border-t" key={account.id}>
            <td className="p-3 font-mono">{account.id}</td><td className="p-3"><StatusBadge tone={account.role === 'lender_pending' ? 'warning' : 'neutral'}>{roleLabels[account.role]}</StatusBadge></td>
            <td className="p-3">{account.role !== 'admin' && <button type="button" disabled={Boolean(busy)}
              aria-label={`${account.role === 'lender' ? 'Remove Lender access for' : 'Assign Lender to'} ${account.id}`}
              onClick={() => { setError(''); setPending(account) }} className="font-semibold text-teal hover:underline disabled:opacity-50">
              {account.role === 'lender_pending' ? 'Approve Lender' : account.role === 'owner' ? 'Assign Lender' : 'Remove Lender access'}
            </button>}</td>
          </tr>)}</tbody>
        </table>
        {page.items.length === 0 && <EmptyState>No accounts on this page.</EmptyState>}
        {(cursor.length > 0 || page.next_after) && <div className="mt-4 flex gap-4">
          <button disabled={Boolean(busy) || !cursor.length} onClick={() => setCursor((current) => current.slice(0, -1))} className="font-semibold text-teal disabled:opacity-50">Previous</button>
          <button disabled={Boolean(busy) || !page.next_after} onClick={() => setCursor((current) => page.next_after ? [...current, page.next_after] : current)} className="font-semibold text-teal disabled:opacity-50">Next</button>
        </div>}
      </section>}
      {pending && <EvidenceDrawer title="Confirm role change" onClose={() => setPending(undefined)}>
        <p className="break-all text-sm text-slate-600">{pending.role === 'lender' ? 'Remove lender access from' : 'Assign lender access to'} {pending.id}?</p>
        {error && <div className="mt-3"><ErrorState>{error}</ErrorState></div>}
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" className="cw-button-secondary" onClick={() => setPending(undefined)}>Cancel</button>
          <button type="button" className="cw-button" disabled={Boolean(busy)} onClick={() => void update(pending)}>Confirm change</button>
        </div>
      </EvidenceDrawer>}
    </main>
  )
}
