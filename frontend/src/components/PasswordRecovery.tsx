import { useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { ApiError, request } from '../lib/api'
import { meetsPasswordRequirements, passwordRequirements, readRecoveryDetails } from '../lib/portal'

import { AuthLayout } from './AuthLayout'
import { ErrorState, PasswordField } from './ui'

const inputClass = 'cw-input'
const buttonClass = 'cw-button'

export function RecoveryFields() {
  return (
    <fieldset className="grid gap-4 rounded-lg border border-slate-200 p-4">
      <legend className="px-1 text-sm font-bold">Password recovery</legend>
      <p className="text-sm text-slate-600">Choose a private question and a secret answer. Save the recovery code you receive when you submit.</p>
      <label className="grid gap-1.5 text-sm font-semibold">
        Security question
        <input className={inputClass} name="recoveryQuestion" minLength={8} maxLength={160} required />
      </label>
      <label className="grid gap-1.5 text-sm font-semibold">
        Security answer
        <input className={inputClass} name="recoveryAnswer" type="password" autoComplete="off" minLength={8} maxLength={128} required />
      </label>
    </fieldset>
  )
}

export function RecoveryCodeCard({ code, children }: { code: string; children?: ReactNode }) {
  return (
    <section className="mt-6 rounded-lg border border-emerald-200 bg-emerald-50 p-5">
      <h2 className="text-lg font-bold">Save your recovery code</h2>
      <p className="mt-2 text-sm text-slate-700">Store this code somewhere safe. You’ll need it with your security answer to reset your password.</p>
      <code className="my-4 block select-all break-all rounded bg-white p-3 text-sm">{code}</code>
      {children}
    </section>
  )
}

export function RecoverySetupPage() {
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    const form = event.currentTarget
    const data = new FormData(form)
    setError('')
    setBusy(true)
    try {
      const result = await request<{ recovery_code: string }>('/api/auth/recovery/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recovery: readRecoveryDetails(data), password: data.get('password') }),
      })
      setCode(result.recovery_code)
      form.reset()
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401
        ? 'Check your current password and try again.'
        : 'We could not set up password recovery. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="mx-auto max-w-lg rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
      <h1 className="text-2xl font-bold">Password recovery</h1>
      {code ? <RecoveryCodeCard code={code}><Link to="/businesses" className={buttonClass}>Done</Link></RecoveryCodeCard> : (
        <form className="mt-6 grid gap-4" onSubmit={save}>
          <p className="text-sm text-slate-600">Set up recovery or replace your existing question and code.</p>
          <PasswordField label="Current password" name="password" autoComplete="current-password" required />
          <RecoveryFields />
          {error && <ErrorState>{error}</ErrorState>}
          <button disabled={busy} className={buttonClass}>Save recovery details</button>
        </form>
      )}
    </main>
  )
}

export function ForgotPasswordPage() {
  const [code, setCode] = useState('')
  const [question, setQuestion] = useState('')
  const [replacement, setReplacement] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function recover(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    const data = new FormData(event.currentTarget)
    setError('')
    setBusy(true)
    try {
      if (!question) {
        const enteredCode = String(data.get('code')).trim()
        const result = await request<{ question: string }>('/api/auth/recovery/question', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code: enteredCode }),
        })
        setCode(enteredCode)
        setQuestion(result.question)
      } else {
        const password = String(data.get('password') ?? '')
        if (!meetsPasswordRequirements(password)) {
          setError(passwordRequirements)
          return
        }
        const result = await request<{ recovery_code: string }>('/api/auth/recovery/reset', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code, answer: data.get('answer'), password }),
        })
        setReplacement(result.recovery_code)
        setCode('')
      }
    } catch (err) {
      const status = err instanceof ApiError ? err.status : undefined
      setError(status === 429 ? 'Too many attempts. Please wait before trying again.'
        : status === 403 ? (question ? 'Check your security answer.' : 'Check your saved recovery code.')
        : status === 422 ? (question ? 'Check your security answer and choose a valid new password.' : 'Check the format of your recovery code.')
        : 'Password recovery is temporarily unavailable. Please try again later.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout>
      <Link to="/login" className="mb-4 inline-block text-sm font-semibold text-teal">← Back to sign-in</Link>
        <h1 className="text-3xl font-bold">{replacement ? 'Password reset' : 'Reset your password'}</h1>
        {replacement ? <RecoveryCodeCard code={replacement}><Link to="/login" className={buttonClass}>Sign in</Link></RecoveryCodeCard> : (
          <form key={question ? 'answer' : 'code'} className="mt-6 grid gap-4" onSubmit={recover}>
            {question ? <>
              <label className="grid gap-1.5 text-sm font-semibold" htmlFor="recovery-answer">Security answer</label>
              <p id="recovery-question" className="text-sm text-slate-600">{question}</p>
              <input id="recovery-answer" aria-describedby="recovery-question" className={inputClass} name="answer" type="password" autoComplete="off" minLength={8} maxLength={128} required />
              <PasswordField label="New password" name="password" autoComplete="new-password" minLength={15} aria-describedby="reset-password-rules" required />
              <p id="reset-password-rules" className="text-sm text-slate-600">{passwordRequirements}</p>
              <button type="button" disabled={busy} className="justify-self-start text-sm font-semibold text-teal" onClick={() => { setCode(''); setQuestion(''); setError('') }}>Use a different recovery code</button>
            </> : <label className="grid gap-1.5 text-sm font-semibold">Saved recovery code
              <input className={inputClass} name="code" autoComplete="off" autoCapitalize="none" spellCheck={false} maxLength={40} required />
            </label>}
            {error && <ErrorState>{error}</ErrorState>}
            <button disabled={busy} className={buttonClass}>{busy ? 'Please wait…' : question ? 'Reset password' : 'Continue'}</button>
          </form>
        )}
    </AuthLayout>
  )
}
