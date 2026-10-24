
import json
import logging
import re
import difflib
import io
import zipfile
from typing import List, Optional

import httpx

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models.analysis import Analysis
from backend.app.models.failure import Failure, FailureStatus
from backend.app.models.fix import FixProposal
from backend.app.models.repository import Repository
from backend.app.models.user import User
from backend.app.models.workflow import LogArtifact, WorkflowRun
from backend.app.models.workspace import WorkspaceMembership
from backend.app.core.config import settings
from backend.app.schemas.analysis import AnalysisResponse
from backend.app.schemas.failure import FailureDetailResponse, FailureResponse
from backend.app.schemas.workflow import WorkflowRunResponse
from backend.app.services.ai_service import AIService
from backend.app.services.failure_classifier import FailureClassifierService
from backend.app.services.fix_generator import FixGeneratorService
from backend.app.services.log_parser import LogParserService


async def _build_unused_variable_patch(repository: Repository, run: WorkflowRun, log: str):
    """Create a conservative ESLint unused-variable patch from source at the failed commit."""
    match = re.search(r"""['"]([A-Za-z_$][\w$]*)['"]\s+is assigned a value but never used""", log, re.I)
    if not match or not run.commit_sha:
        return None
    identifier = match.group(1)
    owner_repo = repository.full_name.strip("/")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "DeployGuard-CI-Observability",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = getattr(settings, "GITHUB_TOKEN", "") or ""
    if token.strip():
        headers["Authorization"] = f"Bearer {token.strip()}"
    async with httpx.AsyncClient(timeout=20.0, headers=headers, follow_redirects=True) as client:
        tree_response = await client.get(
            f"https://api.github.com/repos/{owner_repo}/git/trees/{run.commit_sha}",
            params={"recursive": "1"},
        )
        if tree_response.status_code != 200:
            return None
        tree = tree_response.json().get("tree", [])
        candidates = [
            item["path"] for item in tree
            if item.get("type") == "blob"
            and item.get("path", "").lower().endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"))
            and not any(part in item["path"].split("/") for part in ("node_modules", "dist", "build", ".git"))
        ]
        # Bound API work; the identifier must occur only in a single candidate file.
        for file_path in candidates[:150]:
            response = await client.get(
                f"https://raw.githubusercontent.com/{owner_repo}/{run.commit_sha}/{file_path}"
            )
            if response.status_code != 200:
                continue
            original = response.text
            if not re.search(rf"\b{re.escape(identifier)}\b", original):
                continue
            # Only remove a single-line const/let/var declaration when this is the
            # identifier's sole occurrence in the file. Do not guess at usages.
            occurrences = list(re.finditer(rf"\b{re.escape(identifier)}\b", original))
            if len(occurrences) != 1:
                continue
            lines = original.splitlines(keepends=True)
            line_index = next((i for i, line in enumerate(lines) if re.search(rf"\b{re.escape(identifier)}\b", line)), None)
            if line_index is None:
                continue
            line = lines[line_index]
            if not re.match(rf"^\s*(?:const|let|var)\s+{re.escape(identifier)}\s*=", line):
                continue
            updated = lines[:line_index] + lines[line_index + 1:]
            diff = list(difflib.unified_diff(
                original.splitlines(keepends=True),
                updated,
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
                n=3,
            ))
            if not diff:
                continue

            patch = "".join(diff)
            # The proposal and verifier must use byte-for-byte equivalent
            # source from the same failed commit. Raw GitHub content and the
            # ZIPball can occasionally disagree (for example, a stale SHA or
            # unexpected response); do not save a patch in that situation.
            archive_response = await client.get(
                f"https://api.github.com/repos/{owner_repo}/zipball/{run.commit_sha}"
            )
            if archive_response.status_code != 200:
                logger.warning(
                    "Skipping candidate patch: could not preflight commit %s (%s)",
                    run.commit_sha,
                    archive_response.status_code,
                )
                return None

            try:
                with zipfile.ZipFile(io.BytesIO(archive_response.content)) as archive:
                    source_member = next(
                        (
                            name for name in archive.namelist()
                            if name.endswith("/" + file_path)
                        ),
                        None,
                    )
                    if source_member is None:
                        return None
                    archive_source = archive.read(source_member).decode("utf-8")
            except (zipfile.BadZipFile, UnicodeDecodeError, OSError):
                logger.warning(
                    "Skipping candidate patch: commit archive could not be checked (%s)",
                    run.commit_sha,
                )
                return None

            # Normalize only newline representation; any content difference
            # means the patch is not safe to propose for this commit.
            if archive_source.replace("\r\n", "\n") != original.replace("\r\n", "\n"):
                logger.warning(
                    "Skipping candidate patch: raw source does not match commit archive for %s at %s",
                    file_path,
                    run.commit_sha,
                )
                return None

            return (
                patch,
                f"Removed the single-use declaration of '{identifier}' flagged by ESLint. Source matched failed commit {run.commit_sha[:12]}; review the diff before approval.",
                [file_path],
            )
    return None


