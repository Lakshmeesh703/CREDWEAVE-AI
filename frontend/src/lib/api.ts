export type HealthResponse = {
  status: string
  service: string
  version: string
  synthetic_demo: boolean
}

export type Business = {
  id: string
  name: string
  sector: string
  operating_months: number
  city: string
  consent_status: string
  source_upload_consent?: boolean | null
  passport_sharing_consent?: boolean | null
  created_at: string
}

export type RecordsSummary = {
  business_id: string
  synthetic: boolean
  counts: Record<string, number>
}

export type EvidenceFinding = {
  code: string
  severity: string
  explanation: string
  linked_source_ids: string[]
  record_ids: string[]
  amounts_inr: string[]
  check_performed: string
  recommended_follow_up: string
  rule_version: string
}

export type EvidenceDna = {
  business_id: string
  business_name: string
  rule_version: string
  evidence_completeness: { score: number; denominator: number; expected_periods: string[] }
  evidence_consistency: { score: number; denominator: number; matched: number }
  verification_status: Record<string, number>
  gateway_status_counts?: Partial<Record<VerificationStatus, number>>
  assessment_confidence: { label: string; rationale: string }
  claim_to_evidence: {
    reported_amount_inr: string | null
    observed_monthly_credit_inr: Record<string, string>
    status: string
    explanation: string
  }
  findings: EvidenceFinding[]
  limitations: string[]
  provenance: { data_scope: string; synthetic: boolean; source_ids: string[]; rule_version: string }
}

export type TrustGraphNode = {
  id: string
  type: 'Business' | 'Counterparty' | 'Invoice' | 'Transaction'
  label: string
  source_ids: string[]
  [key: string]: unknown
}

export type TrustGraphEdge = {
  id: string
  source: string
  target: string
  type: string
  source_ids: string[]
  [key: string]: unknown
}

export type TrustGraph = {
  business_id: string
  rule_version: string
  nodes: TrustGraphNode[]
  edges: TrustGraphEdge[]
  anomalies: Array<{ code: string; severity: string; message: string; record_ids: string[]; recommended_follow_up: string }>
  metrics: Record<string, string | number | null>
  provenance: { synthetic: boolean; business_id: string; source_ids: string[]; data_scope: string; networkx: string; rule_version: string }
}

export type FinancialMetric = {
  value: string | number | null
  unit: string
  formula: string
  data_coverage: string
  caveats: string[]
}

export type FinancialSummary = {
  business_id: string
  business_name: string
  rule_version: string
  date_window: { start: string | null; end: string | null }
  monthly: Array<{ month: string; inflows_inr: string; outflows_inr: string; net_cash_flow_inr: string; positive_net_month: boolean }>
  metrics: Record<string, FinancialMetric>
  seasonality: { label: string; method: string; observed_months: number; warning: string | null }
  coverage: { transaction_count: number; operating_transaction_count: number; excluded_transaction_count: number; excluded_amount_inr: string; date_window: string | null }
  limitations: string[]
  provenance: { synthetic: boolean; source_ids: string[]; data_scope: string; rule_version: string }
}

export type Assessment = {
  assessment_id: string
  business_id: string
  created_at: string
  rule_version: string
  status: string
  snapshot: {
    risk_indicators: Array<{ code: string; status: string; value: number | null; unit: string; explanation: string; formula: string; thresholds: Record<string, number> }>
    evidence_quality: { completeness: { score: number; denominator?: number }; consistency: { score: number; denominator?: number }; verification_status: Record<string, number>; limitations: string[] }
    assessment_confidence: { label: string; rationale: string; derivation: string }
    key_risk_factors: string[]
    mitigating_factors: string[]
    unknowns: string[]
    recommended_lender_questions: string[]
    decision_boundary: string
    fairness_notes: string[]
    financial_summary: FinancialSummary
  }
  limitations: string[]
}

export type StressTestRequest = {
  base_monthly?: Array<{ month: string; inflows_inr: string; outflows_inr: string }>
  revenue_shock_pct: number
  expense_shock_pct: number
  payment_delay_days: number
  duration_months: number
  selected_loan_emi: string
  seasonal_weaker_months: number
}

