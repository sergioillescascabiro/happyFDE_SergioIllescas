'use client';

import { useState, useEffect } from 'react';
import { Phone, ChevronDown, ChevronRight, CheckSquare, Square } from 'lucide-react';
import { clsx } from 'clsx';
import { apiFetch } from '@/lib/api';
import { Load, CarrierSummary, Call } from '@/types';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

type Tab = 'booking' | 'accounting' | 'tracking';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function formatDateTime(iso: string): string {
  return `${formatDate(iso)} ${formatTime(iso)}`;
}

function MetadataChip({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex flex-col gap-1.5 p-3.5 rounded-2xl bg-white/[0.02] border border-white/5 transition-all hover:bg-white/[0.04]">
      <span className="text-[9px] text-slate-500 font-heading font-bold uppercase tracking-[0.12em]">{label}</span>
      <span className="text-xs text-slate-100 font-mono-data font-semibold">{value}</span>
    </div>
  );
}

function CarrierRow({ carrier, selected, onToggle }: {
  carrier: CarrierSummary;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      onClick={onToggle}
      className="flex items-center gap-3 px-4 py-3 hover:bg-[#1a1a1a] transition-colors cursor-pointer border-b border-[#1a1a1a] last:border-0"
    >
      <button className="shrink-0 text-[#555555] hover:text-white transition-colors">
        {selected ? (
          <CheckSquare className="w-4 h-4 text-white" />
        ) : (
          <Square className="w-4 h-4" />
        )}
      </button>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-white truncate">{carrier.legal_name}</p>
        <p className="text-xs text-[#555555] font-mono-data">MC {carrier.mc_number}</p>
      </div>
      <div className="flex items-center gap-2">
        <StatusBadge status={carrier.status} />
        <span className="text-xs text-[#555555] font-mono-data whitespace-nowrap">
          {carrier.similar_match_count} matches
        </span>
      </div>
    </div>
  );
}

