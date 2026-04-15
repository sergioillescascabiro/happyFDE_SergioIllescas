import { clsx } from 'clsx';

type Status = 'available' | 'pending' | 'covered' | 'cancelled' | 'delivered' | 'active' | 'in_review' | 'suspended' | 'inactive' | 'positive' | 'neutral' | 'negative' | 'booked' | 'rejected' | 'no_agreement' | 'transferred' | 'in_progress' | 'carrier_not_authorized' | 'no_loads_available';

const STATUS_CONFIG: Record<Status, { label: string; className: string }> = {
  available:             { label: 'Available',           className: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  pending:               { label: 'Pending',             className: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
  covered:               { label: 'Covered',             className: 'bg-sky-500/10 text-sky-400 border-sky-500/20' },
  cancelled:             { label: 'Cancelled',           className: 'bg-rose-500/10 text-rose-400 border-rose-500/20' },
  delivered:             { label: 'Delivered',           className: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20' },
  active:                { label: 'Active',              className: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  in_review:             { label: 'In Review',           className: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
  suspended:             { label: 'Suspended',           className: 'bg-rose-500/10 text-rose-400 border-rose-500/20' },
  inactive:              { label: 'Inactive',            className: 'bg-slate-500/10 text-slate-500 border-slate-500/20' },
  positive:              { label: 'Positive',            className: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  neutral:               { label: 'Neutral',             className: 'bg-slate-500/10 text-slate-400 border-slate-500/20' },
  negative:              { label: 'Negative',            className: 'bg-rose-500/10 text-rose-400 border-rose-500/20' },
  booked:                { label: 'Booked',              className: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  rejected:              { label: 'Rejected',            className: 'bg-rose-500/10 text-rose-400 border-rose-500/20' },
  no_agreement:          { label: 'No Agreement',        className: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
  transferred:           { label: 'Transferred',         className: 'bg-sky-500/10 text-sky-400 border-sky-500/20' },
  in_progress:           { label: 'In Progress',         className: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' },
  carrier_not_authorized:{ label: 'Not Authorized',      className: 'bg-rose-500/10 text-rose-400 border-rose-500/20' },
  no_loads_available:    { label: 'No Loads',            className: 'bg-slate-500/10 text-slate-500 border-slate-500/20' },
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const config = STATUS_CONFIG[status as Status] ?? { label: status, className: 'bg-slate-500/10 text-slate-500 border-slate-500/20' };
  return (
    <span className={clsx(
      'inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border font-mono-data tracking-tight',
      config.className,
      className
    )}>
      {config.label}
    </span>
  );
}
