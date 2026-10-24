import pytest
from backend.app.services.log_parser import LogParserService


def test_strip_ansi():
    colored_text = "\x1b[31mError:\x1b[0m \x1b[1;33mBuild failed\x1b[0m"
    stripped = LogParserService.strip_ansi(colored_text)
    assert stripped == "Error: Build failed"


def test_redact_secrets():
    raw_log = "Error connecting to db: password='superSecretPassword123' token=ghp_1234567890abcdef1234567890abcdef1234"
    sanitized = LogParserService.redact_secrets(raw_log)
    assert "superSecretPassword123" not in sanitized
    assert "ghp_1234567890abcdef1234567890abcdef1234" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized or "[REDACTED_GITHUB_TOKEN]" in sanitized


def test_extract_stack_traces_python():
    log_content = """
2026-10-12T10:00:00Z Starting test...
Traceback (most recent call last):
  File "src/main.py", line 12, in run
    raise ValueError("Invalid configuration")
ValueError: Invalid configuration
Process exited with code 1.
"""
    traces = LogParserService.extract_stack_traces(log_content)
    assert len(traces) == 1
    assert "Traceback (most recent call last):" in traces[0]
    assert "ValueError: Invalid configuration" in traces[0]


def test_normalized_signature_consistency():
    err1 = [(12, "Traceback (most recent call last):"), (14, "ModuleNotFoundError: No module named 'requests' at 0x7f8a9b")]
    err2 = [(99, "Traceback (most recent call last):"), (101, "ModuleNotFoundError: No module named 'requests' at 0x1a2b3c")]

    sig1 = LogParserService.compute_normalized_signature("build", err1)
    sig2 = LogParserService.compute_normalized_signature("build", err2)

    assert sig1 == sig2
    assert len(sig1) == 64