function BookingTab({ load }: { load: Load }) {
  const [carriers, setCarriers] = useState<CarrierSummary[]>([]);
  const [calls, setCalls] = useState<Call[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadId = load.load_id;
    Promise.all([
      apiFetch<CarrierSummary[]>(`/api/loads/${loadId}/carriers`),
      apiFetch<Call[]>(`/api/loads/${loadId}/calls`),
    ]).then(([c, calls]) => {
      setCarriers(c);
      setCalls(calls);
    }).catch(console.error).finally(() => setLoading(false));
  }, [load.load_id]);

  const toggleCarrier = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selected.size === carriers.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(carriers.map(c => c.id)));
    }
  };

  const inboundCalls = calls.filter(c => c.direction === 'inbound');
  const outboundCalls = calls.filter(c => c.direction === 'outbound');

  if (loading) return (
    <div className="flex items-center justify-center py-12">
      <LoadingSpinner />
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Rate reference for broker */}
      <div className="text-[11px] text-slate-400 font-mono-data flex items-center gap-4 bg-emerald-500/5 border border-emerald-500/10 rounded-2xl px-5 py-4">
        <div className="flex items-center gap-2">
          <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest">Loadboard</span>
          <span className="text-white font-bold text-base leading-none tracking-tight">${load.total_rate.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
        </div>
        <div className="w-[1px] h-6 bg-white/10" />
        <div className="flex items-center gap-2">
          <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest">Per Mile</span>
          <span className="text-emerald-400 font-bold text-base leading-none tracking-tight">${load.per_mile_rate.toFixed(2)}/mi</span>
        </div>
        <div className="flex-1 text-right">
          <span className="text-[10px] text-slate-500 font-medium">{load.miles.toFixed(0)} total miles</span>
        </div>
      </div>

      {/* Recommended Carriers */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-white">Recommended Carriers</h3>
            <span className="text-xs text-[#555555] bg-[#1a1a1a] px-2 py-0.5 rounded font-mono-data">
              {carriers.length}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={selectAll}
              className="text-xs text-[#888888] hover:text-white transition-colors"
            >
              {selected.size === carriers.length && carriers.length > 0 ? 'Deselect all' : 'Select all'}
            </button>
            <button className="flex items-center gap-1.5 bg-white/10 hover:bg-white/20 text-white text-xs px-3 py-1.5 rounded transition-colors">
              <Phone className="w-3 h-3" />
              Call {selected.size > 0 ? `(${selected.size})` : ''}
            </button>
          </div>
        </div>

        <div className="bg-[#111111] border border-[#2a2a2a] rounded-lg overflow-hidden">
          {carriers.length === 0 ? (
            <div className="px-4 py-8 text-center text-[#555555] text-sm">
              No recommended carriers for this load
            </div>
          ) : (
            carriers.map(c => (
              <CarrierRow
                key={c.id}
                carrier={c}
                selected={selected.has(c.id)}
                onToggle={() => toggleCarrier(c.id)}
              />
            ))
          )}
        </div>
      </div>

      {/* Outbound Calls */}
      {outboundCalls.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-white mb-3">
            Outbound <span className="text-[#555555] font-normal ml-1 text-xs font-mono-data">({outboundCalls.length})</span>
          </h3>
          <div className="bg-[#111111] border border-[#2a2a2a] rounded-lg overflow-hidden divide-y divide-[#1a1a1a]">
            {outboundCalls.map(call => (
              <div key={call.id} className="flex items-center gap-3 px-4 py-3 hover:bg-[#1a1a1a] transition-colors">
                <Phone className="w-3.5 h-3.5 text-[#555555] shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white font-mono-data">{call.phone_number ?? 'Unknown'}</p>
                  <p className="text-xs text-[#555555]">{formatDateTime(call.call_start)}</p>
                </div>
                <StatusBadge status={call.outcome} />
                <button className="flex items-center gap-1 text-xs bg-white/10 hover:bg-white/20 text-white px-2.5 py-1.5 rounded transition-colors">
                  <Phone className="w-3 h-3" />
                  Call
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Inbound Calls */}
      {inboundCalls.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-white mb-3">
            Inbound <span className="text-[#555555] font-normal ml-1 text-xs font-mono-data">({inboundCalls.length})</span>
          </h3>
          <div className="bg-[#111111] border border-[#2a2a2a] rounded-lg overflow-hidden divide-y divide-[#1a1a1a]">
            {inboundCalls.map(call => (
              <div key={call.id} className="flex items-center gap-3 px-4 py-3 hover:bg-[#1a1a1a] transition-colors">
                <Phone className="w-3.5 h-3.5 text-[#555555] shrink-0 rotate-180" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white font-mono-data">{call.phone_number ?? 'Unknown'}</p>
                  <p className="text-xs text-[#555555]">{call.use_case}</p>
                </div>
                <p className="text-xs text-[#555555]">{formatDate(call.call_start)}</p>
                <StatusBadge status={call.outcome} />
              </div>
            ))}
          </div>
        </div>
      )}

      {calls.length === 0 && (
        <div className="text-center py-8 text-[#555555] text-sm">
          No call history for this load
        </div>
      )}
    </div>
  );
}

function AccountingTab({ load }: { load: Load }) {
  const isBooked = load.status === 'covered' || load.status === 'delivered';

  if (!isBooked) {
    return (
      <div className="space-y-4">
        <div className="bg-[#111111] border border-[#2a2a2a] rounded-lg p-5">
          <p className="text-xs text-[#555555] uppercase tracking-wider mb-4 font-mono-data">Rate Summary</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-[10px] text-[#555555] uppercase tracking-wider mb-1">Loadboard Rate</p>
              <p className="text-lg font-bold text-white font-mono-data">
                ${load.total_rate.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-[#555555] uppercase tracking-wider mb-1">Per Mile</p>
              <p className="text-lg font-bold text-green-400 font-mono-data">
                ${load.per_mile_rate.toFixed(2)}/mi
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 text-[#555555] text-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
          Financial data available once load is booked
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Core financial metrics */}
      <div className="bg-[#111111] border border-[#2a2a2a] rounded-lg overflow-hidden">
        <div className="px-5 py-3 border-b border-[#2a2a2a]">
          <p className="text-xs text-[#555555] uppercase tracking-wider font-mono-data">Financial Summary</p>
        </div>
        <div className="divide-y divide-[#1a1a1a]">
          <div className="flex items-center justify-between px-5 py-3">
            <span className="text-sm text-[#888888]">Loadboard Rate</span>
            <span className="text-sm font-mono-data text-white">
              ${load.total_rate.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </span>
          </div>
          {load.booked_rate != null && (
            <div className="flex items-center justify-between px-5 py-3">
              <span className="text-sm text-[#888888]">Booked Rate <span className="text-[#555555] text-xs">(carrier paid)</span></span>
              <span className="text-sm font-mono-data text-amber-400">
                ${load.booked_rate.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </span>
            </div>
          )}
          {load.margin_pct != null && (
            <div className="flex items-center justify-between px-5 py-3">
              <span className="text-sm text-[#888888]">Broker Margin</span>
              <span className={`text-sm font-mono-data font-bold ${load.margin_pct > 0 ? 'text-green-400' : 'text-red-400'}`}>
                {load.margin_pct.toFixed(1)}%
              </span>
            </div>
          )}
          <div className="flex items-center justify-between px-5 py-3">
            <span className="text-sm text-[#888888]">Per Mile</span>
            <span className="text-sm font-mono-data text-[#aaaaaa]">
              ${load.per_mile_rate.toFixed(2)}/mi
            </span>
          </div>
        </div>
      </div>

      {/* Booking metadata */}
      <div className="bg-[#111111] border border-[#2a2a2a] rounded-lg overflow-hidden">
        <div className="px-5 py-3 border-b border-[#2a2a2a]">
          <p className="text-xs text-[#555555] uppercase tracking-wider font-mono-data">Booking Info</p>
        </div>
        <div className="divide-y divide-[#1a1a1a]">
          <div className="flex items-center justify-between px-5 py-3">
            <span className="text-sm text-[#888888]">Booking Method</span>
            <span className={`text-xs font-mono-data px-2 py-0.5 rounded border ${
              load.is_ai_booked
                ? 'bg-blue-500/15 text-blue-400 border-blue-500/30'
                : 'bg-[#2a2a2a] text-[#888] border-[#333]'
            }`}>
              {load.is_ai_booked ? 'AI Automated' : 'Manual'}
            </span>
          </div>
          <div className="flex items-center justify-between px-5 py-3">
            <span className="text-sm text-[#888888]">Status</span>
            <span className={`text-xs font-mono-data px-2 py-0.5 rounded border ${
              load.status === 'delivered'
                ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                : 'bg-blue-500/15 text-blue-400 border-blue-500/30'
            }`}>
              {load.status.charAt(0).toUpperCase() + load.status.slice(1)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

interface LoadDetailProps {
  load: Load;
}

export function LoadDetail({ load }: LoadDetailProps) {
  const [activeTab, setActiveTab] = useState<Tab>('booking');
  const [notesExpanded, setNotesExpanded] = useState(false);

  const TABS: { key: Tab; label: string }[] = [
    { key: 'booking', label: 'Booking' },
    { key: 'accounting', label: 'Accounting' },
    { key: 'tracking', label: 'Tracking' },
  ];

  const formatDateLocal = (iso: string) =>
    new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  const formatTimeLocal = (iso: string) =>
    new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-8 py-5 border-b border-white/5 flex items-center justify-between shrink-0 bg-white/[0.01]">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-bold text-white font-heading tracking-tight">Load Ref: <span className="font-mono-data text-emerald-400">{load.load_id}</span></h2>
          <StatusBadge status={load.status} />
        </div>
        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.15em] font-heading">{load.equipment_type}</span>
      </div>

      {/* Route Info */}
      <div className="px-6 py-4 border-b border-[#2a2a2a] shrink-0">
        <div className="flex items-center gap-2 mb-3">
          <div className="flex-1">
            <p className="text-xs text-[#555555] uppercase tracking-wider mb-0.5">Origin</p>
            <p className="text-sm font-medium text-white">{load.origin}</p>
            <p className="text-xs text-[#666666]">{formatDateLocal(load.pickup_datetime)} · {formatTimeLocal(load.pickup_datetime)}</p>
          </div>
          <div className="text-[#333333] px-2">→</div>
          <div className="flex-1 text-right">
            <p className="text-xs text-[#555555] uppercase tracking-wider mb-0.5">Destination</p>
            <p className="text-sm font-medium text-white">{load.destination}</p>
            <p className="text-xs text-[#666666]">{formatDateLocal(load.delivery_datetime)} · {formatTimeLocal(load.delivery_datetime)}</p>
          </div>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-[#555555] font-mono-data">{load.miles.toFixed(0)} miles</span>
          <span className="text-green-400 font-mono-data font-medium">${load.per_mile_rate.toFixed(2)}/mi</span>
          <span className="text-white font-mono-data font-medium">${load.total_rate.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
        </div>
      </div>

      {/* Metadata grid */}
      <div className="px-8 py-6 border-b border-white/5 grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 shrink-0 bg-white/[0.005]">
        <MetadataChip label="Equipment" value={load.equipment_type} />
        <MetadataChip label="Commodity" value={load.commodity_type} />
        <MetadataChip label="Weight (Lbs)" value={`${(load.weight).toLocaleString()} lbs`} />
        <MetadataChip label="Cargo Pieces" value={load.num_of_pieces} />
        <MetadataChip label="Dimensions" value={load.dimensions ?? '—'} />
        <MetadataChip label="Reference ID" value={load.reference_id ?? '—'} />
      </div>

      {/* Notes (collapsible) */}
      {load.notes && (
        <div className="px-6 py-3 border-b border-[#2a2a2a] shrink-0">
          <button
            onClick={() => setNotesExpanded(!notesExpanded)}
            className="flex items-center gap-2 text-xs text-[#666666] hover:text-white transition-colors w-full"
          >
            {notesExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            Notes
          </button>
          {notesExpanded && (
            <p className="mt-2 text-sm text-[#888888] leading-relaxed">{load.notes}</p>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="px-6 border-b border-[#2a2a2a] flex gap-0 shrink-0">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={clsx(
              'px-4 py-3 text-sm transition-colors border-b-2 -mb-px',
              activeTab === key
                ? 'text-white border-white'
                : 'text-[#555555] border-transparent hover:text-[#888]'
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto px-6 py-5">
        {activeTab === 'booking' && <BookingTab load={load} />}
        {activeTab === 'accounting' && <AccountingTab load={load} />}
        {activeTab === 'tracking' && (
          <div className="space-y-4">
            <div className="bg-[#111111] border border-[#2a2a2a] rounded-lg p-5">
              <p className="text-xs text-[#555555] uppercase tracking-wider mb-4 font-mono-data">Shipment Timeline</p>
              <div className="space-y-3">
                {[
                  { label: 'Load Created', date: load.created_at, done: true },
                  { label: 'Pickup', date: load.pickup_datetime, done: new Date(load.pickup_datetime) < new Date() },
                  { label: 'In Transit', date: null, done: load.status === 'covered' || load.status === 'delivered' },
                  { label: 'Delivered', date: load.delivery_datetime, done: load.status === 'delivered' },
                ].map(({ label, date, done }, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${done ? 'bg-green-400' : 'bg-[#333]'}`} />
                    <div className="flex-1">
                      <span className={`text-sm ${done ? 'text-white' : 'text-[#555555]'}`}>{label}</span>
                    </div>
                    {date && (
                      <span className="text-xs font-mono-data text-[#555555]">
                        {new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
