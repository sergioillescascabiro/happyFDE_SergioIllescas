'use client';

import { useState, useEffect, useCallback, useRef, DragEvent } from 'react';
import { Search, Filter, Upload, Package, X, AlertCircle, CheckCircle } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import { Load, LoadListResponse, Shipper } from '@/types';
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

function generateLoadId(): string {
  const now = new Date();
  const date = now.toISOString().slice(0, 10).replace(/-/g, '');
  const rand = Math.random().toString(36).slice(2, 6).toUpperCase();
  return `LOAD-${date}-${rand}`;
}

const EQUIPMENT_TYPES = ['Dry Van', 'Flatbed', 'Reefer', 'Step Deck', 'RGN'];

interface ManualFormData {
  origin: string;
  destination: string;
  pickup_datetime: string;
  delivery_datetime: string;
  equipment_type: string;
  loadboard_rate: string;
  quoted_rate: string;
  weight: string;
  commodity_type: string;
  miles: string;
  shipper_id: string;
  num_of_pieces: string;
  dimensions: string;
  reference_id: string;
  notes: string;
}

interface ManualFormErrors {
  origin?: string;
  destination?: string;
  pickup_datetime?: string;
  delivery_datetime?: string;
  equipment_type?: string;
  loadboard_rate?: string;
  quoted_rate?: string;
  weight?: string;
  commodity_type?: string;
  miles?: string;
  shipper_id?: string;
}

const INPUT_CLS = 'bg-white/[0.03] border border-white/10 text-slate-100 text-sm rounded-lg px-4 py-2.5 w-full focus:outline-none focus:ring-1 focus:ring-emerald-500/50 transition-all font-sans';
const LABEL_CLS = 'text-[10px] font-heading font-bold text-slate-500 mb-1.5 block uppercase tracking-wider';
const ERROR_CLS = 'text-[10px] text-rose-400 mt-1 font-medium';
const REQ = <span className="text-rose-500 ml-1">*</span>;

interface UploadModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

