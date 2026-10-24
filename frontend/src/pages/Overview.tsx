import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  GitBranch,
  PlayCircle,
  AlertOctagon,
  Percent,
  Sparkles,
  CheckCircle2,
  ArrowRight,
  TrendingUp,
} from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, AreaChart, Area } from 'recharts';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../lib/api';
import { DashboardSummary, AnalyticsTrend } from '../types';

export const Overview: React.FC = () => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [trends, setTrends] = useState<AnalyticsTrend | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [sumData, trendData] = await Promise.all([
        api.getDashboardSummary(),
        api.getAnalyticsTrends(),
      ]);
      setSummary(sumData);
      setTrends(trendData);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard metrics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-slate-800/60 rounded w-1/4"></div>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-28 bg-card border border-border rounded-lg"></div>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-72 bg-card border border-border rounded-lg"></div>
          <div className="h-72 bg-card border border-border rounded-lg"></div>
        </div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="bg-rose-950/20 border border-rose-800/60 rounded-lg p-6 text-rose-300">
        <h3 className="text-sm font-semibold">Error Loading Dashboard</h3>
        <p className="mt-1 text-xs text-rose-400">{error || 'Unable to retrieve summary metrics.'}</p>
        <button
          onClick={fetchData}
          className="mt-4 px-3 py-1.5 bg-rose-900/60 hover:bg-rose-800 text-xs text-white rounded transition-colors"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl md:text-3xl font-semibold tracking-tight text-white">System overview</h2>
        <p className="text-sm text-slate-400 mt-2">
          Real-time CI/CD telemetry, root cause classifications, and automated verification status.
        </p>
      </div>

      {summary.monitored_repositories_count === 0 && (
        <section className="relative overflow-hidden rounded-2xl border border-emerald-400/20 bg-gradient-to-br from-emerald-400/[0.09] via-card to-card p-6 md:p-8">
          <div className="absolute -right-12 -top-16 h-48 w-48 rounded-full bg-emerald-400/[0.07] blur-2xl" />
          <div className="relative max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">Start here</p>
            <h3 className="mt-3 text-2xl md:text-3xl font-semibold tracking-tight text-white">Your pipelines, without the guesswork.</h3>
            <p className="mt-3 text-sm md:text-base leading-7 text-slate-300">Connect a public GitHub repository to import real workflow runs. Your dashboard will populate when GitHub data is synced—this workspace does not use sample metrics.</p>
            <Link to="/repositories" className="mt-5 inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300">Connect a repository <ArrowRight className="h-4 w-4" /></Link>
          </div>
        </section>
      )}

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <MetricCard
          title="Monitored Repos"
          value={summary.monitored_repositories_count}
          subtitle="Active GitHub projects"
          icon={GitBranch}
        />
        <MetricCard
          title="Total Runs"
          value={summary.total_workflow_runs_count}
          subtitle="CI workflow runs"
          icon={PlayCircle}
        />
        <MetricCard
          title="Failed Runs"
          value={summary.failed_workflow_runs_count}
          subtitle="Unsuccessful runs"
          icon={AlertOctagon}
          trend={summary.failed_workflow_runs_count > 0 ? 'Active' : 'Clear'}
          isPositive={summary.failed_workflow_runs_count === 0}
        />
        <MetricCard
          title="Failure Rate"
          value={`${summary.failure_rate_percent}%`}
          subtitle="Observed failure %"
          icon={Percent}
        />
        <MetricCard
          title="Analyses Completed"
          value={summary.analyses_completed_count}
          subtitle="Deterministic & AI RCA"
          icon={Sparkles}
        />
        <MetricCard
          title="Fix Pass Rate"
          value={`${summary.fix_verification_pass_rate_percent}%`}
          subtitle="Verified test fixes"
          icon={CheckCircle2}
          isPositive={summary.fix_verification_pass_rate_percent >= 50}
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Failure Trend Chart */}
        <div className="bg-card border border-border rounded-lg p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">CI/CD Failure Frequency</h3>
              <p className="text-[11px] text-slate-400">Daily failed workflows over the past 7 days</p>
            </div>
            <TrendingUp className="w-4 h-4 text-primary-light" />
          </div>
          <div className="h-60 w-full">
            {trends?.daily_trends && trends.daily_trends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trends.daily_trends}>
                  <defs>
                    <linearGradient id="colorFailures" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={11} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#101726', borderColor: '#1f2a40', fontSize: '12px' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="failed_runs"
                    stroke="#f43f5e"
                    fillOpacity={1}
                    fill="url(#colorFailures)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-xs text-slate-500">
                No trend telemetry available yet.
              </div>
            )}
          </div>
        </div>

        {/* Top Failure Categories Chart */}
        <div className="bg-card border border-border rounded-lg p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">Failure Category Distribution</h3>
              <p className="text-[11px] text-slate-400">Deterministic rule classification breakdowns</p>
            </div>
            <AlertOctagon className="w-4 h-4 text-purple-400" />
          </div>
          <div className="h-60 w-full">
            {summary.top_failure_categories && summary.top_failure_categories.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={summary.top_failure_categories}>
                  <XAxis
                    dataKey="category"
                    stroke="#64748b"
                    fontSize={10}
                    tickLine={false}
                    tickFormatter={(val) => val.split('_')[0]}
                  />
                  <YAxis stroke="#64748b" fontSize={11} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#101726', borderColor: '#1f2a40', fontSize: '12px' }}
                  />
                  <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-xs text-slate-500">
                No failures logged.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Failures Table */}
      <div className="bg-card border border-border rounded-lg overflow-hidden shadow-sm">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white">Recent CI/CD Failures</h3>
            <p className="text-[11px] text-slate-400">Latest pipeline incidents requiring root cause diagnosis</p>
          </div>
          <Link
            to="/failures"
            className="text-xs font-medium text-primary-light hover:text-white flex items-center space-x-1 transition-colors"
          >
            <span>View all failures</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-border bg-slate-900/50 text-slate-400 uppercase font-mono text-[10px]">
                <th className="py-3 px-5">Workflow</th>
                <th className="py-3 px-4">Failed Job</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Branch / Commit</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {summary.recent_failures.length > 0 ? (
                summary.recent_failures.map((f) => (
                  <tr key={f.id} className="hover:bg-card-hover transition-colors">
                    <td className="py-3.5 px-5 font-medium text-white">{f.workflow_name}</td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">{f.failed_job}</td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={f.category} type="category" />
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-400">
                      {f.branch} ({f.commit_sha})
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={f.status} type="status" />
                    </td>
                    <td className="py-3.5 px-5 text-right">
                      <Link
                        to={`/failures/${f.id}`}
                        className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs transition-colors"
                      >
                        <span>Diagnose</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No active failures found. Monitored pipelines are green!
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
