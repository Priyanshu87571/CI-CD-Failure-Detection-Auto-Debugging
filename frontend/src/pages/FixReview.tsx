
import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  FileCode,
  Play,
  ShieldCheck,
  ArrowLeft,
  Terminal,
  AlertCircle,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';

import { CodeDiffView } from '../components/CodeDiffView';
import { StatusBadge } from '../components/StatusBadge';
import { ConfirmationModal } from '../components/ConfirmationModal';
import { api } from '../lib/api';
import type { FixProposal, VerificationRun } from '../types';

export const FixReview: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [proposal, setProposal] = useState<FixProposal | null>(null);
  const [verification, setVerification] = useState<VerificationRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [testCommand, setTestCommand] = useState('pytest');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadProposal = useCallback(async (proposalId: string) => {
    const data = await api.getProposal(proposalId);
    setProposal(data);
    return data;
  }, []);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        setNotice(null);

        if (!id) {
          const proposals = await api.getProposals();
          if (!active) return;
          if (proposals.length > 0) {
            navigate(`/fixes/${proposals[0].id}`, { replace: true });
            return;
          }
          setProposal(null);
          setError('No saved fix proposals yet. Open a failed workflow and generate a candidate proposal first.');
          return;
        }

        const data = await api.getProposal(id);

        if (active) {
          setProposal(data);
          const files = data.affected_files || [];
          setTestCommand(files.some((file) => /\.(tsx?|jsx?|mjs|cjs)$/.test(file)) ? 'npm run build' : 'pytest');
        }
      } catch (err: unknown) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : 'Failed to load the fix proposal.',
          );
          setProposal(null);
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    void load();

    return () => {
      active = false;
    };
  }, [id, navigate]);

  const handleApprove = async () => {
    if (!proposal || approving) return;

    try {
      setApproving(true);
      setError(null);
      setNotice(null);

      const updated = await api.approveProposal(
        proposal.id,
        true,
        'Approved by reviewer for sandbox testing.',
      );

      setProposal(updated);
      setShowApprovalModal(false);
      setNotice('Proposal approval was recorded.');
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : 'Proposal approval failed.',
      );
    } finally {
      setApproving(false);
    }
  };

  const handleRunVerification = async () => {
    if (!proposal || verifying) return;

    const command = testCommand.trim();

    if (!command) {
      setError('Enter a supported test command.');
      return;
    }

    try {
      setVerifying(true);
      setError(null);
      setNotice(null);

      const result = await api.verifyProposal(proposal.id, command);
      setVerification(result);

      if (result.status === 'passed') {
        setNotice('Verification passed: the baseline failed and the candidate tests passed.');
      } else if (result.status === 'inconclusive') {
        setNotice('Inconclusive: candidate tests passed, but the baseline also passed. The original failure was not reproduced, so the fix was not marked verified.');
      } else {
        setError(
          `Verification status: ${result.status}. Review the recorded results below.`,
        );
      }
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : 'Verification could not be completed.',
      );
    } finally {
      setVerifying(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl space-y-6 animate-pulse">
        <div className="h-6 w-1/3 rounded bg-slate-800" />
        <div className="h-64 rounded-lg border border-border bg-card" />
      </div>
    );
  }

  if (!proposal) {
    return (
      <div className="max-w-3xl space-y-4">
        <Link
          to="/failures"
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Failures
        </Link>

        <section className="rounded-lg border border-border bg-card p-8 text-center">
          <FileCode className="mx-auto h-10 w-10 text-slate-500" />

          <h2 className="mt-4 text-lg font-semibold text-white">
            No Fix Proposal Available
          </h2>

          <p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed text-slate-400">
            This page displays saved proposals only. Return to the failed
            workflow, open its failure details, and select Generate Fix
            Proposal. If analysis cannot produce a safe patch, review the
            failure logs and source context.
          </p>

          {error && (
            <div
              role="alert"
              className="mt-4 rounded border border-rose-800 bg-rose-950/40 p-3 text-left text-xs text-rose-300"
            >
              {error}
            </div>
          )}

          <Link
            to="/failures"
            className="mt-5 inline-flex items-center gap-2 rounded bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Open Failures
            <ArrowLeft className="h-4 w-4 rotate-180" />
          </Link>
        </section>
      </div>
    );
  }

  return (
    <div className="max-w-6xl space-y-6">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 border-b border-border pb-5 md:flex-row md:items-center">
        <div className="flex items-start gap-3">
          <Link
            to="/failures"
            aria-label="Back to failures"
            className="mt-1 text-slate-400 transition-colors hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>

          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-xl font-bold tracking-tight text-white">
                Candidate Fix Proposal
              </h2>
              <StatusBadge status={proposal.status} type="status" />
            </div>

            <p className="mt-1 text-xs text-slate-400">
              Target files:{' '}
              <span className="font-mono text-slate-300">
                {proposal.affected_files?.join(', ') || 'Not specified'}
              </span>
            </p>

            <p className="mt-1 break-all font-mono text-[10px] text-slate-500">
              Proposal ID: {proposal.id}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {proposal.status !== 'approved' &&
            proposal.status !== 'applied' && (
              <button
                type="button"
                onClick={() => setShowApprovalModal(true)}
                className="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-xs font-medium text-white shadow-sm transition-colors hover:bg-indigo-500"
              >
                <ShieldCheck className="h-4 w-4" />
                Approve Candidate Patch
              </button>
            )}

          {proposal.status === 'approved' && (
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="text"
                value={testCommand}
                onChange={(event) => setTestCommand(event.target.value)}
                placeholder="Supported test command"
                aria-label="Test command"
                className="w-48 rounded border border-border bg-slate-950 px-3 py-2 font-mono text-xs text-white focus:border-primary focus:outline-none"
              />

              <button
                type="button"
                onClick={handleRunVerification}
                disabled={verifying}
                className="inline-flex items-center gap-2 rounded-md bg-emerald-600 px-4 py-2 text-xs font-medium text-white shadow-sm transition-colors hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {verifying ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                {verifying ? 'Verifying...' : 'Run Verification'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Status messages */}
      {error && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-md border border-rose-800 bg-rose-950/40 p-3 text-xs text-rose-300"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {notice && (
        <div
          role="status"
          className="rounded-md border border-emerald-800 bg-emerald-950/40 p-3 text-xs text-emerald-300"
        >
          {notice}
        </div>
      )}

      {/* Safety notice */}
      <div className="flex items-start gap-3 rounded-lg border border-border bg-slate-900 p-4 text-xs text-slate-300">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />

        <div>
          <p className="font-semibold text-white">
            Review before verification
          </p>
          <p className="mt-1 leading-relaxed text-slate-400">
            Review the candidate diff before approving it. Verification is
            only meaningful when the backend actually applies the candidate
            patch in an isolated environment and records the test outcome.
          </p>
        </div>
      </div>

      {/* Candidate diff */}
      <CodeDiffView
        patchContent={proposal.patch_content}
        explanation={proposal.explanation}
      />

      {/* Verification results */}
      {verification && (
        <section className="space-y-4 rounded-lg border border-border bg-card p-6 shadow-md">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">
                Verification Results
              </h3>
              <p className="mt-1 text-[11px] text-slate-400">
                Recorded baseline and candidate outcomes
              </p>
            </div>

            <StatusBadge status={verification.status} type="verification" />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded border border-border bg-slate-950 p-4">
              <span className="font-mono text-[10px] uppercase text-slate-500">
                Baseline
              </span>
              <div className="mt-2">
                <StatusBadge
                  status={verification.baseline_result || 'unknown'}
                  type="verification"
                />
              </div>
            </div>

            <div className="rounded border border-border bg-slate-950 p-4">
              <span className="font-mono text-[10px] uppercase text-slate-500">
                Candidate
              </span>
              <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                <StatusBadge
                  status={verification.candidate_result || 'unknown'}
                  type="verification"
                />
                <span className="font-mono text-[11px] text-slate-400">
                  Duration: {verification.duration_ms} ms
                </span>
              </div>
            </div>
          </div>

          <div>
            <div className="flex items-center gap-2 border-b border-border bg-slate-900 px-3 py-2 font-mono text-xs text-slate-300">
              <Terminal className="h-3.5 w-3.5 text-primary-light" />
              Test Execution Output
            </div>

            <pre className="max-h-64 overflow-x-auto whitespace-pre-wrap rounded-b border border-border bg-slate-950 p-4 font-mono text-xs text-slate-300">
              {verification.parsed_test_summary?.candidate?.output_tail ||
                verification.failure_reason ||
                'No test output was recorded.'}
            </pre>
          </div>
        </section>
      )}

      {/* Approval confirmation */}
      <ConfirmationModal
        isOpen={showApprovalModal}
        title="Approve Candidate Patch for Testing"
        message="Approve this candidate patch for the verification workflow? Approval does not modify a production branch. Continue only if the backend verifies the patch in a supported isolated environment."
        confirmLabel="Approve Candidate Fix"
        onConfirm={handleApprove}
        onCancel={() => setShowApprovalModal(false)}
        isLoading={approving}
      />
    </div>
  );
};

export default FixReview;