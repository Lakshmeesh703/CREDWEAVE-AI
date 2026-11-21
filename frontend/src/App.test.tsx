import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { ApiError, fetchBusinesses, request } from './lib/api'

vi.mock('./lib/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./lib/api')>()),
  request: vi.fn(),
  fetchBusinesses: vi.fn(),
  fetchLenderQueue: vi.fn().mockResolvedValue([]),
}))

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function open(path: string) {
  window.history.replaceState(null, '', path)
  render(<App />)
}

function fillRegistration() {
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'owner@example.test' } })
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'example-password' } })
  fireEvent.change(screen.getByLabelText('Security question'), { target: { value: 'What is my private hint?' } })
  fireEvent.change(screen.getByLabelText('Security answer'), { target: { value: 'secret phrase' } })
}

describe('portal access', () => {
  it('offers login, registration, and the isolated demo on the landing page', () => {
    vi.mocked(request).mockImplementation(() => new Promise(() => {}))
    open('/')
    expect(screen.getByRole('link', { name: 'Login' })).toHaveAttribute('href', '/login')
    expect(screen.getByRole('link', { name: 'Register' })).toHaveAttribute('href', '/register')
    expect(screen.getByRole('link', { name: 'Explore the synthetic demo' })).toHaveAttribute('href', '/demo')
  })

  it('requires sign-in before opening a private business URL', async () => {
    vi.mocked(request).mockRejectedValue(new ApiError(401, 'Sign in to continue.'))
    open('/businesses/private-business/credit-passport')
    expect(await screen.findByRole('heading', { name: 'Sign in to CREDWEAVE AI' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/login')
  })

  it('lists all sign-in workspaces and routes an authenticated admin to account management', async () => {
    let signedIn = false
    vi.mocked(request).mockImplementation(async (path) => {
      if (path === '/api/me') {
        if (!signedIn) throw new ApiError(401, 'Sign in to continue.')
        return { id: 'admin-id', role: 'admin', demo: false }
      }
      if (path === '/api/admin/accounts') return { items: [], next_after: null }
      signedIn = true
      return { signed_in: true }
    })
    open('/login')
    const workspaces = within(screen.getByRole('navigation', { name: 'Sign-in workspaces' }))
    expect(workspaces.getByRole('link', { name: 'Business Owner' })).toHaveAttribute('aria-current', 'page')
    expect(workspaces.getByRole('link', { name: 'Lender' })).toHaveAttribute('href', '/login?role=lender')
    fireEvent.click(workspaces.getByRole('link', { name: 'Admin' }))
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'admin@example.test' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'example-password' } })
    fireEvent.click(screen.getByRole('button', { name: 'Login' }))
    expect(await screen.findByRole('heading', { name: 'Account administration' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/admin')
  })

  it('sends the selected login role and stays on sign-in when it is denied', async () => {
    vi.mocked(request).mockImplementation(async (path) => {
      if (path === '/api/me') throw new ApiError(401, 'Sign in to continue.')
      throw new ApiError(409, 'Wrong role')
    })
    open('/login?role=lender')
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'owner@example.test' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'legacy-pass' } })
    fireEvent.click(screen.getByRole('button', { name: 'Login' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Choose the sign-in option for your account role')
    expect(request).toHaveBeenCalledWith('/api/auth/login', expect.objectContaining({
      method: 'POST', body: JSON.stringify({ email: 'owner@example.test', password: 'legacy-pass', role: 'lender' }),
    }))
    expect(window.location.pathname).toBe('/login')
  })

  it('keeps an existing owner session out of the Admin sign-in page', async () => {
    vi.mocked(request).mockResolvedValue({ id: 'owner-id', role: 'owner', demo: false })
    open('/login?role=admin')
    expect(await screen.findByRole('button', { name: 'Sign out to switch accounts' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Login' })).not.toBeInTheDocument()
    expect(window.location.pathname + window.location.search).toBe('/login?role=admin')
  })

  it('shows and enforces the new-password policy before requesting registration', async () => {
    vi.mocked(request).mockImplementation(async () => { throw new ApiError(401, 'Sign in to continue.') })
    open('/register')
    fillRegistration()
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: '🔒'.repeat(19) } })
    fireEvent.click(screen.getByRole('button', { name: 'Register' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Use at least 15 characters and no more than 72 UTF-8 bytes.')
    expect(request).not.toHaveBeenCalledWith('/api/auth/register', expect.anything())
  })

  it('offers registration only for Business Owners and Lenders', () => {
    vi.mocked(request).mockImplementation(() => new Promise(() => {}))
    open('/register')
    const choices = within(screen.getByRole('navigation', { name: 'Account registration options' }))
    expect(choices.getByRole('link', { name: 'Business Owner' })).toHaveAttribute('href', '/register?role=owner')
    expect(choices.getByRole('link', { name: 'Lender' })).toHaveAttribute('href', '/register?role=lender')
    expect(choices.queryByRole('link', { name: 'Admin' })).not.toBeInTheDocument()
  })

  it('redirects a direct Admin registration link to Admin sign-in', async () => {
    vi.mocked(request).mockImplementation(() => new Promise(() => {}))
    open('/register?role=admin')
    expect(await screen.findByRole('heading', { name: 'Sign in to CREDWEAVE AI' })).toBeInTheDocument()
    expect(window.location.pathname + window.location.search).toBe('/login?role=admin')
    expect(screen.getByRole('link', { name: 'Admin' })).toHaveAttribute('aria-current', 'page')
    expect(screen.queryByRole('link', { name: /register/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Register' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Forgot password?' })).not.toBeInTheDocument()
  })

  it.each(['owner', 'lender'])('registers a %s applicant and opens the appropriate workspace', async (role) => {
    let signedIn = false
    vi.mocked(fetchBusinesses).mockResolvedValue([])
    vi.mocked(request).mockImplementation(async (path) => {
      if (path === '/api/me') {
        if (!signedIn) throw new ApiError(401, 'Sign in to continue.')
        return { id: 'owner-id', role: role === 'lender' ? 'lender_pending' : 'owner', demo: false }
      }
      signedIn = true
      return { signed_in: true, recovery_code: 'example-recovery-code' }
    })
    open(`/register?role=${role}`)
    fillRegistration()
    fireEvent.click(screen.getByRole('button', { name: 'Register' }))
    expect(await screen.findByText('example-recovery-code')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Continue to workspace' }))
    expect(await screen.findByRole('heading', { name: role === 'lender' ? 'Lender access pending' : 'Your businesses' })).toBeInTheDocument()
    expect(request).toHaveBeenCalledWith('/api/auth/register', expect.objectContaining({
      method: 'POST', body: JSON.stringify({
        email: 'owner@example.test', password: 'example-password', account_type: role,
        recovery: { question: 'What is my private hint?', answer: 'secret phrase' },
      }),
    }))
    if (role === 'lender') {
      expect(screen.getByText(/share your account ID with your CREDWEAVE AI admin/i)).toBeInTheDocument()
      expect(screen.queryByRole('heading', { name: 'Register a business' })).not.toBeInTheDocument()
    }
  })

  it('sends a pending lender back to their setup page after a reload', async () => {
    vi.mocked(request).mockResolvedValue({ id: 'pending-id', role: 'lender_pending', demo: false })
    open('/businesses')
    expect(await screen.findByRole('heading', { name: 'Lender access pending' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/lender-setup')
    expect(fetchBusinesses).not.toHaveBeenCalled()
    expect(screen.queryByRole('link', { name: 'Businesses' })).not.toBeInTheDocument()
  })

  it('opens the lender workspace after the Admin approves access', async () => {
    vi.mocked(request)
      .mockResolvedValueOnce({ id: 'pending-id', role: 'lender_pending', demo: false })
      .mockResolvedValueOnce({ id: 'pending-id', role: 'lender', demo: false })
    vi.mocked(fetchBusinesses).mockResolvedValue([])
    open('/lender-setup')
    fireEvent.click(await screen.findByRole('button', { name: 'Check approval status' }))
    expect(await screen.findByRole('heading', { name: 'Businesses shared with you' })).toBeInTheDocument()
  })

  it('asks the saved security question after a lender supplies a recovery code', async () => {
    vi.mocked(request).mockImplementation(async (path) => {
      if (path === '/api/me') throw new ApiError(401, 'Sign in to continue.')
      if (path === '/api/auth/recovery/question') return { question: 'What is my private hint?' }
      return { recovery_code: 'replacement-code' }
    })
    open('/login?role=lender')
    fireEvent.click(screen.getByRole('link', { name: 'Forgot password?' }))
    expect(screen.queryByLabelText('Security answer')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Saved recovery code'), { target: { value: 'example-recovery-code' } })
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
    expect(await screen.findByText('What is my private hint?')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Security answer'), { target: { value: 'secret phrase' } })
    fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'new-example-password' } })
    fireEvent.click(screen.getByRole('button', { name: 'Reset password' }))
    expect(await screen.findByText('replacement-code')).toBeInTheDocument()
  })

  it('allows showing and hiding the password without losing the entered value', () => {
    vi.mocked(request).mockImplementation(() => new Promise(() => {}))
    open('/login')
    const password = screen.getByLabelText('Password')
    fireEvent.change(password, { target: { value: 'test-hint' } })
    fireEvent.click(screen.getByRole('button', { name: 'Show password' }))
    expect(password).toHaveAttribute('type', 'text')
    expect(password).toHaveValue('test-hint')
    fireEvent.click(screen.getByRole('button', { name: 'Hide password' }))
    expect(password).toHaveAttribute('type', 'password')
  })

  it('waits for the provider email confirmation before signing in', async () => {
    vi.mocked(request).mockImplementation(async (path) => {
      if (path === '/api/me') throw new ApiError(401, 'Sign in to continue.')
      return { signed_in: false, confirmation_required: true }
    })
    open('/register?role=lender')
    fillRegistration()
    fireEvent.click(screen.getByRole('button', { name: 'Register' }))
    expect(await screen.findByRole('heading', { name: 'Check your email' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to sign-in' })).toHaveAttribute('href', '/login?role=lender')
  })

  it('holds off another registration attempt for the provider retry window', async () => {
    vi.mocked(request).mockImplementation(async (path) => {
      if (path === '/api/me') throw new ApiError(401, 'Sign in to continue.')
      throw new ApiError(429, 'Supabase has limited confirmation emails.', '60')
    })
    open('/register')
    fillRegistration()
    fireEvent.click(screen.getByRole('button', { name: 'Register' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Too many attempts. Please wait before trying again.')
    expect(screen.getByRole('button', { name: 'Register' })).toBeDisabled()
    expect(screen.getByRole('status')).toHaveTextContent('Try again after')
  })

  it('keeps backend configuration errors off the registration page', async () => {
    vi.mocked(request).mockImplementation(async (path) => {
      if (path === '/api/me') throw new ApiError(401, 'Sign in to continue.')
      throw new ApiError(503, 'Turn off Confirm email in Supabase Auth settings.')
    })
    open('/register')
    fillRegistration()
    fireEvent.click(screen.getByRole('button', { name: 'Register' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Account registration is temporarily unavailable.')
    expect(screen.queryByText(/Supabase Auth settings/)).not.toBeInTheDocument()
  })

  it('shows the lender empty state and hides owner registration', async () => {
    vi.mocked(request).mockResolvedValue({ id: 'lender-id', role: 'lender', demo: false })
    vi.mocked(fetchBusinesses).mockResolvedValue([])
    open('/businesses')
    expect(await screen.findByRole('heading', { name: 'Businesses shared with you' })).toBeInTheDocument()
    expect(await screen.findByText('No owner has shared a business with you yet.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Register a business' })).not.toBeInTheDocument()
  })
})
