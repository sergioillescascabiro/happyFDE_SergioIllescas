'use client';

import { useState, useEffect, useCallback } from 'react';
import { Package, PhoneCall, TrendingUp, DollarSign, RefreshCw } from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  PieChart, Pie, Cell,
} from 'recharts';
import { apiFetch, getCallsOverTime, getOutcomeDistribution, getNegotiationAnalysis, getSentimentDistribution } from '@/lib/api';
import {
  MetricsOverview, Shipper, Load, Quote, Carrier,
  CallsOverTimePoint, OutcomeDistribution, NegotiationAnalysis, SentimentDistribution,
} from '@/types';
import { KPICard } from '@/components/ui/KPICard';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { PageLoader } from '@/components/ui/LoadingSpinner';

function formatCurrency(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function isLate(load: Load): boolean {
  return load.status === 'available' && new Date(load.pickup_datetime) < new Date();
}

function ActiveLoadCard({ load }: { load: Load }) {
  const late = isLate(load);
  return (
    <div className="bg-[#111111] border border-[#2a2a2a] rounded-lg p-4 hover:border-[#3a3a3a] transition-colors">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <p className="text-xs text-[#555555] font-mono-data">{load.load_id}</p>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="text-sm font-medium text-white truncate max-w-[120px]">{load.origin}</span>
            <span className="text-[#555555] text-xs">→</span>
            <span className="text-sm font-medium text-white truncate max-w-[120px]">{load.destination}</span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <StatusBadge status={load.status} />
          {late && (
            <span className="text-[10px] font-bold text-red-400 bg-red-500/10 border border-red-500/30 px-1.5 py-0.5 rounded font-mono-data">
              LATE
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-3 text-xs text-[#666666]">
        <span className="font-mono-data">{load.equipment_type}</span>
        <span>·</span>
        <span>{formatDate(load.pickup_datetime)}</span>
        <span>·</span>
        <span className="font-mono-data">${load.per_mile_rate.toFixed(2)}/mi</span>
      </div>
    </div>
  );
}

const OUTCOME_COLORS: Record<string, string> = {
  booked: '#10b981',
  rejected: '#ef4444',
  no_agreement: '#f59e0b',
  cancelled: '#6b7280',
  transferred: '#3b82f6',
  in_progress: '#a855f7',
  carrier_not_authorized: '#f97316',
  no_loads_available: '#64748b',
};

const OUTCOME_LABELS: Record<string, string> = {
  booked: 'Booked',
  rejected: 'Rejected',
  no_agreement: 'No Agreement',
  cancelled: 'Cancelled',
  transferred: 'Transferred',
  in_progress: 'In Progress',
  carrier_not_authorized: 'Not Authorized',
  no_loads_available: 'No Loads',
};

function SectionHeader({ title }: { title: string }) {
  return (
    <p className="text-[10px] font-mono-data text-[#555555] uppercase tracking-widest mb-3">{title}</p>
  );
}

function SkeletonPanel({ height }: { height: number }) {
  return <div className={`animate-pulse bg-[#1a1d27] rounded-lg border border-[#2a2d3a]`} style={{ height }} />;
}

export default function OverviewPage() {
  const [metrics, setMetrics] = useState<MetricsOverview | null>(null);
  const [shippers, setShippers] = useState<Shipper[]>([]);
  const [selectedShipper, setSelectedShipper] = useState<string>('all');
  const [activeLoads, setActiveLoads] = useState<Load[]>([]);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [topCarriers, setTopCarriers] = useState<Array<{ carrier: Carrier; booking_count: number }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Analytics state
  const [callsOverTime, setCallsOverTime] = useState<CallsOverTimePoint[] | null>(null);
  const [outcomeDistribution, setOutcomeDistribution] = useState<OutcomeDistribution[] | null>(null);
  const [negotiationAnalysis, setNegotiationAnalysis] = useState<NegotiationAnalysis | null>(null);
  const [sentimentData, setSentimentData] = useState<SentimentDistribution | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const shipperParam = selectedShipper !== 'all' ? `?shipper_id=${selectedShipper}` : '';

      const [metricsData, shippersData, loadsData, quotesData, carriersData] = await Promise.all([
        apiFetch<MetricsOverview>(`/api/metrics/overview${shipperParam}`),
        apiFetch<Shipper[]>('/api/shippers'),
        apiFetch<{ items: Load[] }>(`/api/loads?status=pending&page_size=20${selectedShipper !== 'all' ? `&shipper_id=${selectedShipper}` : ''}`),
        apiFetch<Quote[]>(`/api/quotes${selectedShipper !== 'all' ? `?shipper_id=${selectedShipper}` : ''}`),
        apiFetch<Array<{ carrier: Carrier; booking_count: number }>>('/api/metrics/top-carriers?limit=5'),
      ]);

      // Also fetch covered loads
      const coveredData = await apiFetch<{ items: Load[] }>(
        `/api/loads?status=covered&page_size=20${selectedShipper !== 'all' ? `&shipper_id=${selectedShipper}` : ''}`
      );

      setMetrics(metricsData);
      setShippers(shippersData);
      setActiveLoads([...loadsData.items, ...coveredData.items].slice(0, 12));
      setQuotes(quotesData.slice(0, 8));
      setTopCarriers(carriersData);
      setError('');
    } catch {
      setError('Failed to load dashboard data. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, [selectedShipper]);

  // Load analytics data (independent of shipper filter)
  const loadAnalytics = useCallback(async () => {
    try {
      const [cotData, odData, naData, sentData] = await Promise.all([
        getCallsOverTime(30),
        getOutcomeDistribution(),
        getNegotiationAnalysis(),
        getSentimentDistribution(),
      ]);
      setCallsOverTime(cotData);
      setOutcomeDistribution(odData);
      setNegotiationAnalysis(naData);
      setSentimentData(sentData);
    } catch {
      // analytics are non-critical — don't surface error
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  if (loading && !metrics) return <PageLoader />;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Acme Logistics</h1>
          <p className="text-[#555555] text-sm mt-0.5">Freight Operations Overview</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Shipper filter */}
          <select
            value={selectedShipper}
            onChange={(e) => setSelectedShipper(e.target.value)}
            className="bg-[#111111] border border-[#2a2a2a] text-white text-sm rounded-md px-3 py-2 focus:outline-none focus:border-[#444]"
          >
            <option value="all">All Shippers</option>
            {shippers.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <button
            onClick={loadData}
            className="p-2 rounded-md border border-[#2a2a2a] text-[#888] hover:text-white hover:border-[#444] transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      {/* KPI Row */}
      {metrics && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard
            title="Total Loads"
            value={metrics.total_loads}
            icon={Package}
          />
          <KPICard
            title="Active Loads"
            value={metrics.active_loads}
            icon={TrendingUp}
            subtitle="Pending + Covered"
            valueClassName="text-amber-400"
          />
          <KPICard
            title="Cargo Value"
            value={formatCurrency(metrics.cargo_value)}
            icon={DollarSign}
            subtitle="Across all loads"
            valueClassName="text-green-400"
          />
          <KPICard
            title="Conversion Rate"
            value={`${metrics.conversion_rate}%`}
            icon={PhoneCall}
            subtitle={`${metrics.booked_calls} / ${metrics.total_calls} calls`}
            valueClassName={metrics.conversion_rate >= 30 ? 'text-green-400' : 'text-amber-400'}
          />
        </div>
      )}

      {/* ── ANALYTICS SECTION ── */}
      {/* Call Volume — full-width */}
      <div className="bg-[#111318] border border-[#2a2d3a] rounded-lg p-5">
        <SectionHeader title="Call Volume — Last 30 Days" />
        {!callsOverTime ? (
          <div className="animate-pulse bg-[#1a1d27] rounded h-[180px]" />
        ) : callsOverTime.length === 0 ? (
          <div className="flex items-center justify-center h-[180px] text-[#555555] text-sm">No data yet</div>
        ) : (
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={callsOverTime} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradTotal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradBooked" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2230" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={(d: string) => {
                  const dt = new Date(d + 'T00:00:00');
                  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                }}
                tick={{ fill: '#555555', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                allowDecimals={false}
                tick={{ fill: '#555555', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{ background: '#111318', border: '1px solid #2a2d3a', borderRadius: 6, fontSize: 11 }}
                labelStyle={{ color: '#aaaaaa', fontFamily: 'JetBrains Mono' }}
                itemStyle={{ fontFamily: 'JetBrains Mono' }}
                labelFormatter={(d) => typeof d === 'string' ? new Date(d + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : String(d)}
              />
              <Area type="monotone" dataKey="count" name="Total Calls" stroke="#3b82f6" strokeWidth={1.5} fill="url(#gradTotal)" dot={false} />
              <Area type="monotone" dataKey="booked_count" name="Booked" stroke="#10b981" strokeWidth={1.5} fill="url(#gradBooked)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
        <div className="flex items-center gap-5 mt-3">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-[#3b82f6] inline-block rounded" />
            <span className="text-[11px] text-[#555555] font-mono-data">Total Calls</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-[#10b981] inline-block rounded" />
            <span className="text-[11px] text-[#555555] font-mono-data">Booked</span>
          </div>
        </div>
      </div>

      {/* Outcome + Negotiation row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Outcome Distribution */}
        <div className="bg-[#111318] border border-[#2a2d3a] rounded-lg p-5">
          <SectionHeader title="Outcome Distribution" />
          {!outcomeDistribution ? (
            <SkeletonPanel height={200} />
          ) : outcomeDistribution.length === 0 ? (
            <div className="flex items-center justify-center h-[200px] text-[#555555] text-sm">No data yet</div>
          ) : (
            <div className="flex items-center gap-6">
              <PieChart width={160} height={160}>
                <Pie
                  data={outcomeDistribution}
                  dataKey="count"
                  nameKey="outcome"
                  cx={75}
                  cy={75}
                  innerRadius={48}
                  outerRadius={72}
                  strokeWidth={0}
                >
                  {outcomeDistribution.map((entry) => (
                    <Cell key={entry.outcome} fill={OUTCOME_COLORS[entry.outcome] ?? '#6b7280'} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#111318', border: '1px solid #2a2d3a', borderRadius: 6, fontSize: 11 }}
                  itemStyle={{ fontFamily: 'JetBrains Mono' }}
                />
              </PieChart>
              <div className="flex-1 space-y-2">
                {outcomeDistribution.map((item) => {
                  const total = outcomeDistribution.reduce((s, i) => s + i.count, 0);
                  const pct = total > 0 ? Math.round(item.count / total * 100) : 0;
                  return (
                    <div key={item.outcome} className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-2 h-2 rounded-full shrink-0"
                          style={{ background: OUTCOME_COLORS[item.outcome] ?? '#6b7280' }}
                        />
                        <span className="text-xs text-[#aaaaaa]">{OUTCOME_LABELS[item.outcome] ?? item.outcome}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono-data text-white">{item.count}</span>
                        <span className="text-[10px] font-mono-data text-[#555555] w-8 text-right">{pct}%</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Negotiation Performance */}
        <div className="bg-[#111318] border border-[#2a2d3a] rounded-lg p-5">
          <SectionHeader title="Negotiation Performance" />
          {!negotiationAnalysis ? (
            <SkeletonPanel height={200} />
          ) : negotiationAnalysis.total_negotiations === 0 ? (
            <div className="flex items-center justify-center h-[200px] text-[#555555] text-sm">No negotiations yet</div>
          ) : (
            <div className="grid grid-cols-2 gap-4 mt-2">
              {[
                { label: 'Acceptance Rate', value: `${negotiationAnalysis.acceptance_rate}%`, color: 'text-green-400' },
                { label: 'Avg Rounds', value: negotiationAnalysis.avg_rounds.toFixed(1), color: 'text-blue-400' },
                { label: 'Counter Rate', value: `${negotiationAnalysis.counter_rate}%`, color: 'text-amber-400' },
                { label: 'Rejection Rate', value: `${negotiationAnalysis.rejection_rate}%`, color: 'text-red-400' },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-[#0d1017] border border-[#2a2d3a] rounded-lg p-4">
                  <p className="text-[10px] text-[#555555] uppercase tracking-widest mb-1">{label}</p>
                  <p className={`text-xl font-bold font-mono-data ${color}`}>{value}</p>
                </div>
              ))}
              <div className="col-span-2 text-[10px] text-[#444444] font-mono-data text-right">
                {negotiationAnalysis.total_negotiations} total negotiation rounds
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Sentiment Overview */}
      {sentimentData && (
        <div className="bg-[#111318] border border-[#2a2d3a] rounded-lg p-5">
          <SectionHeader title="Call Sentiment" />
          <div className="space-y-3">
            {/* Stacked bar */}
            {(() => {
              const total = sentimentData.positive.count + sentimentData.neutral.count + sentimentData.negative.count;
              if (total === 0) return <p className="text-[#555555] text-sm">No sentiment data</p>;
              return (
                <>
                  <div className="flex h-5 rounded overflow-hidden gap-0.5">
                    {sentimentData.positive.count > 0 && (
                      <div
                        className="bg-green-500 transition-all"
                        style={{ width: `${sentimentData.positive.percentage}%` }}
                      />
                    )}
                    {sentimentData.neutral.count > 0 && (
                      <div
                        className="bg-amber-500 transition-all"
                        style={{ width: `${sentimentData.neutral.percentage}%` }}
                      />
                    )}
                    {sentimentData.negative.count > 0 && (
                      <div
                        className="bg-red-500 transition-all"
                        style={{ width: `${sentimentData.negative.percentage}%` }}
                      />
                    )}
                  </div>
                  <div className="flex items-center gap-6">
                    {[
                      { key: 'positive', label: 'Positive', color: 'bg-green-500', data: sentimentData.positive },
                      { key: 'neutral', label: 'Neutral', color: 'bg-amber-500', data: sentimentData.neutral },
                      { key: 'negative', label: 'Negative', color: 'bg-red-500', data: sentimentData.negative },
                    ].map(({ key, label, color, data }) => (
                      <div key={key} className="flex items-center gap-2">
                        <span className={`w-2.5 h-2.5 rounded-sm ${color}`} />
                        <span className="text-xs text-[#888888]">
                          {label} <span className="font-mono-data text-white">{data.count}</span>
                          <span className="text-[#555555] ml-1">({data.percentage}%)</span>
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              );
            })()}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Active Loads Panel */}
        <div className="xl:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Active Loads</h2>
            <span className="text-xs text-[#555555]">{activeLoads.length} loads</span>
          </div>
          {activeLoads.length === 0 ? (
            <div className="bg-[#111111] border border-[#2a2a2a] rounded-lg p-8 text-center">
              <p className="text-[#555555] text-sm">No active loads</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {activeLoads.map(load => <ActiveLoadCard key={load.id} load={load} />)}
            </div>
          )}
        </div>

        {/* Right column */}
        <div className="space-y-6">
          {/* Preferred Carriers */}
          <div>
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">Preferred Carriers</h2>
            <div className="bg-[#111111] border border-[#2a2a2a] rounded-lg overflow-hidden">
              {topCarriers.length === 0 ? (
                <div className="p-6 text-center text-[#555555] text-sm">No carrier data</div>
              ) : (
                <div className="divide-y divide-[#2a2a2a]">
                  {topCarriers.map(({ carrier, booking_count }, i) => (
                    <div key={carrier.id} className="flex items-center gap-3 px-4 py-3 hover:bg-white/5 transition-colors">
                      <span className="text-[#444] text-xs font-mono-data w-4">{i + 1}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-white truncate">{carrier.legal_name}</p>
                        <p className="text-xs text-[#555555] font-mono-data">MC {carrier.mc_number}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-mono-data text-green-400">{booking_count}</p>
                        <p className="text-[10px] text-[#555555]">bookings</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Quotes Table */}
      <div>
        <h2 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">Lane Quotes</h2>
        <div className="bg-[#111111] border border-[#2a2a2a] rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#2a2a2a]">
                  {['Lane', 'Equipment', 'Market Rate', 'Quoted Rate', 'Status'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-[#555555] text-xs uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1a1a1a]">
                {quotes.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-[#555555] text-sm">No quotes available</td>
                  </tr>
                ) : (
                  quotes.map(q => (
                    <tr key={q.id} className="hover:bg-white/5 transition-colors">
                      <td className="px-4 py-3">
                        <span className="text-sm text-white">{q.origin}</span>
                        <span className="text-[#555555] mx-1.5 text-xs">→</span>
                        <span className="text-sm text-white">{q.destination}</span>
                      </td>
                      <td className="px-4 py-3 text-sm text-[#888888] font-mono-data">{q.equipment_type}</td>
                      <td className="px-4 py-3 text-sm font-mono-data text-[#888888]">${q.market_rate.toFixed(2)}</td>
                      <td className="px-4 py-3 text-sm font-mono-data text-white">${q.quoted_rate.toFixed(2)}</td>
                      <td className="px-4 py-3"><StatusBadge status={q.status} /></td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
