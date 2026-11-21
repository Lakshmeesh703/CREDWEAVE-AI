export type Role = 'owner' | 'lender' | 'lender_pending' | 'admin'
export type PortalUser = { id: string; role: Role; demo: boolean }

export const passwordRequirements = 'Use at least 15 characters and no more than 72 UTF-8 bytes.'

export function meetsPasswordRequirements(password: string) {
  return Array.from(password).length >= 15 && Boolean(password.trim()) && new TextEncoder().encode(password).length <= 72
}

export const demoBuild = import.meta.env.MODE === 'jury'
export const demoUrl = import.meta.env.VITE_DEMO_URL ?? 'http://127.0.0.1:8080/demo'
export const portalUrl = import.meta.env.VITE_PORTAL_URL ?? 'http://localhost:5173/'
export const roleLabels: Record<Role, string> = {
  owner: 'Business Owner',
  lender: 'Lender',
  lender_pending: 'Lender pending approval',
  admin: 'Admin',
}

export function readRecoveryDetails(data: FormData) {
  return { question: data.get('recoveryQuestion'), answer: data.get('recoveryAnswer') }
}

export function workspacePath(role: Role) {
  if (role === 'admin') return '/admin'
  if (role === 'lender_pending') return '/lender-setup'
  return '/businesses'
}
