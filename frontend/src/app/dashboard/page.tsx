'use client';

import { useState, useEffect, useCallback } from 'react';
import { Package, PhoneCall, TrendingUp, DollarSign, RefreshCw, Truck, FileText, Bot, Globe } from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  PieChart, Pie, Cell,
} from 'recharts';
import { apiFetch, getCallsOverTime, getOutcomeDistribution, getNegotiationAnalysis, getSentimentDistribution, getAgentPerformance } from '@/lib/api';
import {
  MetricsOverview, Shipper, Load, Quote, Carrier,
  CallsOverTimePoint, OutcomeDistribution, NegotiationAnalysis, SentimentDistribution, AgentPerformance,
} from '@/types';
import { clsx } from 'clsx';
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
    <div className="glass-card rounded-xl p-4 hover:border-emerald-500/20 transition-all hover:translate-y-[-1px] group animate-in">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <p className="text-[10px] text-slate-500 font-mono-data uppercase tracking-tight">{load.load_id}</p>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="text-sm font-semibold text-white truncate max-w-[120px]">{load.origin}</span>
            <span className="text-slate-600 text-xs">→</span>
            <span className="text-sm font-semibold text-white truncate max-w-[120px]">{load.destination}</span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <StatusBadge status={load.status} />
          {late && (
            <span className="text-[10px] font-bold text-rose-400 bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 rounded-full font-mono-data">
              LATE
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-3 text-[11px] text-slate-500 font-medium">
        <span className="font-mono-data bg-white/5 px-1.5 py-0.5 rounded">{load.equipment_type}</span>
        <span className="opacity-30">|</span>
        <span>{formatDate(load.pickup_datetime)}</span>
        <span className="opacity-30">|</span>
        <span className="font-mono-data text-emerald-400/90">${load.per_mile_rate.toFixed(2)}/mi</span>
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
    <p className="text-[10px] font-heading font-semibold text-slate-500 uppercase tracking-[0.15em] mb-4">{title}</p>
  );
}

function SkeletonPanel({ height }: { height: number }) {
  return <div className={`animate-pulse bg-[#1a1d27] rounded-lg border border-[#2a2d3a]`} style={{ height }} />;
}

// ── Time-range aggregation helpers ────────────────────────────────────────────

function aggregateWeekly(data: CallsOverTimePoint[]): CallsOverTimePoint[] {
  const buckets: Record<string, CallsOverTimePoint> = {};
  for (const pt of data) {
    const d = new Date(pt.date + 'T00:00:00');
    // Move to Monday of that week
    const day = d.getDay(); // 0=Sun
    const diff = (day === 0 ? -6 : 1 - day);
    d.setDate(d.getDate() + diff);
    const key = d.toISOString().slice(0, 10);
    if (!buckets[key]) buckets[key] = { date: key, count: 0, booked_count: 0 };
    buckets[key].count += pt.count;
    buckets[key].booked_count += pt.booked_count;
  }
  return Object.values(buckets).sort((a, b) => a.date.localeCompare(b.date));
}

function aggregateMonthly(data: CallsOverTimePoint[]): CallsOverTimePoint[] {
  const buckets: Record<string, CallsOverTimePoint> = {};
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  for (const pt of data) {
    const d = new Date(pt.date + 'T00:00:00');
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    const label = MONTHS[d.getMonth()];
    if (!buckets[key]) buckets[key] = { date: label, count: 0, booked_count: 0 };
    buckets[key].count += pt.count;
    buckets[key].booked_count += pt.booked_count;
  }
  return Object.values(buckets).sort((a, b) => a.date.localeCompare(b.date));
}

