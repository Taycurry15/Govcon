export interface Opportunity {
  id: string
  solicitation_number: string
  title: string
  agency: string
  set_aside: string | null
  naics_code: string | null
  psc_code: string | null
  status: OpportunityStatus
  bid_score_total: number | null
  bid_recommendation: string | null
  response_deadline: string | null
  posted_date: string
  naics_match: number | null
  psc_match: number | null
  shapeable: boolean
  estimated_value: number | null
}

export enum OpportunityStatus {
  DISCOVERED = 'discovered',
  SCREENING = 'screening',
  AWAITING_PINK_TEAM = 'awaiting_pink_team',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  IN_PROGRESS = 'in_progress',
  AWAITING_GOLD_TEAM = 'awaiting_gold_team',
  SUBMITTED = 'submitted',
}

export interface Proposal {
  id: string
  opportunity_id: string
  title: string
  version: string
  status: ProposalStatus
  stage?: string
  vetcert_required: boolean
  submitted_at: string | null
  created_at: string
  updated_at: string
  due_date?: string | null
  completion_percentage?: number | null
  volumes?: Array<{
    id: string
    name: string
    section_count?: number
    status: string
  }>
  total_price?: number
  labor_cost?: number
  materials_cost?: number
  indirect_cost?: number
}

export enum ProposalStatus {
  DRAFT = 'draft',
  COMPLIANCE_REVIEW = 'compliance_review',
  TECHNICAL_WRITING = 'technical_writing',
  PRICING = 'pricing',
  PINK_TEAM = 'pink_team',
  RED_TEAM = 'red_team',
  GOLD_TEAM = 'gold_team',
  READY_FOR_SUBMISSION = 'ready_for_submission',
  SUBMITTED = 'submitted',
}

export interface WorkflowState {
  opportunity_id: string
  current_stage: string
  stages_completed: string[]
  stages_failed: string[]
  approval_gates_pending: string[]
  errors: string[]
  started_at: string
  updated_at: string
}

export interface User {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  can_manage_certifications: boolean
}

export interface DashboardStats {
  opportunities_total: number
  opportunities_this_month: number
  proposals_active: number
  proposals_submitted: number
  win_rate: number
  pipeline_value: number
}

export interface DiscoveryRequest {
  days_back?: number
  auto_approve?: boolean
}

export interface WorkflowExecutionRequest {
  opportunity_id: string
  auto_approve: boolean
}
