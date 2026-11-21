export const businessStages = [
  { label: 'Data Sources', to: '/data-sources', suffix: '' },
  { label: 'Verified Evidence Gateway', to: '/verified-evidence', suffix: '/verified-evidence' },
  { label: 'Evidence DNA', to: '/evidence-dna', suffix: '/evidence-dna' },
  { label: 'Trust Graph', to: '/trust-graph', suffix: '/trust-graph' },
  { label: 'Financial Health', to: '/financial-health', suffix: '/financial-health' },
  { label: 'Risk Insights', to: '/risk-insights', suffix: '/assess' },
  { label: 'CashFlow Twin', to: '/cashflow-twin', suffix: '/cashflow-twin' },
  { label: 'Loan Options', to: '/loan-options', suffix: '/loan-options' },
  { label: 'Credit Passport', to: '/credit-passport', suffix: '/credit-passport' },
  { label: 'Reviewer Desk', to: '/reviewer-desk', suffix: '/review' },
] as const

export function businessStagePath(businessId: string, suffix: string) {
  return `/businesses/${encodeURIComponent(businessId)}${suffix}`
}
