import io
import zipfile
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.failure import Failure, FailureCategory, FailureStatus
from backend.app.models.repository import Repository
from backend.app.models.workflow import LogArtifact, WorkflowRun
from backend.app.services.failure_classifier import FailureClassifierService
from backend.app.services.log_parser import LogParserService


class GitHubService:
    """Synchronize real GitHub Actions runs and classify failed job logs."""

    FAILED_CONCLUSIONS = {"failure", "timed_out", "action_required"}

    @staticmethod
    def normalize_repo(value: str) -> str:
        value = (value or "").strip().rstrip("/")

        if value.endswith(".git"):
            value = value[:-4]

        if value.startswith(("https://", "http://")):
            parsed = urlparse(value)

            if parsed.hostname not in {"github.com", "www.github.com"}:
                raise ValueError(
                    "Only github.com repository URLs are supported."
                )

            if parsed.query or parsed.fragment:
                raise ValueError(
                    "Enter a repository URL without query parameters or fragments."
                )

            parts = [
                part for part in parsed.path.strip("/").split("/") if part
            ]
        else:
            parts = value.split("/")

        if len(parts) != 2 or not all(
            __import__("re").fullmatch(r"[A-Za-z0-9_.-]+", part)
            for part in parts
        ):
            raise ValueError(
                "Enter a repository as owner/repo or "
                "https://github.com/owner/repo."
            )

        return f"{parts[0]}/{parts[1]}"

    @staticmethod
    def _headers() -> dict:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "DeployGuard-CI-Observability",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        token = getattr(settings, "GITHUB_TOKEN", "") or ""
        if token.strip():
            headers["Authorization"] = f"Bearer {token.strip()}"

        return headers

    @staticmethod
    def _parse_time(value):
        if not value:
            return None

        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (ValueError, AttributeError, TypeError):
            return None

    @classmethod
    async def sync_repository(
        cls, db: AsyncSession, repo: Repository
    ) -> int:
        try:
            repo.full_name = cls.normalize_repo(repo.full_name)
            return await cls._sync_real_github(db, repo)
        except Exception:
            await db.rollback()
            raise

    @classmethod
    async def _sync_real_github(
        cls, db: AsyncSession, repo: Repository
    ) -> int:
        headers = cls._headers()
        base = f"https://api.github.com/repos/{repo.full_name}"

        async with httpx.AsyncClient(
            timeout=45,
            follow_redirects=True,
        ) as client:
            response = await client.get(
                f"{base}/actions/runs",
                params={"per_page": 100},
                headers=headers,
            )

            if response.status_code == 404:
                raise ValueError(
                    "Repository or Actions runs were not found. Verify the "
                    "repository URL and that GitHub Actions has run at least once."
                )

            if response.status_code == 401:
                raise ValueError(
                    "GitHub rejected the configured token. Check GITHUB_TOKEN."
                )

            if response.status_code == 403:
                remaining = response.headers.get(
                    "X-RateLimit-Remaining", "unknown"
                )
                raise ValueError(
                    "GitHub denied the request or the API rate limit was reached "
                    f"(remaining: {remaining}). Configure GITHUB_TOKEN or retry later."
                )

            response.raise_for_status()

            try:
                runs = response.json().get("workflow_runs", [])
            except (ValueError, AttributeError) as exc:
                raise ValueError(
                    "GitHub returned an invalid workflow-runs response."
                ) from exc

            imported = 0

            for item in runs:
                external_id = str(item["id"])

                result = await db.execute(
                    select(WorkflowRun).where(
                        WorkflowRun.repository_id == repo.id,
                        WorkflowRun.external_run_id == external_id,
                    )
                )
                run = result.scalar_one_or_none()

                if run is None:
                    run = WorkflowRun(
                        repository_id=repo.id,
                        external_run_id=external_id,
                        workflow_name=(
                            item.get("name")
                            or item.get("display_title")
                            or "GitHub Actions workflow"
                        ),
                        branch=item.get("head_branch") or "unknown",
                        commit_sha=item.get("head_sha") or "unknown",
                        status=item.get("status") or "completed",
                        conclusion=item.get("conclusion"),
                        started_at=cls._parse_time(
                            item.get("run_started_at")
                        ),
                        completed_at=(
                            cls._parse_time(item.get("updated_at"))
                            if item.get("status") == "completed"
                            else None
                        ),
                    )
                    db.add(run)
                    await db.flush()
                    imported += 1
                else:
                    run.status = item.get("status") or run.status
                    run.conclusion = item.get("conclusion")
                    run.workflow_name = (
                        item.get("name") or run.workflow_name
                    )
                    run.branch = item.get("head_branch") or run.branch
                    run.commit_sha = item.get("head_sha") or run.commit_sha

                    if item.get("run_started_at"):
                        run.started_at = cls._parse_time(
                            item.get("run_started_at")
                        )

                    if item.get("status") == "completed":
                        run.completed_at = cls._parse_time(
                            item.get("updated_at")
                        )
                    else:
                        run.completed_at = None

                if (
                    run.status == "completed"
                    and run.conclusion in cls.FAILED_CONCLUSIONS
                ):
                    await cls._ingest_failed_jobs(
                        db=db,
                        client=client,
                        base=base,
                        headers=headers,
                        run=run,
                        external_id=external_id,
                        html_url=item.get("html_url", ""),
                    )

            repo.connection_status = "connected"
            repo.last_synced_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(
                "GitHub sync complete repo=%s returned=%d new=%d",
                repo.full_name,
                len(runs),
                imported,
            )

            return imported

    @classmethod
    async def _ingest_failed_jobs(
        cls,
        db: AsyncSession,
        client: httpx.AsyncClient,
        base: str,
        headers: dict,
        run: WorkflowRun,
        external_id: str,
        html_url: str,
    ) -> None:
        """Import accessible failed-job logs and classify their root causes."""

        try:
            jobs_response = await client.get(
                f"{base}/actions/runs/{external_id}/jobs",
                params={"per_page": 100},
                headers=headers,
            )

            if jobs_response.status_code in {401, 403, 404}:
                logger.warning(
                    "Cannot access jobs for run %s (HTTP %s); "
                    "workflow metadata remains available.",
                    external_id,
                    jobs_response.status_code,
                )
                return

            jobs_response.raise_for_status()
            jobs = jobs_response.json().get("jobs", [])

        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            logger.warning(
                "Could not retrieve jobs for run %s: %s",
                external_id,
                type(exc).__name__,
            )
            return

        for job in jobs:
            if job.get("conclusion") not in cls.FAILED_CONCLUSIONS:
                continue

            job_name = job.get("name") or "failed job"

            try:
                log_response = await client.get(
                    f"{base}/actions/jobs/{job['id']}/logs",
                    headers=headers,
                )

                if log_response.status_code in {401, 403, 404}:
                    logger.warning(
                        "Cannot access logs for job %s (HTTP %s).",
                        job.get("id"),
                        log_response.status_code,
                    )
                    raw_log = (
                        f"GitHub reports job '{job_name}' failed, but its "
                        "logs were not accessible to DeployGuard. "
                        f"Workflow: {html_url}"
                    )
                else:
                    log_response.raise_for_status()
                    raw_log = cls._decode_job_logs(log_response.content)

            except (httpx.HTTPError, KeyError, ValueError) as exc:
                logger.warning(
                    "Could not download logs for job %s: %s",
                    job.get("id"),
                    type(exc).__name__,
                )
                raw_log = (
                    f"GitHub reports job '{job_name}' failed, but its logs "
                    f"could not be downloaded. Workflow: {html_url}"
                )

            parsed = LogParserService.parse_log(
                raw_log,
                failed_job_name=job_name,
            )

            result = await db.execute(
                select(LogArtifact).where(
                    LogArtifact.workflow_run_id == run.id,
                    LogArtifact.content_hash == parsed.content_hash,
                )
            )
            existing_artifact = result.scalars().first()

            # Reuse the existing artifact when the log is unchanged.
            # Still reclassify the failure so stale UNKNOWN records can recover.
            if existing_artifact is None:
                artifact = LogArtifact(
                    workflow_run_id=run.id,
                    storage_reference=html_url or None,
                    sanitized_excerpt=parsed.sanitized_log,
                    content_hash=parsed.content_hash,
                )
                db.add(artifact)
                await db.flush()
            else:
                parsed = LogParserService.parse_log(
                    existing_artifact.sanitized_excerpt or raw_log,
                    failed_job_name=job_name,
                )

            classification = FailureClassifierService.classify(
                sanitized_log=parsed.sanitized_log,
                error_lines=parsed.error_lines,
                failed_job_name=job_name,
            )

            result = await db.execute(
                select(Failure).where(
                    Failure.workflow_run_id == run.id,
                    Failure.failed_job_name == job_name,
                    Failure.error_signature == parsed.normalized_signature,
                )
            )
            failure = result.scalars().first()
            now = datetime.now(timezone.utc)

            if failure is not None:
                failure.last_seen_at = now
                failure.category = classification.category.value
                failure.summary = classification.summary
            else:
                db.add(
                    Failure(
                        workflow_run_id=run.id,
                        failed_job_name=job_name,
                        category=classification.category.value,
                        severity=(
                            "high"
                            if classification.category == FailureCategory.UNIT_TEST
                            else "medium"
                        ),
                        error_signature=parsed.normalized_signature,
                        summary=classification.summary,
                        first_seen_at=now,
                        last_seen_at=now,
                        occurrence_count=1,
                        status=FailureStatus.OPEN.value,
                    )
                )

            logger.info(
                "Processed failed GitHub job run=%s job=%s category=%s rule=%s",
                external_id,
                job_name,
                classification.category.value,
                classification.rule_id,
            )

    @staticmethod
    def _decode_job_logs(content: bytes) -> str:
        """Decode GitHub job logs, supporting ZIP and plain-text responses."""

        if not content:
            return "GitHub returned an empty job-log response."

        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                texts = []

                for name in archive.namelist():
                    if name.endswith("/"):
                        continue

                    try:
                        texts.append(
                            archive.read(name).decode(
                                "utf-8",
                                errors="replace",
                            )
                        )
                    except (OSError, KeyError, RuntimeError):
                        logger.warning(
                            "Could not decode a file in the job-log archive."
                        )

                if texts:
                    return "\n".join(texts)

                return (
                    "The GitHub job-log archive contained no readable log files."
                )

        except (zipfile.BadZipFile, OSError, ValueError):
            return content.decode("utf-8", errors="replace")
