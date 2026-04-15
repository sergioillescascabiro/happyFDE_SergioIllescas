export type LoadStatus = 'available' | 'pending' | 'covered' | 'cancelled' | 'delivered';
export type CallOutcome = 'booked' | 'rejected' | 'no_agreement' | 'cancelled' | 'carrier_not_authorized' | 'no_loads_available' | 'transferred' | 'in_progress';
export type CallSentiment = 'positive' | 'neutral' | 'negative';
export type CallDirection = 'inbound' | 'outbound';
export type CarrierStatus = 'active' | 'in_review' | 'suspended' | 'inactive';
export type QuoteStatus = 'pending' | 'accepted' | 'rejected';

export interface Load {
  id: string;
  load_id: string;
  shipper_id: string;
  origin: string;
  destination: string;
  origin_lat?: number;
  origin_lng?: number;
  destination_lat?: number;
  destination_lng?: number;
  pickup_datetime: string;
  delivery_datetime: string;
  equipment_type: string;
  loadboard_rate: number;
  notes?: string;
  weight: number;
  commodity_type: string;
  num_of_pieces: number;
  miles: number;
  dimensions?: string;
  reference_id?: string;
  status: LoadStatus;
  total_rate: number;
  per_mile_rate: number;
  booked_rate?: number | null;
  margin_pct?: number | null;
  is_ai_booked?: boolean;
  quote_id?: string | null;
  created_at: string;
  updated_at: string;
  recommended_carriers?: CarrierSummary[];
}

export interface CarrierSummary {
  id: string;
  mc_number: string;
  legal_name: string;
  status: string;
  similar_match_count: number;
}

export interface Carrier {
  id: string;
  mc_number: string;
  dot_number?: string;
  legal_name: string;
  dba_name?: string;
  phone?: string;
  physical_address?: string;
  is_authorized: boolean;
  safety_rating?: string;
  status: CarrierStatus;
  source: string;
  verification_date?: string;
  created_at: string;
  updated_at: string;
}

export interface Call {
  id: string;
  carrier_id?: string;
  load_id?: string;
  shipper_id?: string;
  mc_number: string;
  direction: CallDirection;
  call_start: string;
  call_end?: string;
  duration_seconds?: number;
  outcome: CallOutcome;
  sentiment?: CallSentiment;
  transcript_summary?: string;
  transcript_full?: TranscriptMessage[];
  transferred_to_rep: boolean;
  happyrobot_call_id?: string;
  phone_number?: string;
  use_case: string;
  carrier_name?: string;
  load_load_id?: string;
  created_at: string;
  updated_at: string;
}

export interface TranscriptMessage {
  role: 'assistant' | 'caller' | 'tool_call';
  message: string;
  timestamp: string;
}

export interface NegotiationRound {
  id: string;
  round_number: number;
  carrier_offer: number;
  carrier_offer_per_mile: number;
  system_response: 'accept' | 'reject' | 'counter';
  counter_offer?: number;
  counter_offer_per_mile?: number;
  final_price?: number | null;
  tone?: string | null;
  is_final?: boolean;
  notes?: string;
  created_at: string;
}

export interface CallDetail extends Call {
  extracted_data?: Record<string, unknown>;
  negotiations: NegotiationRound[];
}

export interface Shipper {
  id: string;
  name: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  address: string;
  logo_url?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ShipperKPIs {
  shipper_id: string;
  shipper_name: string;
  total_loads: number;
  available_loads: number;
  covered_loads: number;
  pending_loads: number;
  cancelled_loads: number;
  total_calls: number;
  booked_calls: number;
  conversion_rate: number;
  total_cargo_value: number;
}

export interface Quote {
  id: string;
  shipper_id: string;
  origin: string;
  destination: string;
  equipment_type: string;
  market_rate: number;
  quoted_rate: number;
  status: QuoteStatus;
  created_at: string;
  updated_at: string;
}

export interface MetricsOverview {
  total_loads: number;
  active_loads: number;
  cargo_value: number;
  conversion_rate: number;
  total_calls: number;
  booked_calls: number;
}

export interface LoadListResponse {
  items: Load[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface CallListResponse {
  items: Call[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface CallsOverTimePoint {
  date: string;
  count: number;
  booked_count: number;
}

export interface OutcomeDistribution {
  outcome: string;
  count: number;
}

export interface NegotiationAnalysis {
  avg_rounds: number;
  acceptance_rate: number;
  rejection_rate: number;
  counter_rate: number;
  total_negotiations: number;
}

export interface SentimentDistribution {
  positive: { count: number; percentage: number };
  neutral: { count: number; percentage: number };
  negative: { count: number; percentage: number };
}

export interface AgentPerformance {
  agent_name: string;
  ai: { count: number; avg_margin_pct: number; total_booked_revenue: number; avg_booked_rate: number };
  manual: { count: number; avg_margin_pct: number; total_booked_revenue: number; avg_booked_rate: number };
  margin_delta_pct: number;
  automation_rate: number;
}

export interface FinancialMetrics {
  total_revenue: number;
  total_carrier_cost: number;
  net_margin: number;
  avg_spread_pct: number;
  avg_discount_pct: number;
  automation_rate: number;
  avg_time_to_cover_hours: number;
  covered_load_count: number;
  ai_booked_count: number;
}