router = APIRouter(prefix="/failures", tags=["Failures"])
logger = logging.getLogger(__name__)


async def _get_latest_artifact(
    db: AsyncSession,
    workflow_run_id: str,
) -> Optional[LogArtifact]:
    """
    Return the most recently created log artifact for a workflow run.

    A workflow run may legitimately have multiple artifacts. Never use
    scalar_one_or_none() for this query.
    """
    result = await db.execute(
        select(LogArtifact)
        .where(LogArtifact.workflow_run_id == workflow_run_id)
        .order_by(
            LogArtifact.created_at.desc(),
            LogArtifact.id.desc(),
        )
        .limit(1)
    )
    return result.scalars().first()


def _workflow_response(
    run: WorkflowRun,
    repository_name: str,
) -> WorkflowRunResponse:
    """Build a workflow response consistently across endpoints."""
    return WorkflowRunResponse(
        id=run.id,
        repository_id=run.repository_id,
        external_run_id=run.external_run_id,
        workflow_name=run.workflow_name,
        branch=run.branch,
        commit_sha=run.commit_sha,
        status=run.status,
        conclusion=run.conclusion,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        repository_name=repository_name,
    )


def _analysis_response(
    analysis: Analysis,
) -> AnalysisResponse:
    """Convert a stored analysis to its API response."""
    return AnalysisResponse(
        id=analysis.id,
        failure_id=analysis.failure_id,
        status=analysis.status,
        provider=analysis.provider,
        model=analysis.model,
        root_cause=analysis.root_cause,
        evidence_json=analysis.evidence_json,
        alternatives_json=analysis.alternatives_json,
        confidence=analysis.confidence,
        confidence_method=analysis.confidence_method,
        recommendations_json=analysis.recommendations_json,
        token_usage=analysis.token_usage,
        estimated_cost=analysis.estimated_cost,
        duration_ms=analysis.duration_ms,
        created_at=analysis.created_at,
    )


@router.get("", response_model=List[FailureResponse])
async def list_failures(
    repository_id: Optional[str] = None,
    category: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List failures belonging to repositories in the user's workspace."""
    query = (
        select(Failure, WorkflowRun, Repository.full_name)
        .join(
            WorkflowRun,
            Failure.workflow_run_id == WorkflowRun.id,
        )
        .join(
            Repository,
            WorkflowRun.repository_id == Repository.id,
        )
        .join(
            WorkspaceMembership,
            WorkspaceMembership.workspace_id == Repository.workspace_id,
        )
        .where(WorkspaceMembership.user_id == current_user.id)
        .order_by(Failure.last_seen_at.desc())
    )

    if repository_id:
        query = query.where(
            WorkflowRun.repository_id == repository_id
        )

    if category:
        query = query.where(Failure.category == category)

    if status_filter:
        query = query.where(Failure.status == status_filter)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            Failure.summary.ilike(term)
            | WorkflowRun.workflow_name.ilike(term)
            | WorkflowRun.branch.ilike(term)
            | Failure.failed_job_name.ilike(term)
        )

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    rows = result.all()

    failures = []

    for failure, run, repository_name in rows:
        run_response = _workflow_response(run, repository_name)

        failures.append(
            FailureResponse(
                id=failure.id,
                workflow_run_id=failure.workflow_run_id,
                failed_job_name=failure.failed_job_name,
                category=failure.category,
                severity=failure.severity,
                error_signature=failure.error_signature,
                summary=failure.summary,
                first_seen_at=failure.first_seen_at,
                last_seen_at=failure.last_seen_at,
                occurrence_count=failure.occurrence_count,
                status=failure.status,
                workflow_run=run_response,
            )
        )

    return failures


