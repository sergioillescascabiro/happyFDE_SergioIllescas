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
        'w-full text-left px-4 py-4 border-b border-[#1a1a1a] transition-colors hover:bg-[#1a1a1a]',
        isSelected ? 'bg-[#1a1a1a] border-l-2 border-l-white' : 'border-l-2 border-l-transparent'
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-white font-mono-data">{load.load_id}</span>
          {late && (
            <span className="text-[10px] font-bold text-red-400 bg-red-500/10 border border-red-500/20 px-1.5 py-0.5 rounded font-mono-data">
              LATE
            </span>
          )}
        </div>
        <StatusBadge status={load.status} />
      </div>

      <div className="flex items-center gap-1.5 mb-2">
        <span className="text-xs text-[#aaaaaa] truncate max-w-[120px]">{load.origin}</span>
        <span className="text-[#444444] text-xs shrink-0">→</span>
        <span className="text-xs text-[#aaaaaa] truncate max-w-[120px]">{load.destination}</span>
      </div>

      <div className="flex items-center gap-3 text-[10px] text-[#555555] font-mono-data">
        <span>{formatDate(load.pickup_datetime)}</span>
        <span>·</span>
        <span>{load.miles.toFixed(0)} mi</span>
        <span>·</span>
        <span>{load.equipment_type}</span>
      </div>
    </button>
  );
}
