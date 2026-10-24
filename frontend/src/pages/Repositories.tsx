import React, { useEffect, useState } from 'react';
import {
  GitBranch,
  RefreshCw,
  Plus,
  Trash2,
  ExternalLink,
  ShieldAlert,
  CheckCircle,
} from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import { ConfirmationModal } from '../components/ConfirmationModal';
import { api } from '../lib/api';
import { Repository } from '../types';

export const Repositories: React.FC = () => {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Repository | null>(null);
  const [showConnectModal, setShowConnectModal] = useState<boolean>(false);
  const [newRepoName, setNewRepoName] = useState<string>('');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    fetchRepositories();
  }, []);

  const fetchRepositories = async () => {
    try {
      setLoading(true);
      const data = await api.getRepositories();
      setRepositories(data);
    } catch (err: any) {
      setMessage({ text: err.message || 'Failed to load repositories', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async (repoId: string) => {
    try {
      setSyncingId(repoId);
      const res = await api.syncRepository(repoId);
      setMessage({
        text: `GitHub sync completed: ${res.runs_imported} new workflow runs imported.`,
        type: 'success',
      });
      fetchRepositories();
    } catch (err: any) {
      setMessage({ text: err.message || 'Synchronization failed', type: 'error' });
    } finally {
      setSyncingId(null);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.deleteRepository(deleteTarget.id);
      setMessage({ text: `Repository ${deleteTarget.full_name} deleted.`, type: 'success' });
      setDeleteTarget(null);
      fetchRepositories();
    } catch (err: any) {
      setMessage({ text: err.message || 'Failed to delete repository', type: 'error' });
    }
  };

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRepoName.trim()) return;
    try {
      const workspaces = await api.getWorkspaces();
      if (!workspaces.length) throw new Error('No workspace available.');
      await api.connectRepository(workspaces[0].id, newRepoName.trim());
      setMessage({ text: `Repository ${newRepoName} connected successfully.`, type: 'success' });
      setShowConnectModal(false);
      setNewRepoName('');
      fetchRepositories();
    } catch (err: any) {
      setMessage({ text: err.message || 'Failed to connect repository', type: 'error' });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Monitored Repositories</h2>
          <p className="text-xs text-slate-400 mt-1">
            Connected GitHub repositories with automated CI/CD failure monitoring.
          </p>
        </div>
        <button
          onClick={() => setShowConnectModal(true)}
          className="inline-flex items-center justify-center space-x-1.5 px-4 py-2.5 bg-emerald-400 hover:bg-emerald-300 text-slate-950 text-sm font-semibold rounded-xl transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>Connect Repository</span>
        </button>
      </div>

      {/* Message notification */}
      {message && (
        <div
          className={`p-3 rounded-md text-xs flex items-center justify-between border ${
            message.type === 'success'
              ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800'
              : 'bg-rose-950/40 text-rose-300 border-rose-800'
          }`}
        >
          <span>{message.text}</span>
          <button onClick={() => setMessage(null)} className="text-slate-400 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {!loading && repositories.length === 0 && (
        <section className="relative overflow-hidden rounded-2xl border border-emerald-400/20 bg-gradient-to-br from-emerald-400/[0.09] via-card to-card p-7 md:p-10">
          <div className="absolute -right-12 -top-16 h-48 w-48 rounded-full bg-emerald-400/[0.07] blur-2xl" />
          <div className="relative max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1.5 text-xs font-medium text-emerald-200"><CheckCircle className="h-3.5 w-3.5" /> Live monitoring is ready</div>
            <h3 className="mt-5 text-2xl md:text-3xl font-semibold tracking-tight text-white">Connect your first repository</h3>
            <p className="mt-3 max-w-xl text-sm md:text-base leading-7 text-slate-300">Add a public GitHub repository to import its real Actions runs. DeployGuard will highlight failed jobs and analyze the logs it can access. No sample failures are added.</p>
            <button onClick={() => setShowConnectModal(true)} className="mt-6 inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300"><Plus className="h-4 w-4" /> Connect a GitHub repository</button>
            <p className="mt-3 text-xs text-slate-500">Paste a URL like https://github.com/owner/repository</p>
          </div>
        </section>
      )}

      {/* Repositories List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {repositories.map((repo) => (
          <div
            key={repo.id}
            className="bg-card border border-border rounded-lg p-5 hover:border-border-highlight transition-all shadow-sm"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 rounded bg-slate-900 border border-border text-slate-300">
                  <GitBranch className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white tracking-tight">{repo.full_name}</h3>
                  <p className="text-[11px] font-mono text-slate-400">Branch: {repo.default_branch}</p>
                </div>
              </div>
              <StatusBadge status={repo.connection_status} type="status" />
            </div>

            <div className="mt-5 grid grid-cols-2 gap-3 py-3 border-y border-border/80 text-xs font-mono">
              <div>
                <span className="text-slate-500 text-[10px] uppercase">Workflow Runs</span>
                <p className="text-sm font-semibold text-white mt-0.5">{repo.workflow_runs_count}</p>
              </div>
              <div>
                <span className="text-slate-500 text-[10px] uppercase">Logged Failures</span>
                <p className="text-sm font-semibold text-rose-400 mt-0.5">{repo.failure_count}</p>
              </div>
            </div>

            <div className="mt-4 flex items-center justify-between text-xs">
              <span className="text-[11px] text-slate-500 font-mono">
                Synced: {repo.last_synced_at ? new Date(repo.last_synced_at).toLocaleTimeString() : 'Never'}
              </span>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleSync(repo.id)}
                  disabled={syncingId === repo.id}
                  className="px-2.5 py-1 text-[11px] text-slate-300 hover:text-white bg-slate-900 border border-border hover:border-slate-700 rounded transition-colors flex items-center space-x-1"
                >
                  <RefreshCw className={`w-3 h-3 ${syncingId === repo.id ? 'animate-spin' : ''}`} />
                  <span>Sync</span>
                </button>
                <button
                  onClick={() => setDeleteTarget(repo)}
                  className="p-1 text-slate-500 hover:text-rose-400 transition-colors"
                  title="Remove repository"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Connect Repository Modal */}
      {showConnectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in">
          <div className="bg-card border border-border rounded-lg max-w-md w-full p-6 shadow-2xl">
            <h3 className="text-sm font-semibold text-white">Connect GitHub Repository</h3>
            <p className="mt-1 text-xs text-slate-400">
              Provide the GitHub repository path (e.g., <code className="font-mono text-primary-light">org/repo</code>).
            </p>
            <form onSubmit={handleConnect} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1">Full Name</label>
                <input
                  type="text"
                  placeholder="https://github.com/owner/repository"
                  value={newRepoName}
                  onChange={(e) => setNewRepoName(e.target.value)}
                  className="w-full bg-slate-950 border border-border rounded px-3 py-2 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-primary"
                  required
                />
              </div>
              <div className="flex items-center justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowConnectModal(false)}
                  className="px-3 py-1.5 text-xs text-slate-400 hover:text-white rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-primary hover:bg-primary-hover text-white text-xs font-medium rounded"
                >
                  Connect & Sync
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <ConfirmationModal
        isOpen={!!deleteTarget}
        title="Remove Repository"
        message={`Are you sure you want to disconnect ${deleteTarget?.full_name}? All associated failure analyses and logs will be removed.`}
        confirmLabel="Remove Repository"
        isDestructive={true}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
};