const RANGE_OPTIONS: { label: string; days: number }[] = [
  { label: '7D', days: 7 },
  { label: '30D', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
];

// ── Paul's Performance Card ───────────────────────────────────────────────────

function PaulPerformanceCard({ data }: { data: AgentPerformance }) {
  const noData = data.ai.count === 0;
  const deltaPositive = data.margin_delta_pct >= 0;

  return (
    <div className="relative flex bg-gradient-to-br from-emerald-500/10 via-[#030303] to-[#030303] border border-emerald-500/20 rounded-2xl p-6 overflow-hidden animate-in">
      {/* Decorative grain/shimmer */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]" />
      
      <div className="flex-1 min-w-0 z-10">
        {/* Header row */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-500/10 rounded-lg">
              <Bot className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <span className="text-xl font-heading font-bold text-white tracking-tight">Paul</span>
              <span className="ml-2 text-[10px] font-mono-data text-emerald-400/60 bg-emerald-400/10 px-2 py-0.5 rounded-full uppercase">AI Agent</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-[9px] text-slate-500 uppercase font-heading font-bold tracking-wider">Automation</p>
              <p className="text-sm font-mono-data text-white">{data.automation_rate.toFixed(1)}%</p>
            </div>
            <div className="w-[1px] h-8 bg-white/10" />
            <div className="text-right">
              <p className="text-[9px] text-slate-500 uppercase font-heading font-bold tracking-wider flex items-center justify-end gap-1">
                vs Manual {deltaPositive ? <TrendingUp className="w-2.5 h-2.5 text-emerald-400" /> : null}
              </p>
              <p className={`text-sm font-mono-data ${deltaPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
                {deltaPositive ? '+' : ''}{data.margin_delta_pct.toFixed(1)}%
              </p>
            </div>
          </div>
        </div>

        {noData ? (
          <p className="text-sm text-slate-500 italic py-2">
            No AI-booked loads yet — Paul is ready to negotiate
          </p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {/* Margin Achieved */}
            <div className="space-y-2">
              <p className="text-[10px] text-slate-500 uppercase font-heading font-bold tracking-wider">Avg Margin</p>
              <p className="text-4xl font-bold font-mono-data text-emerald-400 tracking-tighter">
                {data.ai.avg_margin_pct.toFixed(1)}<span className="text-xl ml-0.5">%</span>
              </p>
              <div className="mt-2 h-1 rounded-full bg-white/5 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-500 to-emerald-300 rounded-full transition-all duration-1000"
                  style={{ width: `${Math.min(100, data.ai.avg_margin_pct * 4)}%` }}
                />
              </div>
            </div>

            {/* Loads Booked */}
            <div className="space-y-2">
              <p className="text-[10px] text-slate-500 uppercase font-heading font-bold tracking-wider">Total Booked</p>
              <p className="text-4xl font-bold font-mono-data text-white tracking-tighter">{data.ai.count}</p>
              <p className="text-[10px] text-slate-500 font-mono-data">
                of {data.ai.count + data.manual.count} total
              </p>
            </div>

            {/* Revenue */}
            <div className="space-y-2">
              <p className="text-[10px] text-slate-500 uppercase font-heading font-bold tracking-wider">Revenue</p>
              <p className="text-4xl font-bold font-mono-data text-white tracking-tighter">
                {formatCurrency(data.ai.total_booked_revenue)}
              </p>
              <p className="text-[10px] text-slate-500 font-mono-data">
                avg {formatCurrency(data.ai.avg_booked_rate)}/load
              </p>
            </div>

            {/* Manual Comparison */}
            <div className="space-y-2 bg-white/5 p-3 rounded-xl border border-white/5">
              <p className="text-[9px] text-slate-500 uppercase font-heading font-bold tracking-wider">Manual Performance</p>
              <div className="flex items-center justify-between">
                <p className="text-lg font-bold font-mono-data text-slate-300">{data.manual.avg_margin_pct.toFixed(1)}%</p>
                <div className="text-[9px] text-slate-500 font-mono-data text-right">
                  {data.manual.count} loads<br />
                  {formatCurrency(data.manual.total_booked_revenue)}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Overview Page ─────────────────────────────────────────────────────────────

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
  const [agentPerf, setAgentPerf] = useState<AgentPerformance | null>(null);

  // Chart range state
  const [range, setRange] = useState<number>(30);

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
      
      const combinedActive = [...loadsData.items, ...coveredData.items]
        .sort((a, b) => {
          const priority = { pending: 1, covered: 2 };
          const pa = priority[a.status as keyof typeof priority] || 99;
          const pb = priority[b.status as keyof typeof priority] || 99;
          if (pa !== pb) return pa - pb;
          return new Date(a.pickup_datetime).getTime() - new Date(b.pickup_datetime).getTime();
        });

      setActiveLoads(combinedActive.slice(0, 12));
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
      const [cotData, odData, naData, sentData, perfData] = await Promise.all([
        getCallsOverTime(range),
        getOutcomeDistribution(),
        getNegotiationAnalysis(),
        getSentimentDistribution(),
        getAgentPerformance(),
      ]);
      setCallsOverTime(cotData);
      setOutcomeDistribution(odData);
      setNegotiationAnalysis(naData);
      setSentimentData(sentData);
      setAgentPerf(perfData);
    } catch {
      // analytics are non-critical — don't surface error
    }
  }, [range]);

  // Reload chart data when range changes
  const reloadChart = useCallback(async () => {
    try {
      const cotData = await getCallsOverTime(range);
      setCallsOverTime(cotData);
    } catch {
      // non-critical
    }
  }, [range]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    loadAnalytics();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    reloadChart();
  }, [reloadChart]);

  // Aggregate chart data based on range
  const chartData: CallsOverTimePoint[] = (() => {
    if (!callsOverTime) return [];
    if (range >= 180) return aggregateMonthly(callsOverTime);
    if (range >= 90) return aggregateWeekly(callsOverTime);
    return callsOverTime;
  })();

  if (loading && !metrics) return <PageLoader />;

  return (
    <div className="p-10 space-y-8 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-5">
          <div className="p-3 bg-white/[0.03] rounded-2xl border border-white/10 shadow-inner">
            <Globe className="w-6 h-6 text-emerald-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-heading font-bold text-emerald-500 uppercase tracking-[0.2em]">Acme Logistics</span>
              <span className="text-[10px] text-slate-700 font-bold">•</span>
              <span className="text-[10px] font-heading font-bold text-slate-500 uppercase tracking-[0.2em]">Operational Pulse</span>
            </div>
            <h1 className="text-3xl font-heading font-bold text-white tracking-tight mt-0.5">Executive Dashboard</h1>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Shipper filter */}
          <select
            value={selectedShipper}
            onChange={(e) => setSelectedShipper(e.target.value)}
            className="bg-[#111111] border border-white/10 text-slate-200 text-xs font-medium rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500/50 transition-all appearance-none pr-8 bg-[url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20width%3D%2220%22%20height%3D%2220%22%20viewBox%3D%220%200%2020%2020%22%20fill%3D%22none%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%3E%3Cpath%20d%3D%22M5%207L10%2012L15%207%22%20stroke%3D%22%2364748b%22%20stroke-width%3D%221.5%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22/%3E%3C/svg%3E')] bg-no-repeat bg-[right_0.5rem_center]"
          >
            <option value="all">Global (All Shippers)</option>
            {shippers.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <button
            onClick={loadData}
            className="p-2 rounded-lg border border-white/10 text-slate-500 hover:text-white hover:bg-white/5 transition-all"
            title="Reload Data"
          >
            <RefreshCw className={clsx('w-4 h-4', loading && 'animate-spin')} />
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

      {/* Paul's Performance — featured card */}
      {agentPerf ? (
        <PaulPerformanceCard data={agentPerf} />
      ) : (
        <SkeletonPanel height={130} />
      )}

      {/* ── ANALYTICS SECTION ── */}
      {/* Call Volume — full-width with range selector */}
      <div className="bg-[#111318] border border-[#2a2d3a] rounded-lg p-5">
        <div className="flex items-center justify-between mb-3">
          <SectionHeader title={`Call Volume — Last ${range >= 365 ? '1Y' : range >= 180 ? '6M' : range >= 90 ? '3M' : range >= 30 ? '30D' : '7D'}`} />
          {/* Range selector */}
          <div className="flex items-center gap-1 -mt-3">
            {RANGE_OPTIONS.map(({ label, days }) => (
              <button
                key={label}
                onClick={() => setRange(days)}
                className={
                  range === days
                    ? 'bg-[#1a1d27] border border-[#3b82f6] text-blue-400 text-xs font-mono-data px-2.5 py-1 rounded'
                    : 'bg-transparent border border-[#2a2d3a] text-[#555555] text-xs font-mono-data px-2.5 py-1 rounded hover:text-[#888888]'
                }
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        {!callsOverTime ? (
          <div className="animate-pulse bg-[#1a1d27] rounded h-[180px]" />
        ) : chartData.length === 0 ? (
          <div className="flex items-center justify-center h-[180px] text-[#555555] text-sm">No data yet</div>
        ) : (
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
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
                  // Monthly aggregation already has "Jan", "Feb" etc.
                  if (range >= 180) return d;
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
                labelFormatter={(d) => {
                  if (range >= 180) return String(d);
                  return typeof d === 'string' ? new Date(d + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : String(d);
                }}
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
              <div className="flex flex-col items-center justify-center py-8 text-[#555555]">
                <Package className="w-8 h-8 mb-2 opacity-30" />
                <p className="text-sm">No active loads</p>
              </div>
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
                <div className="flex flex-col items-center justify-center py-8 text-[#555555]">
                  <Truck className="w-8 h-8 mb-2 opacity-30" />
                  <p className="text-sm">No carrier data</p>
                </div>
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
        <h2 className="text-xs font-heading font-bold text-slate-500 uppercase tracking-[0.15em] mb-4">Lane Quotes & Market Pulse</h2>
        <div className="glass-card rounded-2xl overflow-hidden border-white/5">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="bg-white/[0.02]">
                  {['Lane', 'Equipment', 'Market Rate', 'Quoted Rate', 'Status'].map(h => (
                    <th key={h} className="text-left px-5 py-4 text-slate-500 text-[10px] font-heading font-bold uppercase tracking-widest border-b border-white/5">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {quotes.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center">
                      <div className="flex flex-col items-center justify-center py-8 text-slate-600">
                        <FileText className="w-10 h-10 mb-3 opacity-20" />
                        <p className="text-sm font-medium">No market quotes indexed</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  quotes.map(q => (
                    <tr key={q.id} className="hover:bg-white/[0.02] transition-colors group">
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-slate-200">{q.origin}</span>
                          <span className="text-slate-600 text-[10px]">→</span>
                          <span className="text-sm font-semibold text-slate-200">{q.destination}</span>
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <span className="text-xs font-mono-data text-slate-500">{q.equipment_type}</span>
                      </td>
                      <td className="px-5 py-4">
                        <span className="text-sm font-mono-data text-slate-500">${q.market_rate.toFixed(2)}</span>
                      </td>
                      <td className="px-5 py-4">
                        <span className="text-sm font-mono-data text-white font-bold tracking-tight">${q.quoted_rate.toFixed(2)}</span>
                      </td>
                      <td className="px-5 py-4"><StatusBadge status={q.status} /></td>
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
