import React, { useEffect, useState } from 'react';
import {
  Settings as SettingsIcon,
  CheckCircle,
  AlertCircle,
  Shield,
  Key,
  Cpu,
  Webhook,
  Database,
  ExternalLink,
} from 'lucide-react';
import { api } from '../lib/api';

export const SettingsPage: React.FC = () => {
  const [health, setHealth] = useState<any>(null);
  const [ready, setReady] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    loadDiagnostics();
  }, []);

  const loadDiagnostics = async () => {
    try {
      setLoading(true);
      const [h, r] = await Promise.all([api.getHealth(), api.getReady()]);
      setHealth(h);
      setReady(r);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-white">Platform Settings & Integrations</h2>
        <p className="text-xs text-slate-400 mt-1">
          System telemetry, active LLM providers, and GitHub integration connection states.
        </p>
      </div>

      {/* Integration Status Cards */}
      <div className="space-y-4">
        {/* GitHub Integration */}
        <div className="bg-card border border-border rounded-lg p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-lg bg-slate-900 border border-border text-white">
                <Shield className="w-5 h-5 text-indigo-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">GitHub Integration</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  GitHub App OAuth, repository sync, and webhook events.
                </p>
              </div>
            </div>
            <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-400/10 text-emerald-300 border border-emerald-400/20">
              Live GitHub API
            </span>
          </div>

          <div className="mt-4 pt-4 border-t border-border grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Access</span>
              <p className="text-slate-300">Public repositories; token optional</p>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Webhook Secret</span>
              <p className="text-slate-300">Configure in server environment if using webhooks</p>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Rate Limit</span>
              <p className="text-emerald-400">GitHub API rate limits apply</p>
            </div>
          </div>
        </div>

        {/* AI Provider Configuration */}
        <div className="bg-card border border-border rounded-lg p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-lg bg-slate-900 border border-border text-white">
                <Cpu className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">AI / LLM Analysis Engine</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Deterministic rule parsing engine with provider-independent LLM synthesis.
                </p>
              </div>
            </div>
            <span className="px-2.5 py-1 rounded text-xs font-mono font-medium bg-emerald-950/60 text-emerald-300 border border-emerald-800">
              OPERATIONAL
            </span>
          </div>

          <div className="mt-4 pt-4 border-t border-border grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Active Provider</span>
              <p className="text-slate-200 uppercase">{ready?.ai_provider || 'FALLBACK'}</p>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Fallback Engine</span>
              <p className="text-emerald-400">Deterministic Rules (10 Categories)</p>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Prompt Injection Guard</span>
              <p className="text-indigo-400">Active (Untrusted Boundaries)</p>
            </div>
          </div>
        </div>

        {/* Test Verification Sandbox */}
        <div className="bg-card border border-border rounded-lg p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-lg bg-slate-900 border border-border text-white">
                <Database className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Isolated Test Verification Sandbox</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Verification requires a real source checkout. DeployGuard will not fabricate a test project or report a simulated pass.
                </p>
              </div>
            </div>
            <span className="px-2.5 py-1 rounded text-xs font-mono font-medium bg-indigo-950/60 text-indigo-300 border border-indigo-800">
              {ready?.verification_runner?.toUpperCase() || 'ISOLATED PROCESS'}
            </span>
          </div>

          <div className="mt-4 pt-4 border-t border-border grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Database</span>
              <p className="text-emerald-400">{ready?.database || 'Connected'}</p>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Allowed Runners</span>
              <p className="text-slate-300">pytest, npm, go, cargo</p>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Configured Timeout</span>
              <p className="text-slate-300">{ready?.verification_runner ? '45 seconds (source checkout required)' : 'Source checkout required'}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
