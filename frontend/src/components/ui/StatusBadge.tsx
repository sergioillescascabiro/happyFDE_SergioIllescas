import { clsx } from 'clsx';

type Status = 'available' | 'pending' | 'covered' | 'cancelled' | 'active' | 'in_review' | 'suspended' | 'inactive' | 'positive' | 'neutral' | 'negative' | 'booked' | 'rejected' | 'no_agreement' | 'transferred' | 'in_progress' | 'carrier_not_authorized' | 'no_loads_available';

const STATUS_CONFIG: Record<Status, { label: string; className: string }> = {
  available:             { label: 'Available',           className: 'bg-green-500/15 text-green-400 border-green-500/30' },
  pending:               { label: 'Pending',             className: 'bg-amber-500/15 text-amber-400 border-amber-500/30' },
  covered:               { label: 'Covered',             className: 'bg-blue-500/15 text-blue-400 border-blue-500/30' },
  cancelled:             { label: 'Cancelled',           className: 'bg-red-500/15 text-red-400 border-red-500/30' },
  active:                { label: 'Active',              className: 'bg-green-500/15 text-green-400 border-green-500/30' },
  in_review:             { label: 'In Review',           className: 'bg-amber-500/15 text-amber-400 border-amber-500/30' },
  suspended:             { label: 'Suspended',           className: 'bg-red-500/15 text-red-400 border-red-500/30' },
  inactive:              { label: 'Inactive',            className: 'bg-[#333]/50 text-[#888] border-[#444]/30' },
  positive:              { label: 'Positive',            className: 'bg-green-500/15 text-green-400 border-green-500/30' },
  neutral:               { label: 'Neutral',             className: 'bg-[#333]/50 text-[#aaa] border-[#444]/30' },
  negative:              { label: 'Negative',            className: 'bg-red-500/15 text-red-400 border-red-500/30' },
  booked:                { label: 'Booked',              className: 'bg-green-500/15 text-green-400 border-green-500/30' },
  rejected:              { label: 'Rejected',            className: 'bg-red-500/15 text-red-400 border-red-500/30' },
  no_agreement:          { label: 'No Agreement',        className: 'bg-amber-500/15 text-amber-400 border-amber-500/30' },
  transferred:           { label: 'Transferred',         className: 'bg-blue-500/15 text-blue-400 border-blue-500/30' },
  in_progress:           { label: 'In Progress',         className: 'bg-purple-500/15 text-purple-400 border-purple-500/30' },
  carrier_not_authorized:{ label: 'Not Authorized',      className: 'bg-red-500/15 text-red-400 border-red-500/30' },
  no_loads_available:    { label: 'No Loads',            className: 'bg-[#333]/50 text-[#888] border-[#444]/30' },
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const config = STATUS_CONFIG[status as Status] ?? { label: status, className: 'bg-[#333]/50 text-[#888] border-[#444]/30' };
  return (
    <span className={clsx(
      'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border font-mono-data',
      config.className,
      className
    )}>
      {config.label}
    </span>
  );
}
