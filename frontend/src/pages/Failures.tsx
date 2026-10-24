import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Filter, AlertOctagon, ArrowRight, RotateCcw } from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../lib/api';
import { Failure } from '../types';

export const Failures: React.FC = () => {
  const [failures, setFailures] = useState<Failure[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');

  useEffect(() => {
    fetchFailures();
  }, [selectedCategory, selectedStatus]);

  const fetchFailures = async () => {
    try {
      setLoading(true);
      const data = await api.getFailures({
        category: selectedCategory || undefined,
        status: selectedStatus || undefined,
        search: searchTerm || undefined,
      });
      setFailures(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchFailures();
  };

  const categories = [
    'dependency_installation',
    'compilation_syntax',
    'unit_test',
    'linting_formatting',
    'missing_env_var',
    'configuration_error',
    'permission_error',
    'network_external_service',
    'resource_timeout',
    'unknown',
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-white">CI/CD Failure Explorer</h2>
        <p className="text-xs text-slate-400 mt-1">
          Inspect, classify, and diagnose captured workflow execution failures.
        </p>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-card border border-border rounded-lg p-4 flex flex-col md:flex-row items-center justify-between gap-4 shadow-sm">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-80">
          <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
          <input
            type="text"
            placeholder="Search by summary, workflow, branch..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-950 border border-border rounded-md pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary"
          />
        </form>

        <div className="flex items-center space-x-3 w-full md:w-auto">
          {/* Category Filter */}
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="bg-slate-950 border border-border rounded-md px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-primary font-mono"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c.replace(/_/g, ' ').toUpperCase()}
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="bg-slate-950 border border-border rounded-md px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-primary font-mono"
          >
            <option value="">All Statuses</option>
            <option value="open">OPEN</option>
            <option value="investigating">INVESTIGATING</option>
            <option value="fix_proposed">FIX PROPOSED</option>
            <option value="verified">VERIFIED</option>
            <option value="resolved">RESOLVED</option>
          </select>

          {(selectedCategory || selectedStatus || searchTerm) && (
            <button
              onClick={() => {
                setSelectedCategory('');
                setSelectedStatus('');
                setSearchTerm('');
              }}
              className="p-2 text-slate-400 hover:text-white rounded bg-slate-900 border border-border"
              title="Reset Filters"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Failures Table */}
      <div className="bg-card border border-border rounded-lg overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-border bg-slate-900/60 text-slate-400 uppercase font-mono text-[10px]">
                <th className="py-3 px-5">Workflow & Job</th>
                <th className="py-3 px-4">Failure Classification</th>
                <th className="py-3 px-4">Branch / Commit</th>
                <th className="py-3 px-4">Summary</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Occurrences</th>
                <th className="py-3 px-5 text-right">Diagnosis</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    <span className="inline-block w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin mr-2" />
                    Querying incident telemetry...
                  </td>
                </tr>
              ) : failures.length > 0 ? (
                failures.map((f) => (
                  <tr key={f.id} className="hover:bg-card-hover transition-colors">
                    <td className="py-3.5 px-5">
                      <div className="font-semibold text-white">
                        {f.workflow_run?.workflow_name || 'Workflow Run'}
                      </div>
                      <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                        {f.failed_job_name}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={f.category} type="category" />
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      <div>{f.workflow_run?.branch || 'main'}</div>
                      <div className="text-[10px] text-slate-500">
                        {f.workflow_run?.commit_sha.slice(0, 8)}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-slate-300 max-w-xs truncate" title={f.summary}>
                      {f.summary}
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={f.status} type="status" />
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-400">
                      {f.occurrence_count}x
                    </td>
                    <td className="py-3.5 px-5 text-right">
                      <Link
                        to={`/failures/${f.id}`}
                        className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded bg-primary/20 hover:bg-primary/30 text-primary-light border border-primary/40 text-xs font-medium transition-colors"
                      >
                        <span>Investigate</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    No matching failure incidents found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