@router.get(
    "/{failure_id}",
    response_model=FailureDetailResponse,
)
async def get_failure_detail(
    failure_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return failure details, log excerpt, and latest analysis information."""
    query = (
        select(Failure, WorkflowRun, Repository.full_name)
        .join(
            WorkflowRun,
            Failure.workflow_run_id == WorkflowRun.id,
        )
        .join(
            Repository,
            WorkflowRun.repository_id == Repository.id,
        )
        .join(
            WorkspaceMembership,
            WorkspaceMembership.workspace_id == Repository.workspace_id,
        )
        .where(
            Failure.id == failure_id,
            WorkspaceMembership.user_id == current_user.id,
        )
    )

    result = await db.execute(query)
    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failure not found.",
        )

    failure, run, repository_name = row

    # Multiple artifacts can exist for one run. Select the latest one.
    artifact = await _get_latest_artifact(db, run.id)
    log_excerpt = artifact.sanitized_excerpt if artifact else None

    analysis_result = await db.execute(
        select(Analysis)
        .where(Analysis.failure_id == failure.id)
        .order_by(Analysis.created_at.desc())
        .limit(1)
    )
    latest_analysis = analysis_result.scalars().first()

    latest_proposal_id = None

    if latest_analysis:
        proposal_result = await db.execute(
            select(FixProposal)
            .where(FixProposal.analysis_id == latest_analysis.id)
            .order_by(FixProposal.created_at.desc())
            .limit(1)
        )
        proposal = proposal_result.scalars().first()

        if proposal:
            latest_proposal_id = proposal.id

    stack_traces = (
        LogParserService.extract_stack_traces(log_excerpt)
        if log_excerpt
        else []
    )
    stack_trace_text = (
        "\n\n---\n\n".join(stack_traces)
        if stack_traces
        else None
    )

    return FailureDetailResponse(
        id=failure.id,
        workflow_run_id=failure.workflow_run_id,
        failed_job_name=failure.failed_job_name,
        category=failure.category,
        severity=failure.severity,
        error_signature=failure.error_signature,
        summary=failure.summary,
        first_seen_at=failure.first_seen_at,
        last_seen_at=failure.last_seen_at,
        occurrence_count=failure.occurrence_count,
        status=failure.status,
        workflow_run=_workflow_response(run, repository_name),
        log_excerpt=log_excerpt,
        stack_trace=stack_trace_text,
        analysis_status=(
            latest_analysis.status if latest_analysis else None
        ),
        latest_analysis_id=(
            latest_analysis.id if latest_analysis else None
        ),
        latest_fix_proposal_id=latest_proposal_id,
    )


@router.post(
    "/{failure_id}/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
async def analyze_failure(
    failure_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze a captured failure using deterministic classification and
    the configured AI service, then persist the analysis and any proposal.
    """
    query = (
        select(Failure, WorkflowRun, Repository)
        .join(
            WorkflowRun,
            Failure.workflow_run_id == WorkflowRun.id,
        )
        .join(
            Repository,
            WorkflowRun.repository_id == Repository.id,
        )
        .join(
            WorkspaceMembership,
            WorkspaceMembership.workspace_id == Repository.workspace_id,
        )
        .where(
            Failure.id == failure_id,
            WorkspaceMembership.user_id == current_user.id,
        )
    )

    result = await db.execute(query)
    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failure not found.",
        )

    failure, run, repository = row

    artifact = await _get_latest_artifact(db, run.id)

    if artifact is None or not artifact.sanitized_excerpt:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "No log artifact is available for this workflow run. "
                "Sync the repository again and verify that GitHub Actions "
                "logs are accessible before analyzing this failure."
            ),
        )

    raw_log = artifact.sanitized_excerpt

    # Parse and classify the stored, sanitized log.
    parsed = LogParserService.parse_log(
        raw_log,
        failed_job_name=failure.failed_job_name,
    )

    classification = FailureClassifierService.classify(
        sanitized_log=parsed.sanitized_log,
        error_lines=parsed.error_lines,
        failed_job_name=failure.failed_job_name,
    )

    try:
        output, tokens, cost, duration = await AIService.analyze_failure(
            workflow_name=run.workflow_name,
            job_name=failure.failed_job_name,
            branch=run.branch,
            commit_sha=run.commit_sha,
            sanitized_log=parsed.sanitized_log,
            classification=classification,
            error_lines=parsed.error_lines,
            stack_traces=parsed.stack_traces,
        )

        analysis = Analysis(
            failure_id=failure.id,
            status="completed",
            provider=(
                "ai_synthesis"
                if tokens > 0
                else "deterministic_rule"
            ),
            model=(
                "gpt-4o-mini"
                if tokens > 0
                else "deterministic_rule_engine"
            ),
            root_cause=output.root_cause,
            evidence_json=json.dumps(
                [item.model_dump() for item in output.evidence]
            ),
            alternatives_json=json.dumps(
                [item.model_dump() for item in output.alternatives]
            ),
            confidence=output.confidence,
            confidence_method=output.confidence_justification,
            recommendations_json=json.dumps(
                [
                    item.model_dump()
                    for item in output.recommendations
                ]
            ),
            token_usage=tokens,
            estimated_cost=cost,
            duration_ms=duration,
        )

        db.add(analysis)
        await db.flush()

        patch, explanation, files = (
            FixGeneratorService.generate_candidate_fix(
                category=classification.category.value,
                summary=classification.summary,
                evidence_text=parsed.sanitized_log,
            )
        )
        if not patch and "lint" in classification.category.value.lower():
            source_fix = await _build_unused_variable_patch(
                repository, run, parsed.sanitized_log
            )
            if source_fix:
                patch, explanation, files = source_fix

        if patch:
            proposal = FixProposal(
                analysis_id=analysis.id,
                status="draft",
                patch_content=patch,
                explanation=(
                    explanation
                    or "Proposed candidate patch. Review before applying."
                ),
                affected_files_json=json.dumps(files),
            )
            db.add(proposal)
            failure.status = FailureStatus.FIX_PROPOSED.value
        else:
            failure.status = FailureStatus.INVESTIGATING.value

        failure.category = classification.category.value
        failure.summary = classification.summary

        await db.commit()
        await db.refresh(analysis)

        return AnalysisResponse(
            id=analysis.id,
            failure_id=analysis.failure_id,
            status=analysis.status,
            provider=analysis.provider,
            model=analysis.model,
            root_cause=analysis.root_cause,
            evidence_json=analysis.evidence_json,
            alternatives_json=analysis.alternatives_json,
            confidence=analysis.confidence,
            confidence_method=analysis.confidence_method,
            recommendations_json=analysis.recommendations_json,
            token_usage=analysis.token_usage,
            estimated_cost=analysis.estimated_cost,
            duration_ms=analysis.duration_ms,
            created_at=analysis.created_at,
            parsed_evidence=output.evidence,
            parsed_alternatives=output.alternatives,
            parsed_recommendations=output.recommendations,
        )

    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()

        logger.exception(
            "Failure analysis failed for failure_id=%s",
            failure_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Failure analysis could not be completed. "
                "Check the backend logs for the underlying error."
            ),
        ) from exc


@router.get(
    "/{failure_id}/analyses",
    response_model=List[AnalysisResponse],
)
async def list_analyses(
    failure_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List historical analyses for a failure the user can access."""
    access_query = (
        select(Failure.id)
        .join(
            WorkflowRun,
            Failure.workflow_run_id == WorkflowRun.id,
        )
        .join(
            Repository,
            WorkflowRun.repository_id == Repository.id,
        )
        .join(
            WorkspaceMembership,
            WorkspaceMembership.workspace_id == Repository.workspace_id,
        )
        .where(
            Failure.id == failure_id,
            WorkspaceMembership.user_id == current_user.id,
        )
    )

    access_result = await db.execute(access_query)

    if access_result.first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failure not found.",
        )

    result = await db.execute(
        select(Analysis)
        .where(Analysis.failure_id == failure_id)
        .order_by(Analysis.created_at.desc())
    )

    analyses = result.scalars().all()

    return [_analysis_response(analysis) for analysis in analyses]
