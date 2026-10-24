# DeployGuard — Security Model & Threat Boundary

## 1. Threat Model & Trust Boundaries

DeployGuard analyzes untrusted data originating from third-party repositories, CI/CD runners, and developer-submitted workflows. The system considers the following entities untrusted by default:
- **Build & Test Logs**: May contain terminal escape sequences, malicious payload formatting, prompt-injection attacks, or leaked sensitive credentials.
- **Repository Contents & Git Diffs**: May contain path traversal exploits, arbitrary shell scripts, or malicious instruction directives aimed at confusing an LLM.
- **Webhook Payloads**: Must be authenticated via HMAC-SHA256 signature and deduplicated against replay attacks.
- **AI / LLM Outputs**: Must never be executed automatically on the host system without human-in-the-loop review, validation against safe syntax/path boundaries, and isolated execution constraints.

---

## 2. Security Boundaries & Countermeasures

### 2.1 Defense Against Prompt Injection
- System prompts strictly designate repository content, error messages, and log excerpts as **untrusted data**, not executable instructions.
- Delimiters and structured JSON schemas (via Pydantic v2) enforce strict type-safe parsing.
- Prompts instruct the model that no repository-supplied instruction can override the system policy, bypass verification, reveal secrets, or generate arbitrary commands.

### 2.2 Patch Safety & Path Traversal Prevention
Any generated patch must pass strict validation before being displayed or tested:
1. **Target Path Validation**: Target file paths are resolved against the project root. Absolute paths (e.g., `/etc/passwd`, `C:\Windows\System32`) and relative paths escaping the directory (e.g., `../../secret`) are rejected immediately with a validation error.
2. **File Scope**: Patches can only touch existing repository files or create files within allowed source directories. System-level files (`.git/hooks`, `.env`, Docker sockets) are strictly forbidden.
3. **Diff Syntax Check**: Unified diff format is parsed and checked for syntax integrity before approval.

### 2.3 Secure Test Verification Sandbox
- **No Arbitrary Shell Execution**: The verification service strictly forbids passing arbitrary command strings to `shell=True`. Commands are tokenized and validated against an explicit allowlist:
  - Allowed test runners: `pytest`, `python -m pytest`, `npm test`, `npm run test`, `yarn test`, `pnpm test`, `go test`, `cargo test`.
  - Disallowed symbols: `;`, `&`, `|`, `>`, `<`, `$`, `` ` ``, `&&`, `||`.
- **Credential Stripping**: Subprocess and container environments have their environment variables scrubbed of `GITHUB_TOKEN`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DATABASE_URL`, and secret credentials.
- **Temporary Working Copies**: Tests run on isolated temporary copies created via `tempfile.TemporaryDirectory`. Once test execution finishes (or times out), the temporary directory is destroyed.
- **Execution Resource Limits**:
  - Max Timeout: 60 seconds (configurable, default 45s).
  - Clean termination of child process trees.
- **Container Isolation Guarantee**: When Docker is available, verification runs inside non-root, network-disabled containers (`--network none`) with read-only volume mounts except for the scratch workspace. When Docker is not installed on the host, the system reports `UNAVAILABLE` with an explicit diagnostic reason.

### 2.4 Authentication & Authorization
- **Password Storage**: Modern Argon2id password hashing with custom salt and high work factor.
- **Workspace Isolation**: Multi-tenant workspace data isolation. Every query enforces `workspace_id` scoping to prevent cross-tenant access.
- **Role-Based Access Control**:
  - `Owner`: Full management, deletion, and token administration.
  - `Admin`: Repository connection, sync, and fix approval.
  - `Member`: View failures, trigger analysis, and propose fixes.
- **Secrets Protection**: Secrets (`GITHUB_APP_PRIVATE_KEY`, `WEBHOOK_SECRET`, `AI_API_KEY`) are never stored in plaintext in the database or logged in application logs.