export type StressTest = {
  business_id: string
  rule_version: string
  scenario: Record<string, string | number>
  monthly: Array<{
    month_number: number
    label: string
    base_inflows_inr: string
    base_outflows_inr: string
    projected_inflows_inr: string
    projected_outflows_inr: string
    net_cash_before_emi_inr: string
    loan_emi_inr: string
    net_cash_after_emi_inr: string
    emi_coverage_ratio: string | null
    cash_gap_inr: string
  }>
  metrics: Record<string, string>
  warnings: string[]
  assumptions: string[]
  provenance: { synthetic: boolean; source_ids: string[]; base_data_scope: string }
}

export type LoanOption = {
  tenure_months: number
  emi_inr: string
  total_repayment_inr: string
  interest_cost_inr: string
  origination_fee_inr: string
  total_cost_inr: string
  affordability_status: string
  affordability_rationale: string
  minimum_post_emi_cash_inr: string
  minimum_dscr: string | null
  monthly: Array<{
    month: string
    scenario_inflows_inr: string
    scenario_outflows_inr: string
    available_cash_before_new_debt_inr: string
    proposed_emi_inr: string
    net_cash_after_proposed_emi_inr: string
    debt_service_coverage_ratio: string | null
  }>
  tradeoffs: string[]
}

export type LoanOptions = {
  business_id: string
  rule_version: string
  requested_principal_inr: string
  annual_interest_rate_pct: string
  origination_fee_inr: string
  thresholds: Record<string, number>
  options: LoanOption[]
  assumptions: string[]
  provenance: { synthetic: boolean; source_ids: string[]; scenario_scope: string }
}

export type CreditPassport = {
  passport_version: string
  assessment_id: string
  business_id: string
  created_at: string
  rule_version: string
  status: string
  snapshot: Assessment['snapshot'] & {
    business: Business
    source_inventory: Array<{ source_id: string; kind: string; source_label: string; synthetic: boolean; imported_at: string; parsing_status: string }>
    evidence_dna: EvidenceDna
    trust_graph: TrustGraph
    cashflow_twin: { normal: StressTest; combined_crisis: StressTest }
    loan_options: LoanOptions
  }
  disclosures: string[]
  latest_review?: Pick<ReviewRecord, 'status' | 'updated_at'> | null
  consent: { source_upload: boolean; passport_sharing: boolean }
  export: { format: string; filename: string; allowed: boolean; blocked_reason: string | null }
}

export type ReviewRecord = {
  id: string
  assessment_id: string
  reviewer_name_or_alias: string
  status: 'pending' | 'needs_more_information' | 'reviewed'
  reason: string
  checklist: Record<string, boolean>
  rule_version: string
  updated_at: string
}

export type ReviewWorkspace = {
  business: { id: string; name: string; consent_status: string }
  passport: CreditPassport
  evidence_findings: EvidenceFinding[]
  scenario_comparison: { normal: StressTest; combined_crisis: StressTest }
  consent: { source_upload: boolean; passport_sharing: boolean }
  reviews: ReviewRecord[]
  checklist_keys: string[]
  limitations: string[]
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  readonly status: number
  readonly retryAfter?: string

  constructor(status: number, message: string, retryAfter?: string) {
    super(message)
    this.status = status
    this.retryAfter = retryAfter
  }
}

const send = (path: string, init?: RequestInit) => fetch(`${apiBaseUrl}${path}`, {
  ...init,
  credentials: 'include',
  cache: 'no-store',
})

let refreshAttempt: Promise<Response> | undefined

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response = await send(path, init)
  if (response.status === 401 && !path.startsWith('/api/auth/')) {
    refreshAttempt ??= send('/api/auth/refresh', { method: 'POST' })
      .finally(() => { refreshAttempt = undefined })
    response = (await refreshAttempt).ok ? await send(path, init) : response
    if (response.status === 401) window.dispatchEvent(new Event('credweave:session-expired'))
  }
  const payload = (await response.json().catch(() => ({}))) as { detail?: unknown }
  if (!response.ok) {
    throw new ApiError(response.status, typeof payload.detail === 'string' ? payload.detail : `API returned ${response.status}`, response.headers.get('Retry-After') ?? undefined)
  }
  return payload as T
}

