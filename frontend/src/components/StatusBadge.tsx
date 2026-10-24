import React from 'react';

interface StatusBadgeProps {
  status: string;
  type?: 'category' | 'status' | 'verification';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type = 'status' }) => {
  const normalized = status.toLowerCase().replace(/\s+/g, '_');

  let colorClasses = 'bg-slate-800 text-slate-300 border-slate-700';

  if (type === 'verification') {
    switch (normalized) {
      case 'passed':
        colorClasses = 'bg-emerald-950/60 text-emerald-400 border-emerald-800/80';
        break;
      case 'failed':
        colorClasses = 'bg-rose-950/60 text-rose-400 border-rose-800/80';
        break;
      case 'running':
        colorClasses = 'bg-indigo-950/60 text-indigo-400 border-indigo-800/80 animate-pulse';
        break;
      case 'timed_out':
        colorClasses = 'bg-amber-950/60 text-amber-400 border-amber-800/80';
        break;
      case 'unavailable':
        colorClasses = 'bg-slate-800/80 text-slate-400 border-slate-700';
        break;
      case 'inconclusive':
        colorClasses = 'bg-amber-950/60 text-amber-300 border-amber-800/80';
        break;
      default:
        colorClasses = 'bg-slate-900 text-slate-400 border-slate-800';
    }
  } else if (type === 'category') {
    switch (normalized) {
      case 'dependency_installation':
        colorClasses = 'bg-purple-950/60 text-purple-300 border-purple-800/80';
        break;
      case 'compilation_syntax':
        colorClasses = 'bg-orange-950/60 text-orange-300 border-orange-800/80';
        break;
      case 'unit_test':
        colorClasses = 'bg-rose-950/60 text-rose-300 border-rose-800/80';
        break;
      case 'linting_formatting':
        colorClasses = 'bg-blue-950/60 text-blue-300 border-blue-800/80';
        break;
      case 'missing_env_var':
        colorClasses = 'bg-amber-950/60 text-amber-300 border-amber-800/80';
        break;
      case 'configuration_error':
        colorClasses = 'bg-cyan-950/60 text-cyan-300 border-cyan-800/80';
        break;
      case 'permission_error':
        colorClasses = 'bg-red-950/60 text-red-300 border-red-800/80';
        break;
      case 'network_external_service':
        colorClasses = 'bg-teal-950/60 text-teal-300 border-teal-800/80';
        break;
      case 'resource_timeout':
        colorClasses = 'bg-yellow-950/60 text-yellow-300 border-yellow-800/80';
        break;
      default:
        colorClasses = 'bg-slate-800 text-slate-300 border-slate-700';
    }
  } else {
    // General status
    switch (normalized) {
      case 'verified':
      case 'passed':
      case 'success':
      case 'connected':
        colorClasses = 'bg-emerald-950/60 text-emerald-400 border-emerald-800/80';
        break;
      case 'open':
      case 'failed':
      case 'failure':
        colorClasses = 'bg-rose-950/60 text-rose-400 border-rose-800/80';
        break;
      case 'investigating':
      case 'in_progress':
        colorClasses = 'bg-amber-950/60 text-amber-300 border-amber-800/80';
        break;
      case 'fix_proposed':
      case 'approved':
        colorClasses = 'bg-indigo-950/60 text-indigo-300 border-indigo-800/80';
        break;
      default:
        colorClasses = 'bg-slate-800 text-slate-300 border-slate-700';
    }
  }

  const formatText = (text: string) => {
    return text.replace(/_/g, ' ').toUpperCase();
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium border ${colorClasses}`}
    >
      {formatText(status)}
    </span>
  );
};
