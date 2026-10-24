import hmac
import hashlib
import pytest
from backend.app.core.security import verify_github_signature


def test_valid_webhook_signature():
    secret = "my-secret-key-123"
    payload = b'{"action": "completed", "workflow_run": {"id": 101}}'
    mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    valid_sig = f"sha256={mac.hexdigest()}"

    assert verify_github_signature(payload, valid_sig, secret) is True


def test_invalid_webhook_signature_tampered_payload():
    secret = "my-secret-key-123"
    payload = b'{"action": "completed"}'
    tampered_payload = b'{"action": "completed", "malicious": true}'
    mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    valid_sig = f"sha256={mac.hexdigest()}"

    assert verify_github_signature(tampered_payload, valid_sig, secret) is False


def test_missing_or_malformed_signature_header():
    secret = "my-secret-key-123"
    payload = b'{"test": 1}'

    assert verify_github_signature(payload, None, secret) is False
    assert verify_github_signature(payload, "invalid-format", secret) is False
