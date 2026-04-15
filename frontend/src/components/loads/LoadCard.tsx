'use client';

import { clsx } from 'clsx';
import { Load } from '@/types';
import { StatusBadge } from '@/components/ui/StatusBadge';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function isLate(load: Load): boolean {
  return load.status === 'available' && new Date(load.pickup_datetime) < new Date();
}

interface LoadCardProps {
  load: Load;
  isSelected: boolean;
  onClick: () => void;
}

export function LoadCard({ load, isSelected, onClick }: LoadCardProps) {
  const late = isLate(load);

  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full text-left px-5 py-5 border-b border-white/5 transition-all relative group',
        isSelected ? 'bg-emerald-500/[0.03]' : 'hover:bg-white/[0.02]'
      )}
    >
      {isSelected && (
        <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.5)]" />
      )}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold text-slate-100 font-mono-data uppercase tracking-tight opacity-90">{load.load_id}</span>
          {late && (
            <span className="text-[9px] font-bold text-rose-400 bg-rose-500/10 border border-rose-500/20 px-1.5 py-0.5 rounded-full font-mono-data">
              LATE
            </span>
          )}
        </div>
        <StatusBadge status={load.status} />
      </div>

      <div className="flex items-center gap-1.5 mb-3">
        <span className="text-sm font-semibold text-white truncate max-w-[120px]">{load.origin}</span>
        <span className="text-slate-700 text-xs shrink-0 mx-0.5">→</span>
        <span className="text-sm font-semibold text-white truncate max-w-[120px]">{load.destination}</span>
      </div>

      <div className="flex items-center gap-2.5 text-[10px] text-slate-500 font-bold font-mono-data uppercase tracking-wider">
        <span className="bg-white/5 px-2 py-0.5 rounded text-slate-400">{formatDate(load.pickup_datetime)}</span>
        <span className="text-slate-800">|</span>
        <span className="text-emerald-500/80">{load.miles.toFixed(0)} mi</span>
        <span className="text-slate-800">|</span>
        <span>{load.equipment_type}</span>
      </div>
    </button>
  );
}