export function fetchHealth() {
  return request<HealthResponse>('/api/health')
}

export type BusinessDetails = Pick<Business, 'name' | 'sector' | 'city' | 'operating_months'>
export type RecordKind = 'transactions' | 'invoices' | 'counterparties' | 'obligations'
export type DataSource = {
  id: string
  source_label: string
  kind: string
  synthetic: boolean
  imported_at: string
  parsing_status: string
}

export function fetchBusiness(id: string) {
  return request<Business>(`/api/businesses/${id}`)
}

export function updateBusiness(id: string, details: BusinessDetails & { source_upload_consent?: boolean }) {
  return request<Business>(`/api/businesses/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(details),
  })
}

export function setUploadConsent(id: string, granted: boolean) {
  return request<Business>(`/api/businesses/${id}/upload-consent?granted=${granted}`, { method: 'PATCH' })
}

export function fetchSources(id: string) {
  return request<DataSource[]>(`/api/businesses/${id}/sources`)
}

export function fetchRecords(id: string, kind: RecordKind, offset: number) {
  return request<{ items: Record<string, string | null>[]; next_offset: number | null }>(
    `/api/businesses/${id}/records?kind=${kind}&offset=${offset}`,
  )
}

export function fetchBusinesses(): Promise<Business[]> {
  return request<Business[]>('/api/businesses')
}

export type LenderQueueItem = {
  business: Business
  assessment_id: string | null
  review_status: ReviewRecord['status'] | 'awaiting_review' | 'no_passport'
}

export function fetchLenderQueue() {
  return request<LenderQueueItem[]>('/api/lender/queue')
}

export function createBusiness(payload: Omit<Business, 'id' | 'created_at'>): Promise<Business> {
  return request<Business>('/api/businesses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function fetchSummary(businessId: string): Promise<RecordsSummary> {
  return request<RecordsSummary>(`/api/businesses/${businessId}/records-summary`)
}

export function uploadEvidence(
  businessId: string,
  kind: 'transactions' | 'invoices' | 'suppliers' | 'obligations',
  file: File,
): Promise<{ accepted_rows: number; synthetic: boolean; requires_review?: number }> {
  const form = new FormData()
  form.append('file', file)
  return request(`/api/businesses/${businessId}/imports/${kind}`, { method: 'POST', body: form })
}

export function loadSyntheticDemo(): Promise<{ businesses_seeded: number; synthetic: boolean }> {
  return request('/api/demo/load', { method: 'POST' })
}

export function fetchEvidenceDna(businessId: string): Promise<EvidenceDna> {
  return request<EvidenceDna>(`/api/businesses/${businessId}/evidence-dna`)
}

export function fetchTrustGraph(businessId: string): Promise<TrustGraph> {
  return request<TrustGraph>(`/api/businesses/${businessId}/trust-graph`)
}

export function fetchFinancialSummary(businessId: string): Promise<FinancialSummary> {
  return request<FinancialSummary>(`/api/businesses/${businessId}/financial-summary`)
}

export function createAssessment(businessId: string): Promise<Assessment> {
  return request<Assessment>(`/api/businesses/${businessId}/assess`, { method: 'POST' })
}

export function fetchLatestAssessment(businessId: string): Promise<Assessment> {
  return request<Assessment>(`/api/businesses/${businessId}/assessments/latest`)
}

export function fetchStressPresets(businessId: string) {
  type Preset = Pick<StressTestRequest, 'revenue_shock_pct' | 'expense_shock_pct' | 'payment_delay_days' | 'seasonal_weaker_months'> & { label: string }
  return request<{ business_id: string; presets: Record<string, Preset> }>(`/api/businesses/${businessId}/stress-tests/presets`)
}

export function runStressTest(businessId: string, payload: StressTestRequest): Promise<StressTest> {
  return request<StressTest>(`/api/businesses/${businessId}/stress-tests`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function fetchLoanOptions(businessId: string, payload: {
  principal_inr: string
  annual_interest_rate_pct: number
  tenure_months: number[]
  origination_fee_inr: string
  scenario_preset: "normal" | "combined_crisis"
}): Promise<LoanOptions> {
  return request<LoanOptions>(`/api/businesses/${businessId}/loan-options`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function fetchCreditPassport(businessId: string): Promise<CreditPassport> {
  return request<CreditPassport>(`/api/businesses/${businessId}/credit-passport`)
}

export function fetchReviewWorkspace(businessId: string): Promise<ReviewWorkspace> {
  return request<ReviewWorkspace>(`/api/businesses/${businessId}/review-workspace`)
}

export function createReview(businessId: string, payload: {
  reviewer_name_or_alias?: string
  assessment_id?: string
  status: ReviewRecord['status']
  reason: string
  checklist: Record<string, boolean>
}): Promise<ReviewRecord> {
  return request<ReviewRecord>(`/api/businesses/${businessId}/reviews`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function updateConsent(businessId: string, payload: {
  source_upload_consent: boolean
  passport_sharing_consent: boolean
}): Promise<{ source_upload: boolean; passport_sharing: boolean }> {
  const query = new URLSearchParams({
    source_upload_consent: String(payload.source_upload_consent),
    passport_sharing_consent: String(payload.passport_sharing_consent),
  })
  return request(`/api/businesses/${businessId}/consent?${query}`, { method: 'POST' })
}

export type LenderShare = { lender_id: string; granted_at: string }

export function fetchShares(businessId: string) {
  return request<LenderShare[]>(`/api/businesses/${businessId}/shares`)
}

export function changeShare(businessId: string, lenderId: string, grant: boolean) {
  return request<{ lender_id: string }>(`/api/businesses/${businessId}/shares/${encodeURIComponent(lenderId)}`, {
    method: grant ? 'PUT' : 'DELETE',
  })
}

export type VerificationStatus =
  | 'UNVERIFIED' | 'PARTIALLY_SUPPORTED' | 'SOURCE_VERIFIED' | 'REQUIRES_REVIEW' | 'SIMULATED_SOURCE_VERIFIED'

export type VerificationEvent = {
  event_id: number
  status: VerificationStatus
  method: string
  verified_at: string
  findings: { code: string; reason: string }[]
  supporting_evidence: { record_id: string; source_id: string }[]
  limitations: string[]
}

export type GatewayRecord = {
  provenance_id: string
  record_id: string
  record_type: 'transaction' | 'invoice' | 'obligation'
  source_id: string | null
  source_type: string
  source_provider: string | null
  original_source_reference: string | null
  record_reference?: string | null
  record_date?: string | null
  amount_inr?: string | null
  source_label?: string | null
  uploaded_at: string | null
  file_sha256: string | null
  consent_reference: string | null
  result: VerificationEvent
}

export type GatewayFilters = { kind?: GatewayRecord['record_type']; search?: string; sort?: 'recent' | 'date' | 'amount' | 'reference' }

export function fetchVerifiedEvidence(businessId: string, offset: number, status?: VerificationStatus, filters?: GatewayFilters) {
  const query = new URLSearchParams({ offset: String(offset) })
  if (status) query.set('status', status)
  if (filters?.kind) query.set('kind', filters.kind)
  if (filters?.search) query.set('search', filters.search)
  if (filters?.sort && filters.sort !== 'recent') query.set('sort', filters.sort)
  return request<{ items: GatewayRecord[]; counts: Partial<Record<VerificationStatus, number>>; next_offset: number | null; matching_count?: number }>(
    `/api/businesses/${businessId}/verified-evidence?${query}`,
  )
}

export function fetchVerificationHistory(businessId: string, provenanceId: string, after = 0) {
  return request<{ items: VerificationEvent[]; next_after: number | null }>(
    `/api/businesses/${businessId}/verified-evidence/${provenanceId}/history?after=${after}`,
  )
}

export function reconcileVerifiedEvidence(businessId: string) {
  return request<{ records_updated: number }>(`/api/businesses/${businessId}/verified-evidence/reconcile`, { method: 'POST' })
}
