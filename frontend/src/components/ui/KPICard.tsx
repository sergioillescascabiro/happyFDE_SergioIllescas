import { clsx } from 'clsx';
import { LucideIcon } from 'lucide-react';

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  icon?: LucideIcon;
  valueClassName?: string;
}

export function KPICard({ title, value, subtitle, trend, trendValue, icon: Icon, valueClassName }: KPICardProps) {
  return (
    <div className="bg-[#111111] border border-[#2a2a2a] rounded-lg p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-[#888888] text-xs uppercase tracking-wider">{title}</span>
        {Icon && <Icon className="w-4 h-4 text-[#555555]" />}
      </div>
      <div className="flex items-end justify-between gap-2">
        <span className={clsx('text-2xl font-bold font-mono-data', valueClassName ?? 'text-white')}>
          {value}
        </span>
        {trend && trendValue && (
          <span className={clsx(
            'text-xs font-mono-data mb-0.5',
            trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : 'text-[#888]'
          )}>
            {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '—'} {trendValue}
          </span>
        )}
      </div>
      {subtitle && <span className="text-[#555555] text-xs">{subtitle}</span>}
    </div>
  );
}
