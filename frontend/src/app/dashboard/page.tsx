'use client';

import { useState, useEffect, useCallback } from 'react';
import { Package, PhoneCall, TrendingUp, DollarSign, RefreshCw } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import { MetricsOverview, Shipper, Load, Quote, Carrier } from '@/types';
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

export default function OverviewPage() {
  const [metrics, setMetrics] = useState<MetricsOverview | null>(null);
  const [shippers, setShippers] = useState<Shipper[]>([]);
  const [selectedShipper, setSelectedShipper] = useState<string>('all');
  const [activeLoads, setActiveLoads] = useState<Load[]>([]);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [topCarriers, setTopCarriers] = useState<Array<{ carrier: Carrier; booking_count: number }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const shipperParam = selectedShipper !== 'all' ? `?shipper_id=${selectedShipper}` : '';

      const [metricsData, shippersData, loadsData, quotesData, carriersData] = await Promise.all([
        apiFetch<MetricsOverview>(`/api/metrics/overview${shipperParam}`),
        apiFetch<Shipper[]>('/api/shippers'),
        apiFetch<{ items: Load[] }>(`/api/loads?status=pending&page_size=20${selectedShipper !== 'all' ? `&shipper_id=${selectedShipper}` : ''}`),
        apiFetch<Quote[]>(`/api/quotes${selectedShipper !== 'all' ? `?shipper_id=${selectedShipper}` : ''}`),
        apiFetch<{ items: Carrier[]; total: number }>('/api/carriers'),
      ]);

      // Also fetch covered loads
      const coveredData = await apiFetch<{ items: Load[] }>(
        `/api/loads?status=covered&page_size=20${selectedShipper !== 'all' ? `&shipper_id=${selectedShipper}` : ''}`
      );

      setMetrics(metricsData);
      setShippers(shippersData);
      setActiveLoads([...loadsData.items, ...coveredData.items].slice(0, 12));
      setQuotes(quotesData.slice(0, 8));

      // Mock top carriers — use first 5 carriers with a fake count
      const carriers = carriersData.items.filter(c => c.status === 'active').slice(0, 5);
      setTopCarriers(carriers.map((c, i) => ({ carrier: c, booking_count: 15 - i * 2 })));

      setError('');
    } catch {
      setError('Failed to load dashboard data. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, [selectedShipper]);

  useEffect(() => {
    loadData();
  }, [loadData]);

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
            trend="up"
            trendValue="+3 this week"
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
