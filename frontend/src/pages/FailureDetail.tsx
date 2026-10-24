
import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  Sparkles,
  Terminal,
  Lightbulb,
  ShieldCheck,
  FileCode,
  Download,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
} from 'lucide-react';

import { StatusBadge } from '../components/StatusBadge';
import { api } from '../lib/api';
import type { FailureDetail, Analysis } from '../types';

export const FailureDetailView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [failure, setFailure] = useState<FailureDetail | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadData = useCallback(async (failureId: string) => {
    const failureData = await api.getFailureDetail(failureId);
    const analyses = await api.getFailureAnalyses(failureId);

    setFailure(failureData);
    setAnalysis(analyses.length > 0 ? analyses[0] : null);

    return failureData;
  }, []);

  useEffect(() => {
    let active = true;

    const load = async () => {
      if (!id) {
        setError('No failure ID was provided.');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const failureData = await api.getFailureDetail(id);
        const analyses = await api.getFailureAnalyses(id);

        if (!active) return;

        setFailure(failureData);
        setAnalysis(analyses.length > 0 ? analyses[0] : null);
      } catch (err: unknown) {
        if (!active) return;
        setError(
          err instanceof Error
            ? err.message
            : 'Failed to load failure details.',
        );
      } finally {
        if (active) setLoading(false);
      }
    };

    void load();

    return () => {
      active = false;
    };
  }, [id]);

  const handleAnalyze = async () => {
    if (!id || analyzing) return;

    try {
      setAnalyzing(true);
      setError(null);
      setNotice(null);

      await api.analyzeFailure(id);

      const updatedFailure = await loadData(id);

      if (updatedFailure.latest_fix_proposal_id) {
        navigate(`/fixes/${updatedFailure.latest_fix_proposal_id}`);
        return;
      } else {
        setNotice(
          'Analysis completed, but no candidate patch was saved. ' +
            'Review the failure logs and source context. The backend only ' +
            'creates a proposal when its fix generator returns a patch.',
        );
      }
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : 'Analysis or proposal generation failed.',
      );
    } finally {
      setAnalyzing(false);
    }
  };

  const handleExportReport = () => {
    if (!failure) return;

    const report = {
      failure,
      analysis,
      exported_at: new Date().toISOString(),
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: 'application/json',
    });

    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');

    anchor.href = url;
    anchor.download = `deployguard_report_${failure.id}.json`;
    anchor.click();

    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="max-w-6xl space-y-6 animate-pulse">
        <div className="h-6 w-1/3 rounded bg-slate-800" />
        <div className="h-40 rounded-lg border border-border bg-card" />
        <div className="h-64 rounded-lg border border-border bg-card" />
      </div>
    );
  }

  if (!failure) {
    return (
      <div className="rounded-lg border border-border bg-card p-8 text-center">
        <AlertCircle className="mx-auto h-8 w-8 text-rose-400" />
        <p className="mt-3 text-sm text-slate-300">
          {error || 'Failure incident not found.'}
        </p>
        <Link
          to="/failures"
          className="mt-4 inline-block text-sm text-primary-light underline"
        >
          Return to failures
        </Link>
      </div>
    );
  }

  const evidenceList = analysis?.parsed_evidence || [];
  const alternativesList = analysis?.parsed_alternatives || [];
  const recommendationsList = analysis?.parsed_recommendations || [];

  return (
    <div className="max-w-6xl space-y-6">
      {/* Header and primary actions */}
      <div className="flex flex-col justify-between gap-4 border-b border-border pb-5 md:flex-row md:items-center">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-xl font-bold tracking-tight text-white">
              {failure.workflow_run?.workflow_name || 'Failed workflow'}
            </h2>
            <StatusBadge status={failure.status} type="status" />
          </div>

          <p className="mt-1 font-mono text-xs text-slate-400">
            Job:{' '}
            <span className="text-slate-200">
              {failure.failed_job_name || 'Unknown'}
            </span>
            {' · '}Branch:{' '}
            <span className="text-slate-200">
              {failure.workflow_run?.branch || 'Unknown'}
            </span>
            {' · '}Commit:{' '}
            <span className="text-slate-200">
              {failure.workflow_run?.commit_sha?.slice(0, 8) || 'Unknown'}
            </span>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleExportReport}
            className="inline-flex items-center gap-1.5 rounded border border-border bg-slate-900 px-3 py-2 text-xs text-slate-300 hover:bg-slate-800"
          >
            <Download className="h-3.5 w-3.5" />
            Export Report
          </button>

          <button
            type="button"
            onClick={handleAnalyze}
            disabled={analyzing}
            className="inline-flex items-center gap-1.5 rounded bg-primary px-3 py-2 text-xs font-medium text-white hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {analyzing ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Sparkles className="h-3.5 w-3.5" />
            )}
            {analyzing
              ? 'Analyzing...'
              : analysis
                ? 'Re-run AI Analysis'
                : 'Run AI Analysis'}
          </button>

          <button
            type="button"
            onClick={handleAnalyze}
            disabled={analyzing}
            className="inline-flex items-center gap-1.5 rounded bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <FileCode className="h-3.5 w-3.5" />
            {analyzing ? 'Generating...' : 'Generate Fix Proposal'}
          </button>

          {failure.latest_fix_proposal_id && (
            <Link
              to={`/fixes/${failure.latest_fix_proposal_id}`}
              className="inline-flex items-center gap-1.5 rounded border border-emerald-700 bg-emerald-950/60 px-3 py-2 text-xs font-medium text-emerald-300 hover:bg-emerald-900"
            >
              <FileCode className="h-3.5 w-3.5" />
              Review Fix Diff
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          )}
        </div>
      </div>

      {/* Errors */}
      {error && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded border border-rose-800 bg-rose-950/40 p-3 text-xs text-rose-300"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Analysis and proposal feedback */}
      {notice && (
        <div
          role="status"
          className="flex items-start gap-2 rounded border border-sky-800 bg-sky-950/30 p-3 text-xs text-sky-200"
        >
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p>{notice}</p>
            {failure.latest_fix_proposal_id && (
              <Link
                to={`/fixes/${failure.latest_fix_proposal_id}`}
                className="mt-2 inline-flex items-center gap-1 font-semibold text-emerald-300 underline"
              >
                Open Fix Proposal
                <ArrowRight className="h-3 w-3" />
              </Link>
            )}
          </div>
        </div>
      )}

      {/* Root-cause analysis */}
      {analysis ? (
        <section className="relative overflow-hidden rounded-lg border border-primary/30 bg-card p-6 shadow-md">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-base font-semibold text-white">
              Synthesized Root Cause
            </h3>

            <span className="rounded border border-border bg-slate-900 px-2 py-1 font-mono text-[10px] text-slate-300">
              Provider: {analysis.provider}
              {' · '}Model: {analysis.model || 'Deterministic Engine'}
            </span>
          </div>

          <div className="flex items-start gap-3">
            <div className="mt-1 rounded-lg border border-primary/40 bg-primary/20 p-2 text-primary-light">
              <Sparkles className="h-5 w-5" />
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-3">
                <h4 className="text-sm font-semibold text-white">
                  Analysis Result
                </h4>
                <span className="rounded border border-border bg-slate-900 px-2 py-0.5 font-mono text-xs text-emerald-400">
                  {Math.round(analysis.confidence * 100)}% Confidence
                </span>
              </div>

              <p className="mt-2 rounded border border-border bg-slate-950/60 p-3 font-mono text-xs leading-relaxed text-slate-200">
                {analysis.root_cause}
              </p>

              <p className="mt-2 text-[11px] text-slate-400">
                <strong className="text-slate-300">
                  Scoring Justification:{' '}
                </strong>
                {analysis.confidence_method || 'Not provided'}
              </p>
            </div>
          </div>

          {/* Supporting evidence */}
          {evidenceList.length > 0 && (
            <div className="mt-6 border-t border-border pt-5">
              <h4 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                Supporting Evidence &amp; Line References
              </h4>

              <div className="space-y-2">
                {evidenceList.map((ev, index) => (
                  <div
                    key={index}
                    className="flex flex-col justify-between gap-2 rounded border border-border bg-slate-950 p-3 text-xs md:flex-row md:items-start"
                  >
                    <div className="min-w-0">
                      <span className="font-mono text-[11px] font-medium text-primary-light">
                        [{ev.source}]
                      </span>
                      <pre className="mt-1 whitespace-pre-wrap font-mono text-[11px] text-slate-300">
                        {ev.snippet}
                      </pre>
                    </div>

                    <span className="shrink-0 text-[11px] italic text-slate-400">
                      {ev.relevance}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Alternative explanations */}
          {alternativesList.length > 0 && (
            <div className="mt-6 border-t border-border pt-5">
              <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                Alternative Explanations
              </h4>

              <div className="space-y-2">
                {alternativesList.map((item, index) => (
                  <div
                    key={index}
                    className="rounded border border-border bg-slate-950 p-3 text-xs text-slate-300"
                  >
                    {item.hypothesis || JSON.stringify(item)}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {recommendationsList.length > 0 && (
            <div className="mt-6 border-t border-border pt-5">
              <h4 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <Lightbulb className="h-4 w-4 text-amber-400" />
                Recommended Investigation Steps
              </h4>

              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {recommendationsList.map((rec, index) => (
                  <div
                    key={index}
                    className="rounded border border-border bg-slate-950 p-3 text-xs"
                  >
                    <p className="font-medium text-slate-200">
                      Step {rec.step}: {rec.action}
                    </p>

                    {rec.command && (
                      <code className="mt-2 block rounded bg-slate-900 p-1.5 font-mono text-[11px] text-indigo-300">
                        $ {rec.command}
                      </code>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      ) : (
        <section className="rounded-lg border border-dashed border-border bg-card p-8 text-center">
          <Sparkles className="mx-auto h-8 w-8 text-slate-500" />
          <h3 className="mt-2 text-sm font-semibold text-white">
            No Analysis Generated Yet
          </h3>
          <p className="mx-auto mt-1 max-w-sm text-xs text-slate-400">
            Run an analysis to classify the failure, inspect its logs, and
            attempt to generate a candidate fix proposal.
          </p>
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={analyzing}
            className="mt-4 inline-flex items-center gap-2 rounded bg-primary px-4 py-2 text-xs font-medium text-white hover:bg-primary-hover disabled:opacity-60"
          >
            <Sparkles className="h-4 w-4" />
            {analyzing ? 'Working...' : 'Generate Diagnosis & Fix Proposal'}
          </button>
        </section>
      )}

      {/* Sanitized execution log */}
      <section className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
        <div className="flex items-center justify-between border-b border-border bg-slate-900 px-4 py-3">
          <div className="flex items-center gap-2">
            <Terminal className="h-4 w-4 text-slate-400" />
            <h3 className="text-xs font-semibold text-white">
              Sanitized Execution Log Excerpt
            </h3>
          </div>
          <span className="font-mono text-[10px] text-slate-400">
            Tokens &amp; Secrets Redacted
          </span>
        </div>

        <div className="code-font max-h-96 overflow-x-auto bg-slate-950 p-4 text-xs leading-relaxed text-slate-300">
          <pre className="whitespace-pre-wrap">
            {failure.log_excerpt || 'No log excerpt available for this failure.'}
          </pre>
        </div>
      </section>
    </div>
  );
};

export default FailureDetailView;
