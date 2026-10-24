from fastapi import APIRouter, Request, Header, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/github", status_code=status.HTTP_200_OK)
async def github_webhook(
    request: Request,
    response: Response,
    x_hub_signature_256: str = Header(None),
    x_github_delivery: str = Header(None),
    x_github_event: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest signed GitHub Webhook events.
    Verifies HMAC-SHA256 signature and guarantees idempotent delivery handling.
    """
    body_bytes = await request.body()
    status_code, result = await WebhookService.process_github_webhook(
        db=db,
        payload_bytes=body_bytes,
        signature_header=x_hub_signature_256,
        delivery_id=x_github_delivery,
        event_type=x_github_event,
    )
    response.status_code = status_code
    return result
