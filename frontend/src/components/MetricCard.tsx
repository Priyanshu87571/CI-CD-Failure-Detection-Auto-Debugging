import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: string;
  isPositive?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  isPositive,
}) => {
  return (
    <div className="bg-card border border-border rounded-lg p-5 hover:border-border-highlight transition-colors shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">{title}</p>
        <div className="p-2 rounded-md bg-slate-900/60 border border-border text-slate-300">
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="mt-3 flex items-baseline justify-between">
        <p className="text-2xl font-semibold text-white tracking-tight">{value}</p>
        {trend && (
          <span
            className={`text-xs font-mono font-medium px-1.5 py-0.5 rounded ${
              isPositive
                ? 'text-emerald-400 bg-emerald-950/40 border border-emerald-900/50'
                : 'text-rose-400 bg-rose-950/40 border border-rose-900/50'
            }`}
          >
            {trend}
          </span>
        )}
      </div>
      {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
    </div>
  );
};
