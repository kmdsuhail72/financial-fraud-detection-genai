import axios from 'axios';
import {
  CaseStatus,
  CasePriority,
  InvestigationCase,
  CaseUpdateRequest,
  DashboardMetrics,
  ResolutionAction
} from '../types/case';
import { DEMO_CASES } from './demoData';

const API_BASE_URL = (import.meta.env && import.meta.env.VITE_API_BASE_URL) || '/api';
const IS_DEMO_DEFAULT = (import.meta.env && import.meta.env.VITE_DEMO_MODE) !== 'false';

// Helper to normalize backend case models into full UI models
function normalizeCase(raw: any): InvestigationCase {
  const ev = raw.evidence || {};
  const channel = raw.channel || ev.channel || 'ONLINE';
  const fraudProb = raw.fraud_probability ?? ev.fraud_probability ?? 0.52;
  const anomaly = raw.anomaly_score ?? ev.anomaly_score ?? 0.35;
  const merchant = raw.merchant_name || ev.merchant_name || ev.merchant_id || 'Retail Merchant';
  const merchantCat = raw.merchant_category || ev.merchant_category || 'GENERAL_RETAIL';
  const locationStr =
    typeof raw.location === 'string'
      ? raw.location
      : ev.location
      ? `${ev.location.city || 'Mumbai'}, ${ev.location.country || 'IN'}`
      : 'Mumbai, IN';
  const ip = raw.ip_address || ev.ip_address || '103.21.244.12';
  const dev = raw.device_id || ev.device_id || 'DEV-MOBILE-01';

  // Normalize notes
  const notes = (raw.notes || []).map((n: any) => ({
    note_id: n.note_id || `NOTE-${Math.random().toString(36).substring(2, 7)}`,
    author: n.author || 'analyst@finguard.internal',
    timestamp: n.timestamp || n.created_at || new Date().toISOString(),
    created_at: n.created_at || n.timestamp || new Date().toISOString(),
    content: n.content || n.note || '',
    note: n.note || n.content || ''
  }));

  // Normalize ai_summary / bedrock_summary
  const ai = raw.ai_summary || raw.bedrock_summary || null;
  const normalizedAi = ai
    ? {
        ...ai,
        risk_indicators: ai.risk_indicators || ai.key_evidence || [],
        confidence_score: ai.confidence_score ?? 0.88,
        model_id: ai.model_id || 'anthropic.claude-3-5-sonnet-20241022-v2:0'
      }
    : null;

  return {
    ...raw,
    channel,
    fraud_probability: fraudProb,
    anomaly_score: anomaly,
    merchant_name: merchant,
    merchant_category: merchantCat,
    location: locationStr,
    ip_address: ip,
    device_id: dev,
    ai_summary: normalizedAi,
    bedrock_summary: normalizedAi,
    notes,
    audit_trail: raw.audit_trail || []
  };
}

