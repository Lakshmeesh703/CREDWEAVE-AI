import { useEffect, useState, type FormEvent } from 'react'

import { EvidenceDrawer } from './EvidenceDrawer'
import { ErrorState, StatusBadge } from './ui'
import { ApiError, changeShare, fetchShares, type LenderShare } from '../lib/api'

export function LenderSharing({ businessId, onChange }: { businessId: string; onChange?: () => void }) {
  const [revoke, setRevoke] = useState<string>()
  const [shares, setShares] = useState<LenderShare[]>()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    void fetchShares(businessId).then(setShares).catch(() => setError('Could not load sharing permissions. Please try again.'))
  }, [businessId])

  async function change(lenderId: string, grant: boolean) {
    setBusy(true)
    setError('')
    setMessage('')
    try {
      await changeShare(businessId, lenderId, grant)
      onChange?.()
      setMessage(grant ? 'Lender access granted.' : 'Lender access revoked.')
      setRevoke(undefined)
      await fetchShares(businessId).then(setShares).catch(() => setError('Refresh this page to see the updated sharing list.'))
      return true
    } catch (err) {
      setError(err instanceof ApiError && err.status === 404 ? 'Confirm the approved lender’s account ID.' : 'Could not change lender access. Please try again.')
      return false
    } finally {
      setBusy(false)
    }
  }

  async function grant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const lenderId = String(new FormData(form).get('lender')).trim()
    if (await change(lenderId, true)) form.reset()
  }

  return (
    <section id="share-with-lender" className="cw-panel scroll-mt-4">
      <h2 className="text-xl font-bold">Share with a lender</h2>
      <p className="mt-2 text-sm text-slate-600">Ask your lender for their account ID. A grant lets that lender view this business’s current and future evidence and Credit Passports until you revoke access.</p>
      <form className="mt-4 space-y-3" onSubmit={grant}>
        <label className="block max-w-lg text-sm font-semibold">Lender account ID
          <input name="lender" required maxLength={36} className="cw-input mt-1 block w-full font-mono" />
        </label>
        <label className="flex gap-2 text-sm"><input type="checkbox" required /> I consent to sharing this business’s evidence and Credit Passport with this lender.</label>
        <button disabled={busy} className="cw-button">Grant lender access</button>
      </form>
      {error && <div className="mt-3"><ErrorState>{error}</ErrorState></div>}
      {message && <p role="status" className="mt-3 text-sm text-teal">{message}</p>}
      {shares?.length === 0 && <p className="mt-4 text-sm text-slate-600">No lenders have access to this business.</p>}
      {shares && shares.length > 0 && <ul className="mt-4 divide-y border-t">
        {shares.map((share) => <li className="flex flex-wrap justify-between gap-2 py-3 text-sm" key={share.lender_id}>
          <div><span className="block break-all font-mono">{share.lender_id}</span><span className="text-xs text-slate-600">Granted {new Date(share.granted_at).toLocaleDateString()}</span> <StatusBadge tone="positive">Active</StatusBadge></div>
          <button type="button" disabled={busy} onClick={() => setRevoke(share.lender_id)}
            aria-label={`Revoke access for ${share.lender_id}`} className="font-semibold text-rose-700 disabled:opacity-50">Revoke access</button>
        </li>)}
      </ul>}
      {revoke && <EvidenceDrawer title="Revoke lender access?" onClose={() => setRevoke(undefined)}>
        <p className="text-sm text-slate-600">This lender will lose access to the business’s records and Credit Passports.</p>
        {error && <div className="mt-3"><ErrorState>{error}</ErrorState></div>}
        <div className="mt-4 flex flex-wrap gap-2"><button type="button" className="cw-button-secondary" onClick={() => setRevoke(undefined)}>Cancel</button>
          <button type="button" className="cw-button" disabled={busy} onClick={() => void change(revoke, false)}>Revoke access</button></div>
      </EvidenceDrawer>}
    </section>
  )
}
