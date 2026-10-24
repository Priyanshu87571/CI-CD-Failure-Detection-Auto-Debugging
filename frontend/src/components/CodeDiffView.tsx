import React from 'react';
import { FileCode, Plus, Minus } from 'lucide-react';

interface CodeDiffViewProps {
  patchContent: string;
  explanation?: string;
}

export const CodeDiffView: React.FC<CodeDiffViewProps> = ({ patchContent, explanation }) => {
  if (!patchContent || !patchContent.trim()) {
    return (
      <div className="bg-slate-900 border border-border rounded-lg p-6 text-center text-slate-500 text-sm">
        No diff available for this proposal.
      </div>
    );
  }

  const lines = patchContent.split('\n');

  return (
    <div className="border border-border rounded-lg overflow-hidden bg-slate-950 shadow-inner">
      <div className="bg-slate-900/90 border-b border-border px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <FileCode className="w-4 h-4 text-primary-light" />
          <span className="text-xs font-mono font-medium text-slate-300">Unified Patch Diff</span>
        </div>
        <span className="text-xs font-mono text-slate-500">Read-Only Candidate Patch</span>
      </div>

      {explanation && (
        <div className="bg-indigo-950/20 border-b border-indigo-900/30 px-4 py-3 text-xs text-indigo-200">
          <strong className="text-indigo-400">Diagnosis Rationale: </strong>
          {explanation}
        </div>
      )}

      <div className="overflow-x-auto p-2 code-font text-xs leading-relaxed max-h-[500px]">
        <table className="w-full border-collapse">
          <tbody>
            {lines.map((line, idx) => {
              let rowClass = 'text-slate-400';
              let icon = null;

              if (line.startsWith('+++') || line.startsWith('---')) {
                rowClass = 'text-slate-300 font-semibold bg-slate-900/70';
              } else if (line.startsWith('@@')) {
                rowClass = 'text-indigo-400 bg-indigo-950/30 font-medium';
              } else if (line.startsWith('+')) {
                rowClass = 'bg-emerald-950/40 text-emerald-300 border-l-2 border-emerald-500';
                icon = <Plus className="w-3 h-3 text-emerald-400 inline mr-1" />;
              } else if (line.startsWith('-')) {
                rowClass = 'bg-rose-950/40 text-rose-300 border-l-2 border-rose-500';
                icon = <Minus className="w-3 h-3 text-rose-400 inline mr-1" />;
              }

              return (
                <tr key={idx} className={`hover:bg-slate-900/50 ${rowClass}`}>
                  <td className="w-12 select-none text-right pr-4 text-slate-600 font-mono text-[11px]">
                    {idx + 1}
                  </td>
                  <td className="py-0.5 px-2 font-mono whitespace-pre">
                    {icon}
                    {line}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
