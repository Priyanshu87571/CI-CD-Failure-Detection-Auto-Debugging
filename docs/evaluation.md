# DeployGuard — Evaluation Methodology & Metrics

## 1. Failure Classification Engine

DeployGuard utilizes a dual-engine architecture:
1. **Deterministic Rules Engine**: High-precision regex pattern matchers that evaluate log structure, exit codes, and known framework outputs.
2. **AI Semantic Synthesis Engine**: Provider-independent LLM analysis that identifies nuanced architectural regressions, race conditions, or missing dependencies across multi-file projects.

### 10 Standard Failure Categories
1. `DEPENDENCY_INSTALLATION`: Missing packages, incompatible version resolutions, lockfile mismatch, package registry 404/500 errors.
2. `COMPILATION_SYNTAX`: Syntax errors, compilation failures, TypeScript/Babel compiler errors, missing imports.
3. `UNIT_TEST`: Test assertion errors, mock expectation failures, unexpected exceptions inside unit test suites.
4. `LINTING_FORMATTING`: Linter failures (ESLint, Flake8, Ruff), code style checks, prettier formatting diffs.
5. `MISSING_ENV_VAR`: Undefined environment variables, missing configuration keys, `.env` file absent.
6. `CONFIGURATION_ERROR`: Invalid YAML/JSON configs, improper GitHub Actions action syntax, malformed database connection strings.
7. `PERMISSION_ERROR`: File system permission denied (EACCES), insufficient GitHub token scopes, forbidden API calls (403).
8. `NETWORK_EXTERNAL_SERVICE`: DNS failure, external API connection timeout, HTTP 502/503 from external dependencies.
9. `RESOURCE_TIMEOUT`: Workflow or step timeout exceeded, Out-Of-Memory (OOM) killer killed process, disk space full.
10. `UNKNOWN`: Insufficient evidence or unclassified log output requiring developer inspection.

---

## 2. Confidence Scoring & Transparency

DeployGuard defines explicit scoring rules with transparent rationales:
- **0.90 – 1.00 (High)**: Deterministic pattern match with isolated stack trace, exact line numbers, and explicit error code (e.g., `ModuleNotFoundError: No module named 'requests'`).
- **0.70 – 0.89 (Medium)**: Clear test failure or semantic error in code with stack trace pointing to specific function or file, but multiple potential fixes exist.
- **0.50 – 0.69 (Moderate)**: Broad error detected (e.g., generic exit code 1 or network timeout) with multiple contributing factors.
- **< 0.50 (Low / Inconclusive)**: Truncated logs, non-standard error output, or contradictory error signals. Marked as `INCONCLUSIVE` requiring further diagnostic input.

---

## 3. Fix Verification Evaluation

Every candidate patch undergoes comparative verification:
- **Baseline Test Run**: Executed against the unmodified failure commit to confirm reproduction of the failure.
- **Candidate Test Run**: Executed against the patched workspace to evaluate if the failure is resolved.
- **Verification Outcomes**:
  - `PASSED`: Candidate tests succeed with exit code 0, and previously failing tests now pass.
  - `FAILED`: Candidate tests fail with exit code != 0.
  - `TIMED_OUT`: Test execution exceeded the strict timeout limit.
  - `UNAVAILABLE`: Sandbox/container execution environment is not accessible on the host.

No fix is ever marked as resolved without actual test verification confirmation.
