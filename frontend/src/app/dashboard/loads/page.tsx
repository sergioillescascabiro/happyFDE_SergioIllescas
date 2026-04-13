'use client';

import { useState, useEffect, useCallback } from 'react';
import { Search, Filter, Upload, Package } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import { Load, LoadListResponse } from '@/types';
import { LoadCard } from '@/components/loads/LoadCard';
import { LoadDetail } from '@/components/loads/LoadDetail';

type FilterStatus = 'all' | 'available' | 'pending' | 'covered' | 'cancelled';

const STATUS_TABS: { key: FilterStatus; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'available', label: 'Available' },
  { key: 'pending', label: 'Pending' },
  { key: 'covered', label: 'Covered' },
  { key: 'cancelled', label: 'Cancelled' },
];

export default function LoadsPage() {
  const [loads, setLoads] = useState<Load[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedLoad, setSelectedLoad] = useState<Load | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all');
  const [toast, setToast] = useState('');

  const fetchLoads = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page_size: '50' });
      if (statusFilter !== 'all') params.set('status', statusFilter);
      if (search) params.set('search', search);

      const data = await apiFetch<LoadListResponse>(`/api/loads?${params}`);
      setLoads(data.items);
      setTotal(data.total);
      if (!selectedLoad && data.items.length > 0) {
        setSelectedLoad(data.items[0]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, search]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const t = setTimeout(fetchLoads, search ? 300 : 0);
    return () => clearTimeout(t);
  }, [fetchLoads, search]);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  };

  return (
    <div className="h-screen flex flex-col">
      {/* Page header */}
      <div className="px-6 py-4 border-b border-[#2a2a2a] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <Package className="w-5 h-5 text-[#555555]" />
          <h1 className="text-lg font-semibold text-white">Loads</h1>
          <span className="text-xs text-[#555555] font-mono-data bg-[#1a1a1a] px-2 py-0.5 rounded">{total}</span>
        </div>
        <button
          onClick={() => showToast('Upload feature coming soon')}
          className="flex items-center gap-2 bg-white/10 hover:bg-white/15 text-white text-sm px-3 py-2 rounded-md transition-colors"
        >
          <Upload className="w-4 h-4" />
          Upload Loads
        </button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* LEFT PANEL */}
        <div className="w-80 shrink-0 border-r border-[#2a2a2a] flex flex-col bg-[#0a0a0a]">
          {/* Search + Filter */}
          <div className="p-3 border-b border-[#2a2a2a] flex gap-2">
            <div className="flex-1 flex items-center gap-2 bg-[#111111] border border-[#2a2a2a] rounded-md px-3 py-2">
              <Search className="w-3.5 h-3.5 text-[#555555] shrink-0" />
              <input
                type="text"
                placeholder="Search loads..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="bg-transparent text-sm text-white placeholder-[#444444] outline-none w-full"
              />
            </div>
            <button className="p-2 bg-[#111111] border border-[#2a2a2a] rounded-md text-[#555555] hover:text-white transition-colors">
              <Filter className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Status filter tabs */}
          <div className="flex overflow-x-auto border-b border-[#2a2a2a] shrink-0">
            {STATUS_TABS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setStatusFilter(key)}
                className={`px-3 py-2 text-xs whitespace-nowrap transition-colors border-b-2 -mb-px ${
                  statusFilter === key
                    ? 'text-white border-white'
                    : 'text-[#555555] border-transparent hover:text-[#888]'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Load list */}
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="w-5 h-5 border-2 border-white/10 border-t-white/60 rounded-full animate-spin" />
              </div>
            ) : loads.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-[#555555] text-sm">
                <Package className="w-8 h-8 mb-3 opacity-30" />
                No loads found
              </div>
            ) : (
              loads.map(load => (
                <LoadCard
                  key={load.id}
                  load={load}
                  isSelected={selectedLoad?.id === load.id}
                  onClick={() => setSelectedLoad(load)}
                />
              ))
            )}
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div className="flex-1 overflow-hidden bg-[#0d0d0d]">
          {selectedLoad ? (
            <LoadDetail load={selectedLoad} />
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center text-[#444444]">
                <Package className="w-12 h-12 mx-auto mb-3 opacity-20" />
                <p className="text-sm">Select a load to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 bg-[#1a1a1a] border border-[#3a3a3a] text-white text-sm px-4 py-3 rounded-lg shadow-xl z-50 animate-in">
          {toast}
        </div>
      )}
    </div>
  );
}