function UploadModal({ onClose, onSuccess }: UploadModalProps) {
  const [activeTab, setActiveTab] = useState<'csv' | 'manual'>('csv');

  // CSV state
  const [dragOver, setDragOver] = useState(false);
  const [rows, setRows] = useState<CsvRow[]>([]);
  const [fileName, setFileName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState<{ ok: number; errors: string[] } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Manual form state
  const [shippers, setShippers] = useState<Shipper[]>([]);
  const [form, setForm] = useState<ManualFormData>({
    origin: '', destination: '', pickup_datetime: '', delivery_datetime: '',
    equipment_type: 'Dry Van', loadboard_rate: '', quoted_rate: '',
    weight: '', commodity_type: '', miles: '', shipper_id: '',
    num_of_pieces: '', dimensions: '', reference_id: '', notes: '',
  });
  const [formErrors, setFormErrors] = useState<ManualFormErrors>({});
  const [manualSubmitting, setManualSubmitting] = useState(false);
  const [manualResult, setManualResult] = useState<{ ok: boolean; message: string } | null>(null);

  useEffect(() => {
    apiFetch<Shipper[]>('/api/shippers').then(setShippers).catch(() => {});
  }, []);

  // ── CSV handlers ────────────────────────────────────────────────────────────

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
          load_id: row.load_id || generateLoadId(),
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

  // ── Manual form handlers ────────────────────────────────────────────────────

  const setField = (key: keyof ManualFormData, value: string) => {
    setForm(prev => ({ ...prev, [key]: value }));
    if (formErrors[key as keyof ManualFormErrors]) {
      setFormErrors(prev => ({ ...prev, [key]: undefined }));
    }
  };

  const validateManual = (): ManualFormErrors => {
    const errs: ManualFormErrors = {};
    if (!form.origin.trim()) errs.origin = 'Origin is required';
    if (!form.destination.trim()) errs.destination = 'Destination is required';
    if (!form.pickup_datetime) errs.pickup_datetime = 'Pickup date is required';
    if (!form.delivery_datetime) errs.delivery_datetime = 'Delivery date is required';
    else if (form.pickup_datetime && new Date(form.delivery_datetime) <= new Date(form.pickup_datetime)) {
      errs.delivery_datetime = 'Delivery must be after pickup';
    }
    if (!form.equipment_type) errs.equipment_type = 'Equipment type is required';
    const lb = parseFloat(form.loadboard_rate);
    if (!form.loadboard_rate || isNaN(lb) || lb < 100) errs.loadboard_rate = 'Loadboard rate must be ≥ $100';
    const qr = parseFloat(form.quoted_rate);
    if (!form.quoted_rate || isNaN(qr) || qr < 100) errs.quoted_rate = 'Quoted rate must be ≥ $100';
    else if (!isNaN(lb) && qr <= lb) errs.quoted_rate = 'Quoted rate must exceed loadboard rate';
    const wt = parseFloat(form.weight);
    if (!form.weight || isNaN(wt) || wt < 1) errs.weight = 'Weight must be ≥ 1 lbs';
    if (!form.commodity_type.trim()) errs.commodity_type = 'Commodity type is required';
    const mi = parseFloat(form.miles);
    if (!form.miles || isNaN(mi) || mi < 1) errs.miles = 'Miles must be ≥ 1';
    if (!form.shipper_id) errs.shipper_id = 'Shipper is required';
    return errs;
  };

  const handleManualSubmit = async () => {
    const errs = validateManual();
    if (Object.keys(errs).length > 0) {
      setFormErrors(errs);
      return;
    }
    setManualSubmitting(true);
    setManualResult(null);
    try {
      const payload: Record<string, unknown> = {
        load_id: generateLoadId(),
        shipper_id: form.shipper_id,
        origin: form.origin.trim(),
        destination: form.destination.trim(),
        pickup_datetime: form.pickup_datetime,
        delivery_datetime: form.delivery_datetime,
        equipment_type: form.equipment_type,
        loadboard_rate: parseFloat(form.loadboard_rate),
        quoted_rate: parseFloat(form.quoted_rate),
        weight: parseFloat(form.weight),
        commodity_type: form.commodity_type.trim(),
        miles: parseFloat(form.miles),
        num_of_pieces: form.num_of_pieces ? parseInt(form.num_of_pieces) : 1,
        dimensions: form.dimensions.trim() || undefined,
        reference_id: form.reference_id.trim() || undefined,
        notes: form.notes.trim() || undefined,
        status: 'available',
      };
      await apiFetch('/api/loads', { method: 'POST', body: JSON.stringify(payload) });
      setManualResult({ ok: true, message: 'Load created successfully' });
      onSuccess();
      // Reset form
      setForm({
        origin: '', destination: '', pickup_datetime: '', delivery_datetime: '',
        equipment_type: 'Dry Van', loadboard_rate: '', quoted_rate: '',
        weight: '', commodity_type: '', miles: '', shipper_id: '',
        num_of_pieces: '', dimensions: '', reference_id: '', notes: '',
      });
      setFormErrors({});
    } catch (err) {
      setManualResult({ ok: false, message: err instanceof Error ? err.message : 'Failed to create load' });
    } finally {
      setManualSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-[#030303]/80 backdrop-filter blur-sm border-white/5 border flex items-center justify-center z-50 p-4">
      <div className="glass-card rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl animate-in">
        {/* Header */}
        <div className="flex items-center justify-between px-8 py-5 border-b border-white/5">
          <div>
            <h2 className="text-xl font-heading font-bold text-white tracking-tight">Post New Loads</h2>
            <p className="text-xs text-slate-500 mt-0.5">Automate your lifecycle by importing cargo data</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full text-slate-500 hover:text-white transition-all">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab switcher */}
        <div className="flex border-b border-[#2a2d3a] px-6">
          {(['csv', 'manual'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 text-sm transition-colors border-b-2 -mb-px ${
                activeTab === tab
                  ? 'text-white border-white'
                  : 'text-[#555555] border-transparent hover:text-[#888]'
              }`}
            >
              {tab === 'csv' ? 'CSV Upload' : 'Add Manually'}
            </button>
          ))}
        </div>

        {/* ── CSV Tab ── */}
        {activeTab === 'csv' && (
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

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 pt-2">
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
        )}

        {/* ── Manual Tab ── */}
        {activeTab === 'manual' && (
          <div className="p-6 space-y-5">
            {manualResult && (
              <div className={`flex items-center gap-2 text-sm rounded-lg px-4 py-3 border ${
                manualResult.ok
                  ? 'bg-green-500/10 border-green-500/30 text-green-400'
                  : 'bg-red-500/10 border-red-500/30 text-red-400'
              }`}>
                {manualResult.ok ? <CheckCircle className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
                {manualResult.message}
              </div>
            )}

            {/* Required fields grid */}
            <div className="grid grid-cols-2 gap-4">
              {/* Origin */}
              <div>
                <label className={LABEL_CLS}>Origin{REQ}</label>
                <input
                  type="text"
                  placeholder="Chicago, IL"
                  value={form.origin}
                  onChange={e => setField('origin', e.target.value)}
                  className={INPUT_CLS}
                />
                {formErrors.origin && <p className={ERROR_CLS}>{formErrors.origin}</p>}
              </div>

              {/* Destination */}
              <div>
                <label className={LABEL_CLS}>Destination{REQ}</label>
                <input
                  type="text"
                  placeholder="Dallas, TX"
                  value={form.destination}
                  onChange={e => setField('destination', e.target.value)}
                  className={INPUT_CLS}
                />
                {formErrors.destination && <p className={ERROR_CLS}>{formErrors.destination}</p>}
              </div>

              {/* Pickup Date/Time */}
              <div>
                <label className={LABEL_CLS}>Pickup Date/Time{REQ}</label>
                <input
                  type="datetime-local"
                  value={form.pickup_datetime}
                  onChange={e => setField('pickup_datetime', e.target.value)}
                  className={INPUT_CLS}
                />
                {formErrors.pickup_datetime && <p className={ERROR_CLS}>{formErrors.pickup_datetime}</p>}
              </div>

              {/* Delivery Date/Time */}
              <div>
                <label className={LABEL_CLS}>Delivery Date/Time{REQ}</label>
                <input
                  type="datetime-local"
                  value={form.delivery_datetime}
                  onChange={e => setField('delivery_datetime', e.target.value)}
                  className={INPUT_CLS}
                />
                {formErrors.delivery_datetime && <p className={ERROR_CLS}>{formErrors.delivery_datetime}</p>}
              </div>

              {/* Equipment Type */}
              <div>
                <label className={LABEL_CLS}>Equipment Type{REQ}</label>
                <select
                  value={form.equipment_type}
                  onChange={e => setField('equipment_type', e.target.value)}
                  className={INPUT_CLS}
                >
                  {EQUIPMENT_TYPES.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                {formErrors.equipment_type && <p className={ERROR_CLS}>{formErrors.equipment_type}</p>}
              </div>

              {/* Shipper */}
              <div>
                <label className={LABEL_CLS}>Shipper{REQ}</label>
                <select
                  value={form.shipper_id}
                  onChange={e => setField('shipper_id', e.target.value)}
                  className={INPUT_CLS}
                >
                  <option value="">Select shipper…</option>
                  {shippers.map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
                {formErrors.shipper_id && <p className={ERROR_CLS}>{formErrors.shipper_id}</p>}
              </div>

              {/* Loadboard Rate */}
              <div>
                <label className={LABEL_CLS}>Loadboard Rate ($){REQ}</label>
                <input
                  type="number"
                  min="100"
                  placeholder="1000"
                  value={form.loadboard_rate}
                  onChange={e => setField('loadboard_rate', e.target.value)}
                  className={INPUT_CLS}
                />
                {formErrors.loadboard_rate && <p className={ERROR_CLS}>{formErrors.loadboard_rate}</p>}
              </div>

              {/* Quoted Rate */}
              <div>
                <label className={LABEL_CLS}>Quoted Rate ($){REQ}</label>
                <input
                  type="number"
                  min="100"
                  placeholder="1250"
                  value={form.quoted_rate}
                  onChange={e => setField('quoted_rate', e.target.value)}
                  className={INPUT_CLS}
                />
                {formErrors.quoted_rate && <p className={ERROR_CLS}>{formErrors.quoted_rate}</p>}
              </div>

              {/* Weight */}
              <div>
                <label className={LABEL_CLS}>Weight (lbs){REQ}</label>
                <input
                  type="number"
                  min="1"
                  placeholder="45000"
                  value={form.weight}
                  onChange={e => setField('weight', e.target.value)}
                  className={INPUT_CLS}
                />
                {formErrors.weight && <p className={ERROR_CLS}>{formErrors.weight}</p>}
              </div>

              {/* Commodity Type */}
              <div>
                <label className={LABEL_CLS}>Commodity Type{REQ}</label>
                <input
                  type="text"
                  placeholder="General Freight"
                  value={form.commodity_type}
                  onChange={e => setField('commodity_type', e.target.value)}
                  className={INPUT_CLS}
                />
                {formErrors.commodity_type && <p className={ERROR_CLS}>{formErrors.commodity_type}</p>}
              </div>

              {/* Miles */}
              <div>
                <label className={LABEL_CLS}>Miles{REQ}</label>
                <input
                  type="number"
                  min="1"
                  placeholder="410"
                  value={form.miles}
                  onChange={e => setField('miles', e.target.value)}
                  className={INPUT_CLS}
                />
                {formErrors.miles && <p className={ERROR_CLS}>{formErrors.miles}</p>}
              </div>

              {/* Num of Pieces (optional) */}
              <div>
                <label className={LABEL_CLS}>Num of Pieces</label>
                <input
                  type="number"
                  min="1"
                  placeholder="1"
                  value={form.num_of_pieces}
                  onChange={e => setField('num_of_pieces', e.target.value)}
                  className={INPUT_CLS}
                />
              </div>
            </div>

            {/* Optional single-column fields */}
            <div className="grid grid-cols-2 gap-4">
              {/* Dimensions (optional) */}
              <div>
                <label className={LABEL_CLS}>Dimensions</label>
                <input
                  type="text"
                  placeholder="48x48x96"
                  value={form.dimensions}
                  onChange={e => setField('dimensions', e.target.value)}
                  className={INPUT_CLS}
                />
              </div>

              {/* Reference ID (optional) */}
              <div>
                <label className={LABEL_CLS}>Reference ID</label>
                <input
                  type="text"
                  placeholder="REF-001"
                  value={form.reference_id}
                  onChange={e => setField('reference_id', e.target.value)}
                  className={INPUT_CLS}
                />
              </div>
            </div>

            {/* Notes (optional) */}
            <div>
              <label className={LABEL_CLS}>Notes</label>
              <textarea
                rows={3}
                placeholder="Additional notes…"
                value={form.notes}
                onChange={e => setField('notes', e.target.value)}
                className={INPUT_CLS + ' resize-none'}
              />
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm text-[#888] hover:text-white border border-[#2a2d3a] hover:border-[#444] rounded-md transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleManualSubmit}
                disabled={manualSubmitting}
                className="px-4 py-2 text-sm bg-[#10b981] hover:bg-[#0d9668] text-white font-medium rounded-md disabled:opacity-50 transition-colors"
              >
                {manualSubmitting ? 'Creating…' : 'Create Load'}
              </button>
            </div>
          </div>
        )}
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
    <div className="h-screen flex flex-col bg-[#030303]">
      {/* Page header */}
      <div className="px-8 py-5 border-b border-white/5 flex items-center justify-between shrink-0 bg-white/[0.01]">
        <div className="flex items-center gap-4">
          <div className="p-2 bg-emerald-500/10 rounded-lg">
            <Package className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-xl font-heading font-bold text-white tracking-tight">Cargo Management</h1>
            <p className="text-xs text-slate-500 mt-0.5">{total} active shipments found</p>
          </div>
        </div>
        <button
          onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-2 bg-emerald-500 text-[#030303] text-xs font-bold font-heading uppercase tracking-wider px-5 py-2.5 rounded-full hover:bg-emerald-400 transition-all shadow-lg shadow-emerald-500/10"
        >
          <Upload className="w-4 h-4" />
          Import Cargo
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
            showToast('Load created successfully');
            fetchLoads();
          }}
        />
      )}
    </div>
  );
}
