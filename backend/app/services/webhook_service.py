import json
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.core.config import settings
from backend.app.core.security import verify_github_signature
from backend.app.core.logging import logger
from backend.app.models.webhook import WebhookEvent
from backend.app.models.repository import Repository
from backend.app.models.workflow import WorkflowRun
from backend.app.models.failure import Failure, FailureStatus
from backend.app.services.log_parser import LogParserService
from backend.app.services.failure_classifier import FailureClassifierService


class WebhookService:
    @classmethod
    async def process_github_webhook(
        cls,
        db: AsyncSession,
        payload_bytes: bytes,
        signature_header: Optional[str],
        delivery_id: Optional[str],
        event_type: Optional[str],
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Verify and process incoming GitHub webhook.
        Returns: (http_status_code, response_dict)
        """
        if not delivery_id:
            return 400, {"error": "Missing X-GitHub-Delivery header."}

        # Step 1: Verify HMAC-SHA256 signature
        if settings.GITHUB_WEBHOOK_SECRET:
            is_valid = verify_github_signature(
                payload_body=payload_bytes,
                signature_header=signature_header,
                secret=settings.GITHUB_WEBHOOK_SECRET,
            )
            if not is_valid:
                logger.warning(f"Rejected webhook delivery {delivery_id}: Invalid HMAC signature.")
                return 401, {"error": "Invalid webhook signature."}

        # Step 2: Check Delivery Idempotency
        existing_event = await db.execute(
            select(WebhookEvent).where(WebhookEvent.external_delivery_id == delivery_id)
        )
        if existing_event.scalar_one_or_none():
            logger.info(f"Idempotent webhook: Delivery {delivery_id} already received.")
            return 200, {"status": "duplicate", "delivery_id": delivery_id}

        # Record incoming event
        webhook_event = WebhookEvent(
            provider="github",
            external_delivery_id=delivery_id,
            event_type=event_type or "unknown",
            processing_status="received",
            payload_json=payload_bytes.decode("utf-8", errors="replace"),
            received_at=datetime.now(timezone.utc),
        )
        db.add(webhook_event)
        await db.commit()

        # Step 3: Parse event payload
        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except json.JSONDecodeError:
            webhook_event.processing_status = "error"
            await db.commit()
            return 400, {"error": "Malformed JSON payload."}

        # Handle 'workflow_run' events
        if event_type == "workflow_run":
            action = payload.get("action")
            workflow_run_data = payload.get("workflow_run", {})
            conclusion = workflow_run_data.get("conclusion")
            repo_full_name = payload.get("repository", {}).get("full_name")

            if conclusion == "failure" and repo_full_name:
                # Find repository
                res = await db.execute(select(Repository).where(Repository.full_name == repo_full_name))
                repo = res.scalar_one_or_none()
                if repo:
                    ext_run_id = str(workflow_run_data.get("id"))
                    run_query = await db.execute(
                        select(WorkflowRun).where(
                            WorkflowRun.repository_id == repo.id,
                            WorkflowRun.external_run_id == ext_run_id
                        )
                    )
                    run = run_query.scalar_one_or_none()
                    if not run:
                        run = WorkflowRun(
                            repository_id=repo.id,
                            external_run_id=ext_run_id,
                            workflow_name=workflow_run_data.get("name", "Workflow"),
                            branch=workflow_run_data.get("head_branch", "main"),
                            commit_sha=workflow_run_data.get("head_sha", "unknown"),
                            status="completed",
                            conclusion="failure",
                        )
                        db.add(run)
                        await db.flush()

                    # Create failure record
                    failure = Failure(
                        workflow_run_id=run.id,
                        failed_job_name=workflow_run_data.get("name", "build"),
                        category="unknown",
                        severity="high",
                        error_signature=delivery_id,
                        summary=f"CI Failure reported by GitHub Actions: {workflow_run_data.get('name')}",
                        status=FailureStatus.OPEN.value,
                    )
                    db.add(failure)
                    webhook_event.processing_status = "processed"
                    webhook_event.processed_at = datetime.now(timezone.utc)
                    await db.commit()
                    return 200, {"status": "processed", "run_id": run.id}

        webhook_event.processing_status = "ignored"
        webhook_event.processed_at = datetime.now(timezone.utc)
        await db.commit()
        return 200, {"status": "ignored", "event": event_type}
