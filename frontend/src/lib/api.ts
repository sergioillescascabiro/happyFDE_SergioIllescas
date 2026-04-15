import { getToken } from './auth';
import type {
  CallsOverTimePoint,
  OutcomeDistribution,
  NegotiationAnalysis,
  SentimentDistribution,
  FinancialMetrics,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers['X-Dashboard-Token'] = token;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    throw new Error('UNAUTHORIZED');
  }
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}

export async function validateToken(token: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/health/auth`, {
      headers: { 'X-Dashboard-Token': token },
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function getCallsOverTime(days = 30): Promise<CallsOverTimePoint[]> {
  return apiFetch<CallsOverTimePoint[]>(`/api/metrics/calls-over-time?days=${days}`);
}

export async function getOutcomeDistribution(): Promise<OutcomeDistribution[]> {
  return apiFetch<OutcomeDistribution[]>('/api/metrics/outcome-distribution');
}

export async function getNegotiationAnalysis(): Promise<NegotiationAnalysis> {
  return apiFetch<NegotiationAnalysis>('/api/metrics/negotiation-analysis');
}

export async function getSentimentDistribution(): Promise<SentimentDistribution> {
  return apiFetch<SentimentDistribution>('/api/metrics/sentiment');
}

export async function getFinancialMetrics(): Promise<FinancialMetrics> {
  return apiFetch<FinancialMetrics>('/api/metrics/financial');
}
