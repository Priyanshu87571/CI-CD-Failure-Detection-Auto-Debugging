# DeployGuard — Live GitHub Edition

DeployGuard connects to public GitHub repositories, imports GitHub Actions workflow runs, retrieves failed job logs where the GitHub API permits it, sanitizes logs, classifies likely causes, and stores the results for review. This build has no seeded accounts or fake repository data.

## Requirements
- Python 3.11+ (tested design target; use a version supported by installed dependencies)
- Node.js 20+ and npm
- Internet access to api.github.com

## 1. Setup on Windows (PowerShell)
From the extracted project root, run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup.ps1
```

The script creates a Python virtual environment, installs backend/frontend dependencies, and creates `.env` with a generated local secret. `DATABASE_URL` defaults to local SQLite. `GITHUB_TOKEN` is optional for public repositories but recommended if GitHub rate limits are reached. Never commit `.env`.

Start the backend from the project root:

```powershell
.\run-backend.ps1
```

Docs: http://127.0.0.1:8000/docs

## 2. Frontend
In a second terminal:

```powershell
.\run-frontend.ps1
```

Open http://localhost:5173. Create your own account on the registration screen; no default credentials are created.

## 3. Connect a repository
1. Register and sign in.
2. Open Repositories.
3. Paste either `owner/repo` or `https://github.com/owner/repo`.
4. Connect, then sync.
5. Open CI/CD Failures to review imported failed jobs.

A repository must have GitHub Actions runs for runs to be imported. Public workflow metadata is available unauthenticated subject to GitHub's rate limits. Configure `GITHUB_TOKEN` in `.env` if rate limited. The token is read server-side only.

## Important behavior
- No demo account, fake workflow, or fake failure is seeded. Empty dashboards are expected until you register and connect a repository.
- Sync imports recent workflow runs and tries to fetch logs for failed jobs. GitHub may deny logs in some cases; those cases are logged and represented with a message that the log could not be accessed, not fabricated logs.
- Root-cause labels are deterministic rules, not a claim of generative AI unless an AI provider is configured.
- Fix verification intentionally reports unavailable until a real repository checkout is wired into the isolated runner. It never creates a fake sample repository or simulates a passing test.

## Troubleshooting
- `401` on app endpoints: sign in again and ensure the frontend token is present.
- GitHub `403`: rate limit or permission restriction; configure `GITHUB_TOKEN`.
- GitHub `404`: check owner/repository and whether Actions has run.
- Zero runs: verify the repository's Actions tab contains runs and check the backend logs.

## Security
Use a strong unique `SECRET_KEY`; store GitHub token only in local `.env`; do not share tokens or commit secrets.
