export type CaseStatus = 'OPEN' | 'IN_REVIEW' | 'ESCALATED' | 'RESOLVED' | 'CLOSED';
export type CasePriority = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type RiskLevel = 'CRITICAL' | 'HIGH' | 'REVIEW' | 'LOW';

export type ResolutionAction =
  | 'CONFIRMED_FRAUD'
  | 'FALSE_POSITIVE'
  | 'ACCOUNT_RESTRICTED'
  | 'STEP_UP_VERIFIED'
  | 'DISMISSED';

export interface AnalystNote {
  note_id?: string;
  author: string;
  timestamp?: string;
  created_at?: string;
  content?: string;
  note?: string;
}

export interface AuditTrailEntry {
  action: string;
  performed_by: string;
  timestamp: string;
  details?: Record<string, any>;
}

export interface BedrockAISummary {
  executive_summary: string;
  key_evidence?: string[];
  risk_indicators?: string[];
  recommended_actions: string[];
  alternative_explanations: string[];
  confidence_rationale?: string;
  evidence_limitations?: string;
  confidence_score?: number;
  model_id: string;
  generated_at?: string;
}

export type BedrockSummary = BedrockAISummary;

export interface CaseEvidence {
  amount?: number;
  currency?: string;
  avg_amount_24h?: number;
  amount_deviation?: number;
  transaction_count_5m?: number;
  transaction_count_1h?: number;
  new_device?: boolean;
  location_change?: boolean;
  international_flag?: boolean;
  merchant_risk?: number;
  account_age_days?: number;
  channel?: string;
  merchant_id?: string;
  merchant_name?: string;
  merchant_category?: string;
  device_id?: string;
  ip_address?: string;
  location?: any;
  fraud_probability?: number;
  anomaly_score?: number;
  risk_score?: number;
  [key: string]: any;
}

export interface CaseFeatures {
  amount_ratio_to_avg?: number;
  velocity_1h?: number;
  dist_from_home_km?: number;
  is_new_device?: boolean;
  [key: string]: any;
}

export interface InvestigationCase {
  case_id: string;
  transaction_id: string;
  account_id: string;
  customer_id: string;
  amount: number;
  currency: string;
  risk_score: number;
  risk_level: RiskLevel | string;
  status: CaseStatus;
  priority: CasePriority;
  assigned_to?: string | null;
  created_at: string;
  updated_at: string;
  channel?: string;
  fraud_probability?: number;
  anomaly_score?: number;
  merchant_name?: string;
  merchant_category?: string;
  location?: string;
  ip_address?: string;
  device_id?: string;
  resolution_action?: ResolutionAction | null;
  resolution_notes?: string | null;
  evidence?: CaseEvidence;
  features?: CaseFeatures;
  ai_summary?: BedrockAISummary | null;
  bedrock_summary?: BedrockAISummary | null;
  notes: AnalystNote[];
  audit_trail: AuditTrailEntry[];
}

export interface DashboardMetrics {
  total_cases: number;
  critical_cases: number;
  high_risk_cases: number;
  in_review_cases: number;
  resolved_today: number;
  avg_resolution_time_minutes?: number;
  avg_resolution_time_min?: number;
  false_positive_rate?: number;
}

export type MetricSummary = DashboardMetrics;

export interface CaseUpdateRequest {
  status?: CaseStatus;
  priority?: CasePriority;
  assigned_to?: string;
  resolution_action?: ResolutionAction;
  resolution_notes?: string;
  note?: string;
  author?: string;
}
