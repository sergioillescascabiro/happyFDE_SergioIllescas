'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { MessageSquare } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import { Call, CallListResponse } from '@/types';
import { CallCard } from '@/components/communications/CallCard';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { PageLoader } from '@/components/ui/LoadingSpinner';
import { clsx } from 'clsx';

type MainTab = 'live' | 'all';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function formatDuration(seconds?: number): string {
  if (!seconds) return '—';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function LiveTab({ onPickUp }: { onPickUp: (msg: string) => void }) {
  const [calls, setCalls] = useState<Call[]>([]);
  const [loading, setLoading] = useState(true);
  const [useCaseFilter, setUseCaseFilter] = useState('all');

  const fetchLive = useCallback(async () => {
    try {
      const data = await apiFetch<Call[]>('/api/calls/live');
      setCalls(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initial load
    fetchLive();
    // Poll every 3 seconds for real-time updates
    const interval = setInterval(fetchLive, 3000);
    return () => clearInterval(interval);
  }, [fetchLive]);

  const useCases = ['all', ...Array.from(new Set(calls.map(c => c.use_case)))];
  const filtered = useCaseFilter === 'all' ? calls : calls.filter(c => c.use_case === useCaseFilter);

  if (loading) return <PageLoader />;

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center gap-3">
        <select
          value={useCaseFilter}
          onChange={e => setUseCaseFilter(e.target.value)}
          className="bg-[#111111] border border-[#2a2a2a] text-white text-sm rounded-md px-3 py-2 focus:outline-none focus:border-[#444]"
        >
          {useCases.map(uc => (
            <option key={uc} value={uc}>{uc === 'all' ? 'All Use Cases' : uc}</option>
          ))}
        </select>
        <span className="text-xs text-[#555555]">{filtered.length} calls</span>
      </div>

      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-[#555555]">
          <MessageSquare className="w-10 h-10 mb-3 opacity-30" />
          <p className="text-sm">No active calls</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map(call => (
            <CallCard
              key={call.id}
              call={call}
              onPickUp={() => onPickUp(`Barge-in feature — connecting you to the call with MC ${call.mc_number}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function AllCallsTab() {
  const [calls, setCalls] = useState<Call[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [outcomeFilter, setOutcomeFilter] = useState('');
  const [sentimentFilter, setSentimentFilter] = useState('');

  const fetchCalls = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: '25' });
      if (outcomeFilter) params.set('outcome', outcomeFilter);
      if (sentimentFilter) params.set('sentiment', sentimentFilter);
      const data = await apiFetch<CallListResponse>(`/api/calls?${params}`);
      setCalls(data.items);
      setTotal(data.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [page, outcomeFilter, sentimentFilter]);

  useEffect(() => { fetchCalls(); }, [fetchCalls]);

  const OUTCOMES = ['', 'booked', 'rejected', 'no_agreement', 'cancelled', 'carrier_not_authorized', 'transferred', 'in_progress'];
  const SENTIMENTS = ['', 'positive', 'neutral', 'negative'];

  return (
    <div className="space-y-4">
      {/* Filters row */}
      <div className="flex items-center gap-3 flex-wrap">
        <select
          value={outcomeFilter}
          onChange={e => { setOutcomeFilter(e.target.value); setPage(1); }}
          className="bg-[#111111] border border-[#2a2a2a] text-white text-sm rounded-md px-3 py-2 focus:outline-none focus:border-[#444]"
        >
          <option value="">All Outcomes</option>
          {OUTCOMES.filter(Boolean).map(o => (
            <option key={o} value={o}>{o.replace('_', ' ').replace(/^\w/, c => c.toUpperCase())}</option>
          ))}
        </select>
        <select
          value={sentimentFilter}
          onChange={e => { setSentimentFilter(e.target.value); setPage(1); }}
          className="bg-[#111111] border border-[#2a2a2a] text-white text-sm rounded-md px-3 py-2 focus:outline-none focus:border-[#444]"
        >
          <option value="">All Sentiments</option>
          {SENTIMENTS.filter(Boolean).map(s => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>
        <span className="text-xs text-[#555555]">{total} total calls</span>
      </div>

      {/* Table */}
      {loading ? (
        <PageLoader />
      ) : (
        <div className="bg-[#111111] border border-[#2a2a2a] rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#2a2a2a]">
                  {['Date', 'Carrier', 'MC#', 'Load', 'Direction', 'Outcome', 'Sentiment', 'Duration'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-[10px] text-[#555555] uppercase tracking-wider whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1a1a1a]">
                {calls.map(call => (
                  <React.Fragment key={call.id}>
                    <tr
                      onClick={() => setExpanded(expanded === call.id ? null : call.id)}
                      className="hover:bg-white/5 transition-colors cursor-pointer"
                    >
                      <td className="px-4 py-3 text-xs text-[#888888] whitespace-nowrap font-mono-data">
                        {formatDate(call.call_start)}<br />
                        <span className="text-[#555555]">{formatTime(call.call_start)}</span>
                      </td>
                      <td className="px-4 py-3 text-xs text-white truncate max-w-[140px]">{call.carrier_name ?? '—'}</td>
                      <td className="px-4 py-3 text-xs font-mono-data text-[#888888]">{call.mc_number}</td>
                      <td className="px-4 py-3 text-xs font-mono-data text-[#888888]">{call.load_load_id ?? '—'}</td>
                      <td className="px-4 py-3 text-xs text-[#888888] capitalize">{call.direction}</td>
                      <td className="px-4 py-3"><StatusBadge status={call.outcome} /></td>
                      <td className="px-4 py-3">
                        {call.sentiment ? <StatusBadge status={call.sentiment} /> : <span className="text-[#444444] text-xs">—</span>}
                      </td>
                      <td className="px-4 py-3 text-xs font-mono-data text-[#888888]">{formatDuration(call.duration_seconds)}</td>
                    </tr>
                    {expanded === call.id && (
                      <tr className="bg-[#0d0d0d]">
                        <td colSpan={8} className="px-4 py-4">
                          <div className="space-y-3">
                            {call.transcript_summary && (
                              <div>
                                <p className="text-xs text-[#555555] uppercase tracking-wider mb-1">Summary</p>
                                <p className="text-sm text-[#aaaaaa]">{call.transcript_summary}</p>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="px-4 py-3 border-t border-[#2a2a2a] flex items-center justify-between">
            <span className="text-xs text-[#555555]">Page {page}</span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 text-xs bg-[#1a1a1a] border border-[#2a2a2a] rounded text-[#888] hover:text-white disabled:opacity-30 transition-colors"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={calls.length < 25}
                className="px-3 py-1.5 text-xs bg-[#1a1a1a] border border-[#2a2a2a] rounded text-[#888] hover:text-white disabled:opacity-30 transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function CommunicationsPage() {
  const [activeTab, setActiveTab] = useState<MainTab>('live');
  const [toast, setToast] = useState('');

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 4000);
  };

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <MessageSquare className="w-5 h-5 text-[#555555]" />
          <h1 className="text-lg font-semibold text-white">Communications</h1>
        </div>
      </div>

      {/* Main tabs */}
      <div className="flex border-b border-[#2a2a2a] gap-0">
        {[
          { key: 'live' as MainTab, label: 'Live Communications' },
          { key: 'all' as MainTab, label: 'All Communications' },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={clsx(
              'px-5 py-3 text-sm transition-colors border-b-2 -mb-px',
              activeTab === key ? 'text-white border-white' : 'text-[#555555] border-transparent hover:text-[#888]'
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'live' ? (
        <LiveTab onPickUp={showToast} />
      ) : (
        <AllCallsTab />
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 bg-[#1a1a1a] border border-[#3a3a3a] text-white text-sm px-4 py-3 rounded-lg shadow-xl z-50 max-w-sm">
          {toast}
        </div>
      )}
    </div>
  );
}
