import io
import json
import os
import shutil
import stat
import tempfile
import zipfile
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user
from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.models.analysis import Analysis
from backend.app.models.audit import AuditEvent
from backend.app.models.failure import Failure, FailureStatus
from backend.app.models.fix import FixProposal
from backend.app.models.repository import Repository
from backend.app.models.user import User
from backend.app.models.verification import VerificationRun
from backend.app.models.workflow import WorkflowRun
from backend.app.models.workspace import WorkspaceMembership
from backend.app.schemas.fix import (
    FixApprovalRequest,
    FixProposalCreate,
    FixProposalResponse,
)
from backend.app.schemas.verification import (
    VerificationRunResponse,
    VerificationTriggerRequest,
)
from backend.app.services.fix_generator import (
    FixGeneratorService,
    PatchValidationError,
)
from backend.app.services.verification_service import VerificationService


router = APIRouter(tags=["Fix Proposals & Verification"])


# ---------------------------------------------------------------------------
# Shared response helpers
# ---------------------------------------------------------------------------

def _get_affected_files(proposal: FixProposal) -> list:
    """Read affected files without failing on malformed stored JSON."""
    try:
        value = json.loads(proposal.affected_files_json or "[]")
        return value if isinstance(value, list) else []
    except (TypeError, ValueError):
        return []


def _proposal_response(
    proposal: FixProposal,
    affected_files: Optional[list] = None,
) -> FixProposalResponse:
    """Build a consistent API response for a saved proposal."""
    files = (
        affected_files
        if affected_files is not None
        else _get_affected_files(proposal)
    )

    return FixProposalResponse(
        id=proposal.id,
        analysis_id=proposal.analysis_id,
        status=proposal.status,
        patch_content=proposal.patch_content,
        explanation=proposal.explanation,
        affected_files_json=proposal.affected_files_json,
        affected_files=files,
        approved_by=proposal.approved_by,
        approved_at=proposal.approved_at,
        created_at=proposal.created_at,
    )


# ---------------------------------------------------------------------------
# Create a fix proposal
# ---------------------------------------------------------------------------

