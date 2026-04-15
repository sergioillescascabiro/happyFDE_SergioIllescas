'use client';

import { useState, useEffect, useCallback, useRef, DragEvent } from 'react';
import { Search, Filter, Upload, Package, X, AlertCircle, CheckCircle } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import { Load, LoadListResponse } from '@/types';
import { LoadCard } from '@/components/loads/LoadCard';
import { LoadDetail } from '@/components/loads/LoadDetail';

type FilterStatus = 'all' | 'available' | 'pending' | 'covered' | 'cancelled' | 'delivered';

const STATUS_TABS: { key: FilterStatus; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'available', label: 'Available' },
  { key: 'pending', label: 'Pending' },
  { key: 'covered', label: 'Covered' },
  { key: 'cancelled', label: 'Cancelled' },
  { key: 'delivered', label: 'Delivered' },
];

// CSV column → API field mapping
const CSV_COLUMNS = [
  'load_id', 'shipper_id', 'origin', 'destination', 'pickup_datetime',
  'delivery_datetime', 'equipment_type', 'loadboard_rate', 'quoted_rate',
  'weight', 'commodity_type', 'miles', 'num_of_pieces', 'dimensions',
  'notes', 'reference_id',
];

type CsvRow = Record<string, string>;

function parseCSV(text: string): CsvRow[] {
  const lines = text.trim().split('\n');
  if (lines.length < 2) return [];
  const headers = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/\s+/g, '_'));
  return lines.slice(1).map(line => {
    const vals = line.split(',');
    const row: CsvRow = {};
    headers.forEach((h, i) => { row[h] = (vals[i] ?? '').trim(); });
    return row;
  }).filter(r => Object.values(r).some(v => v !== ''));
}

interface UploadModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

