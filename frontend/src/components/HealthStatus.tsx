import { useEffect, useState } from 'react'

import { fetchHealth, type HealthResponse } from '../lib/api'

type HealthState =
  | { kind: 'loading' }
  | { kind: 'success'; data: HealthResponse }
  | { kind: 'error'; message: string }

export function HealthStatus() {
  const [health, setHealth] = useState<HealthState>({ kind: 'loading' })

  useEffect(() => {
    fetchHealth()
      .then((data) => setHealth({ kind: 'success', data }))
      .catch(() =>
        setHealth({
          kind: 'error',
          message: 'The local API is unavailable. Start the backend and refresh this page.',
        }),
      )
  }, [])

  if (health.kind === 'loading') {
    return <p className="text-sm text-slate-500">Checking local API...</p>
  }

  if (health.kind === 'error') {
    return (
      <p role="alert" className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
        {health.message}
      </p>
    )
  }

  return (
    <p className="rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
      CREDWEAVE AI API online · v{health.data.version} · {health.data.synthetic_demo ? 'synthetic demo mode' : 'portal mode'}
    </p>
  )
}
