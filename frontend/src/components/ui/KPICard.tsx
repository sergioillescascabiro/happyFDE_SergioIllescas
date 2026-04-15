import { clsx } from 'clsx';
import { LucideIcon, Info } from 'lucide-react';

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  icon?: LucideIcon;
  valueClassName?: string;
  description?: string;
}

export function KPICard({ title, value, subtitle, trend, trendValue, icon: Icon, valueClassName, description }: KPICardProps) {
  return (
    <div className="glass-card rounded-xl p-5 flex flex-col gap-3 transition-all hover:translate-y-[-2px] hover:border-emerald-500/20 group animate-in relative">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 group/info">
          <span className="text-slate-500 text-[10px] font-heading font-semibold uppercase tracking-[0.1em]">{title}</span>
          {description && (
            <div className="relative">
              <Info className="w-3 h-3 text-slate-700 hover:text-emerald-400 transition-colors cursor-help" />
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-[#111111] border border-white/10 rounded-lg text-[10px] text-slate-400 font-medium leading-relaxed opacity-0 group-hover/info:opacity-100 pointer-events-none transition-opacity z-50 shadow-2xl">
                {description}
                <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-[#111111]" />
              </div>
            </div>
          )}
        </div>
        {Icon && <Icon className="w-4 h-4 text-slate-600 group-hover:text-emerald-500 transition-colors" />}
      </div>
      <div className="flex items-end justify-between gap-2">
        <span className={clsx('text-2xl font-bold font-mono-data tracking-tight', valueClassName ?? 'text-white')}>
          {value}
        </span>
        {trend && trendValue && (
          <span className={clsx(
            'text-[10px] font-mono-data mb-0.5 px-1.5 py-0.5 rounded-md bg-white/5',
            trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-rose-400' : 'text-slate-500'
          )}>
            {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '—'} {trendValue}
          </span>
        )}
      </div>
      {subtitle && <span className="text-slate-600 text-[10px] font-medium leading-tight">{subtitle}</span>}
    </div>
  );
}