function UploadModal({ onClose, onSuccess }: UploadModalProps) {
  const [dragOver, setDragOver] = useState(false);
  const [rows, setRows] = useState<CsvRow[]>([]);
  const [fileName, setFileName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState<{ ok: number; errors: string[] } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      setRows(parseCSV(text));
    };
    reader.readAsText(file);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith('.csv')) handleFile(file);
  };

  const handleUpload = async () => {
    setUploading(true);
    const errors: string[] = [];
    let ok = 0;
    for (const row of rows) {
      try {
        const payload: Record<string, unknown> = {
          load_id: row.load_id || `LOAD-${Date.now()}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`,
          shipper_id: row.shipper_id,
          origin: row.origin,
          destination: row.destination,
          pickup_datetime: row.pickup_datetime,
          delivery_datetime: row.delivery_datetime,
          equipment_type: row.equipment_type || 'Dry Van',
          loadboard_rate: parseFloat(row.loadboard_rate) || 0,
          quoted_rate: parseFloat(row.quoted_rate) || parseFloat(row.loadboard_rate) * 1.2 || 0,
          weight: parseFloat(row.weight) || 0,
          commodity_type: row.commodity_type || 'General',
          miles: parseFloat(row.miles) || 1,
          num_of_pieces: parseInt(row.num_of_pieces) || 1,
          dimensions: row.dimensions || undefined,
          notes: row.notes || undefined,
          reference_id: row.reference_id || undefined,
          status: 'available',
        };
        await apiFetch('/api/loads', { method: 'POST', body: JSON.stringify(payload) });
        ok++;
      } catch (err) {
        errors.push(`Row ${rows.indexOf(row) + 1}: ${err instanceof Error ? err.message : 'Failed'}`);
      }
    }
    setResults({ ok, errors });
    setUploading(false);
    if (ok > 0) onSuccess();
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-[#111318] border border-[#2a2d3a] rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a2d3a]">
          <div>
            <h2 className="text-base font-semibold text-white">Upload Loads</h2>
            <p className="text-xs text-[#555555] mt-0.5">Import loads from a CSV file</p>
          </div>
          <button onClick={onClose} className="text-[#555555] hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Drop zone */}
          {rows.length === 0 && !results && (
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileRef.current?.click()}
              className={`border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors ${
                dragOver ? 'border-blue-500 bg-blue-500/5' : 'border-[#2a2d3a] hover:border-[#444] bg-[#0d1017]'
              }`}
            >
              <Upload className="w-8 h-8 mx-auto mb-3 text-[#555555]" />
              <p className="text-sm text-[#aaaaaa]">Drop a CSV file here, or <span className="text-blue-400 underline">browse</span></p>
              <p className="text-xs text-[#555555] mt-1">Required: origin, destination, pickup_datetime, delivery_datetime, loadboard_rate, quoted_rate, weight, commodity_type, miles, shipper_id</p>
              <input
                ref={fileRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
              />
            </div>
          )}

          {/* Preview */}
          {rows.length > 0 && !results && (
            <>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-400" />
                  <span className="text-sm text-white">{fileName}</span>
                  <span className="text-xs text-[#555555] font-mono-data">{rows.length} rows parsed</span>
                </div>
                <button onClick={() => { setRows([]); setFileName(''); }} className="text-xs text-[#555555] hover:text-white">
                  Clear
                </button>
              </div>
              <div className="overflow-x-auto rounded-lg border border-[#2a2d3a]">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-[#2a2d3a]">
                      {CSV_COLUMNS.filter(c => rows[0]?.[c] !== undefined).map(col => (
                        <th key={col} className="px-3 py-2 text-left text-[#555555] uppercase tracking-wider whitespace-nowrap font-mono-data">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1a1a1a]">
                    {rows.slice(0, 5).map((row, i) => (
                      <tr key={i} className="hover:bg-white/5">
                        {CSV_COLUMNS.filter(c => rows[0]?.[c] !== undefined).map(col => (
                          <td key={col} className="px-3 py-2 text-[#aaaaaa] font-mono-data whitespace-nowrap max-w-[120px] truncate">
                            {row[col] ?? '—'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {rows.length > 5 && (
                <p className="text-xs text-[#555555] text-center">+{rows.length - 5} more rows</p>
              )}
            </>
          )}

          {/* Results */}
          {results && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-green-400">
                <CheckCircle className="w-5 h-5" />
                <span className="text-sm font-medium">{results.ok} load{results.ok !== 1 ? 's' : ''} created successfully</span>
              </div>
              {results.errors.length > 0 && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 space-y-1">
                  <div className="flex items-center gap-2 text-red-400 text-xs font-medium mb-2">
                    <AlertCircle className="w-4 h-4" />
                    {results.errors.length} error{results.errors.length !== 1 ? 's' : ''}
                  </div>
                  {results.errors.map((e, i) => (
                    <p key={i} className="text-xs text-red-300 font-mono-data">{e}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#2a2d3a]">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-[#888] hover:text-white border border-[#2a2d3a] hover:border-[#444] rounded-md transition-colors"
          >
            {results ? 'Close' : 'Cancel'}
          </button>
          {rows.length > 0 && !results && (
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="px-4 py-2 text-sm bg-white text-black font-medium rounded-md hover:bg-white/90 disabled:opacity-50 transition-colors"
            >
              {uploading ? `Uploading ${rows.length} loads…` : `Upload ${rows.length} Load${rows.length !== 1 ? 's' : ''}`}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function LoadsPage() {
  const [loads, setLoads] = useState<Load[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedLoad, setSelectedLoad] = useState<Load | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all');
  const [toast, setToast] = useState('');
  const [showUploadModal, setShowUploadModal] = useState(false);

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
          onClick={() => setShowUploadModal(true)}
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

      {/* Upload Modal */}
      {showUploadModal && (
        <UploadModal
          onClose={() => setShowUploadModal(false)}
          onSuccess={() => {
            showToast('Loads uploaded successfully');
            fetchLoads();
          }}
        />
      )}
    </div>
  );
}