// Memory cache for client-side demo mutations
let demoCasesCache: InvestigationCase[] = DEMO_CASES.map(normalizeCase);

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 8000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  isDemoMode(): boolean {
    const override = localStorage.getItem('finguard_demo_mode');
    return override !== null ? override === 'true' : IS_DEMO_DEFAULT;
  },

  setDemoMode(enabled: boolean): void {
    localStorage.setItem('finguard_demo_mode', String(enabled));
  },

  getBaseUrl(): string {
    return localStorage.getItem('finguard_api_url') || API_BASE_URL;
  },

  setBaseUrl(url: string): void {
    localStorage.setItem('finguard_api_url', url);
    client.defaults.baseURL = url;
  },

  async healthCheck(): Promise<boolean> {
    if (this.isDemoMode()) {
      return true;
    }
    try {
      const resp = await client.get('/health');
      return resp.status === 200;
    } catch {
      return false;
    }
  },

  async listCases(filters?: { status?: string; priority?: string; search?: string }): Promise<InvestigationCase[]> {
    if (this.isDemoMode()) {
      let filtered = [...demoCasesCache];
      if (filters?.status && filters.status !== 'ALL') {
        filtered = filtered.filter((c) => c.status === filters.status);
      }
      if (filters?.priority && filters.priority !== 'ALL') {
        filtered = filtered.filter((c) => c.priority === filters.priority);
      }
      if (filters?.search) {
        const q = filters.search.toLowerCase();
        filtered = filtered.filter(
          (c) =>
            c.case_id.toLowerCase().includes(q) ||
            c.transaction_id.toLowerCase().includes(q) ||
            c.customer_id.toLowerCase().includes(q) ||
            c.account_id.toLowerCase().includes(q)
        );
      }
      return filtered;
    }

    try {
      const params: any = {};
      if (filters?.status && filters.status !== 'ALL') params.status = filters.status;
      if (filters?.priority && filters.priority !== 'ALL') params.priority = filters.priority;
      const resp = await client.get('/cases', { params });
      const rawCases = resp.data.cases || resp.data || [];
      return rawCases.map(normalizeCase);
    } catch (e) {
      console.warn('Failed to fetch cases from API, falling back to demo cases:', e);
      return demoCasesCache;
    }
  },

  async getCase(caseId: string): Promise<InvestigationCase | null> {
    if (this.isDemoMode()) {
      const found = demoCasesCache.find((c) => c.case_id === caseId);
      return found || null;
    }

    try {
      const resp = await client.get(`/cases/${caseId}`);
      return normalizeCase(resp.data);
    } catch (e) {
      console.warn(`Failed to fetch case ${caseId} from API, checking demo cache:`, e);
      return demoCasesCache.find((c) => c.case_id === caseId) || null;
    }
  },

  async updateCaseStatus(caseId: string, status: CaseStatus): Promise<InvestigationCase> {
    return this.updateCase(caseId, { status });
  },

  async addNote(caseId: string, noteText: string, author: string = 'Alex Mercer'): Promise<InvestigationCase> {
    return this.updateCase(caseId, { note: noteText, author });
  },

  async updateCase(
    caseId: string,
    updates: CaseUpdateRequest,
    analystEmail: string = 'analyst@finguard.internal'
  ): Promise<InvestigationCase> {
    if (this.isDemoMode()) {
      const idx = demoCasesCache.findIndex((c) => c.case_id === caseId);
      if (idx === -1) throw new Error(`Case ${caseId} not found in demo cache`);

      const target = { ...demoCasesCache[idx] };
      const nowStr = new Date().toISOString();

      if (updates.status) target.status = updates.status;
      if (updates.assigned_to !== undefined) target.assigned_to = updates.assigned_to;
      if (updates.priority) target.priority = updates.priority;
      if (updates.resolution_action) {
        target.resolution_action = updates.resolution_action;
        target.status = 'RESOLVED';
        if (updates.resolution_notes) target.resolution_notes = updates.resolution_notes;
      }
      if (updates.note) {
        target.notes = [
          ...target.notes,
          {
            note_id: `NOTE-${Math.random().toString(36).substring(2, 8).toUpperCase()}`,
            author: updates.author || analystEmail,
            timestamp: nowStr,
            created_at: nowStr,
            content: updates.note,
            note: updates.note
          },
        ];
      }
      target.updated_at = nowStr;
      target.audit_trail = [
        ...target.audit_trail,
        {
          action: updates.resolution_action ? 'CASE_RESOLVED' : updates.note ? 'NOTE_ADDED' : `STATUS_${updates.status || 'UPDATED'}`,
          performed_by: updates.author || analystEmail,
          timestamp: nowStr,
          details: updates as any,
        },
      ];

      demoCasesCache[idx] = target;
      return target;
    }

    const resp = await client.patch(`/cases/${caseId}`, updates, {
      headers: { 'X-Analyst-Email': analystEmail },
    });
    return normalizeCase(resp.data);
  },

  async getMetrics(casesList?: InvestigationCase[]): Promise<DashboardMetrics> {
    const list = casesList || (await this.listCases());
    const critical = list.filter((c) => c.priority === 'CRITICAL' || c.risk_level === 'CRITICAL').length;
    const high = list.filter((c) => c.risk_level === 'HIGH' || c.priority === 'HIGH').length;
    const inReview = list.filter((c) => c.status === 'IN_REVIEW').length;
    const resolved = list.filter((c) => c.status === 'RESOLVED' || c.status === 'CLOSED').length;

    return {
      total_cases: list.length,
      critical_cases: critical,
      high_risk_cases: high,
      in_review_cases: inReview,
      resolved_today: resolved,
      avg_resolution_time_minutes: 14.5,
      false_positive_rate: 0.12,
    };
  },
};

export const casesApi = api;