@router.post(
    "/analyses/{analysis_id}/proposals",
    response_model=FixProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_fix_proposal(
    analysis_id: str,
    prop_in: FixProposalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a candidate fix proposal for an analysis."""

    query = (
        select(Analysis, Failure, Repository)
        .join(Failure, Analysis.failure_id == Failure.id)
        .join(WorkflowRun, Failure.workflow_run_id == WorkflowRun.id)
        .join(Repository, WorkflowRun.repository_id == Repository.id)
        .join(
            WorkspaceMembership,
            WorkspaceMembership.workspace_id == Repository.workspace_id,
        )
        .where(
            Analysis.id == analysis_id,
            WorkspaceMembership.user_id == current_user.id,
        )
    )

    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found.",
        )

    try:
        affected_files = FixGeneratorService.validate_patch_safety(
            prop_in.patch_content
        )
    except PatchValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    proposal = FixProposal(
        analysis_id=analysis_id,
        status="draft",
        patch_content=prop_in.patch_content,
        explanation=prop_in.explanation,
        affected_files_json=json.dumps(affected_files),
    )

    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)

    return _proposal_response(proposal, affected_files)


# ---------------------------------------------------------------------------
# List fix proposals
# ---------------------------------------------------------------------------

@router.get(
    "/proposals",
    response_model=List[FixProposalResponse],
)
async def list_fix_proposals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's saved proposals, newest first."""

    query = (
        select(FixProposal)
        .join(Analysis, FixProposal.analysis_id == Analysis.id)
        .join(Failure, Analysis.failure_id == Failure.id)
        .join(WorkflowRun, Failure.workflow_run_id == WorkflowRun.id)
        .join(Repository, WorkflowRun.repository_id == Repository.id)
        .join(
            WorkspaceMembership,
            WorkspaceMembership.workspace_id == Repository.workspace_id,
        )
        .where(WorkspaceMembership.user_id == current_user.id)
        .order_by(FixProposal.created_at.desc())
        .limit(50)
    )

    result = await db.execute(query)
    proposals = result.scalars().all()

    return [_proposal_response(proposal) for proposal in proposals]


# ---------------------------------------------------------------------------
# Get one fix proposal
# ---------------------------------------------------------------------------

@router.get(
    "/proposals/{proposal_id}",
    response_model=FixProposalResponse,
)
async def get_proposal(
    proposal_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a single fix proposal."""

    query = (
        select(FixProposal)
        .join(Analysis, FixProposal.analysis_id == Analysis.id)
        .join(Failure, Analysis.failure_id == Failure.id)
        .join(WorkflowRun, Failure.workflow_run_id == WorkflowRun.id)
        .join(Repository, WorkflowRun.repository_id == Repository.id)
        .join(
            WorkspaceMembership,
            WorkspaceMembership.workspace_id == Repository.workspace_id,
        )
        .where(
            FixProposal.id == proposal_id,
            WorkspaceMembership.user_id == current_user.id,
        )
    )

    result = await db.execute(query)
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fix proposal not found.",
        )

    return _proposal_response(proposal)


# ---------------------------------------------------------------------------
# Approve or reject a proposal
# ---------------------------------------------------------------------------

@router.post(
    "/proposals/{proposal_id}/approve",
    response_model=FixProposalResponse,
)
async def approve_fix_proposal(
    proposal_id: str,
    approval: FixApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Require explicit developer approval or rejection."""

    query = (
        select(FixProposal, Repository)
        .join(Analysis, FixProposal.analysis_id == Analysis.id)
        .join(Failure, Analysis.failure_id == Failure.id)
        .join(WorkflowRun, Failure.workflow_run_id == WorkflowRun.id)
        .join(Repository, WorkflowRun.repository_id == Repository.id)
        .join(
            WorkspaceMembership,
            WorkspaceMembership.workspace_id == Repository.workspace_id,
        )
        .where(
            FixProposal.id == proposal_id,
            WorkspaceMembership.user_id == current_user.id,
        )
    )

    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fix proposal not found.",
        )

    proposal, repository = row

    if approval.approved:
        proposal.status = "approved"
        proposal.approved_by = current_user.id
        proposal.approved_at = datetime.now(timezone.utc)
        action = "fix_approved"
    else:
        proposal.status = "rejected"
        action = "fix_rejected"

    audit = AuditEvent(
        workspace_id=repository.workspace_id,
        actor_id=current_user.id,
        action=action,
        resource_type="FixProposal",
        resource_id=proposal.id,
        metadata_json=json.dumps(
            {"notes": approval.review_notes or ""}
        ),
    )

    db.add(audit)
    await db.commit()
    await db.refresh(proposal)

    return _proposal_response(proposal)


# ---------------------------------------------------------------------------
# Retrieve repository source from GitHub
# ---------------------------------------------------------------------------

def _retrieve_repository_source(
    repository_full_name: str,
    commit_sha: str,
    destination: str,
) -> int:
    """
    Download and safely extract source files from a GitHub commit archive.

    Returns the number of regular files extracted.

    Raises RuntimeError with a useful message if GitHub cannot provide
    a usable archive or if no source files can be extracted.
    """

    if not repository_full_name or "/" not in repository_full_name:
        raise RuntimeError(
            f"Invalid GitHub repository name: {repository_full_name!r}"
        )

    if not commit_sha:
        raise RuntimeError("The workflow run does not have a commit SHA.")

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "DeployGuard-CI-Observability",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    token = getattr(settings, "GITHUB_TOKEN", "") or ""

    if token.strip():
        headers["Authorization"] = f"Bearer {token.strip()}"

    archive_url = (
        "https://api.github.com/repos/"
        f"{repository_full_name}/zipball/{commit_sha}"
    )

    try:
        with httpx.Client(
            timeout=60.0,
            headers=headers,
            follow_redirects=True,
        ) as client:
            response = client.get(archive_url)

    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"Could not contact GitHub to retrieve repository source: {exc}"
        ) from exc

    if response.status_code != 200:
        detail = response.text[:500]

        if response.status_code == 401:
            explanation = "GitHub rejected the authentication credentials."
        elif response.status_code == 403:
            explanation = (
                "GitHub denied access or applied an API rate limit."
            )
        elif response.status_code == 404:
            explanation = (
                "The repository or commit was not found, or access "
                "to it is unavailable."
            )
        else:
            explanation = "GitHub could not provide the requested archive."

        raise RuntimeError(
            f"{explanation} HTTP {response.status_code}; "
            f"repository={repository_full_name}; "
            f"commit={commit_sha}; response={detail}"
        )

    try:
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            members = archive.infolist()

            # Ignore empty ZIP entries and identify the GitHub archive's
            # top-level directory rather than assuming its first entry
            # contains a regular source file.
            names = [
                member.filename
                for member in members
                if member.filename.strip("/")
            ]

            if not names:
                raise RuntimeError(
                    "GitHub returned an empty repository archive."
                )

            first_components = [
                name.split("/", 1)[0]
                for name in names
            ]

            if not all(
                component == first_components[0]
                for component in first_components
            ):
                raise RuntimeError(
                    "The GitHub archive has an unexpected directory layout."
                )

            root_directory = first_components[0]
            root_prefix = root_directory + "/"

            # GitHub zipball archives normally contain one root directory.
            # Support a root entry with or without a trailing slash.
            if not any(
                name.startswith(root_prefix)
                for name in names
            ):
                raise RuntimeError(
                    "Could not identify the source directory in "
                    "the GitHub archive."
                )

            destination_root = os.path.realpath(destination)
            os.makedirs(destination_root, exist_ok=True)

            extracted_count = 0

            for member in members:
                name = member.filename

                if not name or not name.startswith(root_prefix):
                    continue

                relative_path = name[len(root_prefix):]

                if not relative_path:
                    continue

                # Normalize separators and reject absolute paths.
                relative_path = relative_path.replace("\\", "/")

                if relative_path.startswith("/"):
                    continue

                target_path = os.path.realpath(
                    os.path.join(destination_root, relative_path)
                )

                # Protect against ZIP path traversal.
                try:
                    inside_destination = (
                        os.path.commonpath(
                            [destination_root, target_path]
                        )
                        == destination_root
                    )
                except ValueError:
                    inside_destination = False

                if not inside_destination:
                    continue

                if member.is_dir():
                    os.makedirs(target_path, exist_ok=True)
                    continue

                # ZIP entries can have no Unix mode information, so mode 0
                # is accepted. Explicit symlinks/devices are not extracted.
                file_mode = (
                    member.external_attr >> 16
                ) & 0o170000

                if file_mode not in (0, stat.S_IFREG):
                    continue

                os.makedirs(
                    os.path.dirname(target_path),
                    exist_ok=True,
                )

                with archive.open(member, "r") as source_file:
                    with open(target_path, "wb") as target_file:
                        shutil.copyfileobj(source_file, target_file)

                extracted_count += 1

            if extracted_count == 0:
                raise RuntimeError(
                    "GitHub returned a valid archive, but DeployGuard "
                    "could not extract any regular files. "
                    "Check the archive directory layout and ZIP entries."
                )

            return extracted_count

    except zipfile.BadZipFile as exc:
        raise RuntimeError(
            "GitHub returned a response that is not a valid ZIP archive."
        ) from exc


# ---------------------------------------------------------------------------
# Verify an approved proposal
# ---------------------------------------------------------------------------

@router.post(
    "/proposals/{proposal_id}/verify",
    response_model=VerificationRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def verify_fix_proposal(
    proposal_id: str,
    trigger_req: Optional[VerificationTriggerRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve the exact failed commit and verify an approved candidate patch.

    Verification is not executed against a fabricated checkout when source
    retrieval fails. Such failures are recorded as unavailable results.
    """

    query = (
        select(
            FixProposal,
            Analysis,
            Failure,
            WorkflowRun,
            Repository,
        )
        .join(Analysis, FixProposal.analysis_id == Analysis.id)
        .join(Failure, Analysis.failure_id == Failure.id)
        .join(WorkflowRun, Failure.workflow_run_id == WorkflowRun.id)
        .join(Repository, WorkflowRun.repository_id == Repository.id)
        .join(
            WorkspaceMembership,
            WorkspaceMembership.workspace_id == Repository.workspace_id,
        )
        .where(
            FixProposal.id == proposal_id,
            WorkspaceMembership.user_id == current_user.id,
        )
    )

    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fix proposal not found.",
        )

    proposal, analysis, failure, run, repository = row

    if proposal.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Cannot verify fix proposal: explicit developer "
                "approval is required before execution."
            ),
        )

    if not repository.full_name or not run.commit_sha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Verification cannot start because the repository name "
                "or failed workflow commit SHA is missing."
            ),
        )

    test_command = "pytest"

    if trigger_req and trigger_req.test_command:
        test_command = trigger_req.test_command.strip()

    if not test_command:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The verification test command cannot be empty.",
        )

    verification_error = None
    verification_result = None

    # Keep the checkout alive until verification has finished.
    with tempfile.TemporaryDirectory(
        prefix="deployguard_source_"
    ) as source_root:

        try:
            extracted_count = _retrieve_repository_source(
                repository_full_name=repository.full_name,
                commit_sha=run.commit_sha,
                destination=source_root,
            )

            if extracted_count <= 0:
                raise RuntimeError(
                    "Repository source retrieval completed without "
                    "extracting any source files."
                )

            # The service is called with the real checkout only.
            verification_result = VerificationService.run_verification(
                source_dir=source_root,
                patch_content=proposal.patch_content,
                test_command=test_command,
            )

        except (RuntimeError, OSError, ValueError) as exc:
            verification_error = str(exc)

    if verification_error is not None:
        # Do not call the runner with a fake path: record source retrieval
        # failure directly so no test process can accidentally be started and
        # the UI receives an accurate unavailable result.
        from backend.app.services.verification_service import VerificationResult

        verification_result = VerificationResult(
            status="unavailable",
            exit_code=None,
            duration_ms=0,
            baseline_result=None,
            candidate_result="not_run",
            test_summary={
                "command": test_command,
                "patch_applied": False,
                "source_retrieved": False,
                "commit_sha": run.commit_sha,
            },
            failure_reason=f"Repository source retrieval failed: {verification_error}",
        )

    if verification_result is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification did not produce a result.",
        )

    verification_run = VerificationRun(
        fix_proposal_id=proposal.id,
        status=verification_result.status,
        test_summary_json=json.dumps(
            verification_result.test_summary
        ),
        exit_code=verification_result.exit_code,
        duration_ms=verification_result.duration_ms,
        baseline_result=verification_result.baseline_result,
        candidate_result=verification_result.candidate_result,
        failure_reason=verification_result.failure_reason,
        completed_at=datetime.now(timezone.utc),
    )

    db.add(verification_run)
    await db.flush()

    # A fix is verified only when the original baseline failed and the
    # candidate passed. A merely passing candidate is inconclusive if the
    # baseline already passed or the original failure was not reproduced.
    if (
        verification_result.status == "passed"
        and verification_result.test_summary.get("resolved") is True
    ):
        failure.status = FailureStatus.VERIFIED.value

    audit = AuditEvent(
        workspace_id=repository.workspace_id,
        actor_id=current_user.id,
        action="verification_executed",
        resource_type="VerificationRun",
        resource_id=verification_run.id,
        metadata_json=json.dumps(
            {
                "status": verification_result.status,
                "duration_ms": verification_result.duration_ms,
                "source_retrieval_failed": (
                    verification_error is not None
                ),
            }
        ),
    )

    db.add(audit)
    await db.commit()
    await db.refresh(verification_run)

    return VerificationRunResponse(
        id=verification_run.id,
        fix_proposal_id=verification_run.fix_proposal_id,
        status=verification_run.status,
        test_summary_json=verification_run.test_summary_json,
        exit_code=verification_run.exit_code,
        duration_ms=verification_run.duration_ms,
        baseline_result=verification_run.baseline_result,
        candidate_result=verification_run.candidate_result,
        failure_reason=verification_run.failure_reason,
        created_at=verification_run.created_at,
        completed_at=verification_run.completed_at,
        parsed_test_summary=verification_result.test_summary,
    )