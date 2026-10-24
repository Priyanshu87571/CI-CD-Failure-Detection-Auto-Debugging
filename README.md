# DeployGuard — Live GitHub Edition

**AI-Assisted CI/CD Failure Detection and Auto-Debugging**

DeployGuard is a CI/CD observability application that connects to public GitHub repositories, imports GitHub Actions workflow runs, retrieves accessible failure logs, and analyzes them to identify potential causes of pipeline failures.

The application sanitizes logs, classifies likely failure causes, and stores analysis results in a dashboard for review. It is designed to help developers investigate failed workflows more efficiently and understand what went wrong in their CI/CD pipelines.

This edition integrates with real GitHub repositories and does not seed demo accounts, mock repositories, or fabricated workflow failures.

## Key Features

- **Live GitHub Integration:** Connect public GitHub repositories and synchronize their GitHub Actions workflow runs.
- **Workflow Monitoring:** Import recent workflow runs and review their execution status.
- **Failure Log Retrieval:** Retrieve logs for failed jobs when permitted by the GitHub API.
- **Log Sanitization:** Sanitize retrieved logs before processing them.
- **Failure Classification:** Apply deterministic rules to identify likely causes of CI/CD failures.
- **Failure Dashboard:** Store and review imported workflow failures and their analysis results.
- **Repository Management:** Connect repositories using either `owner/repo` or a GitHub repository URL.
- **Authentication:** Register and sign in using your own account. No default demo credentials are provided.
- **Honest Failure Reporting:** Clearly indicate when logs are inaccessible rather than generating fabricated log content.
- **Fix Verification Status:** Report verification as unavailable until a real repository checkout is connected to the isolated execution environment.

## Technology Stack

The application includes a Python backend and a modern web frontend.

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | React, TypeScript, Vite |
| Database | SQLite by default |
| GitHub Integration | GitHub REST API |
| CI/CD | GitHub Actions |
| API Documentation | FastAPI / OpenAPI |

**Note:** PostgreSQL or other database support should only be listed if it is configured and supported by the current implementation.

## Prerequisites

Install the following before running DeployGuard:

- Python 3.11 or later, compatible with the installed dependencies
- Node.js 20 or later
- npm
- Git
- Internet connectivity to `api.github.com`

## Installation and Setup

### 1. Clone the Repository

```powershell
git clone https://github.com/Priyanshu87571/CI-CD-Failure-Detection-Auto-Debugging.git
cd CI-CD-Failure-Detection-Auto-Debugging
```

### 2. Initialize the Application

Open PowerShell in the project root and execute:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup.ps1
```

The setup script prepares the Python virtual environment, installs the backend and frontend dependencies, and creates a local `.env` file containing a generated application secret.

The database defaults to SQLite for local development.

**Security reminder:** Never commit `.env` or publish real credentials, application secrets, or GitHub access tokens.

### 3. Configure GitHub Access

DeployGuard can access public repository metadata without authentication, subject to GitHub API rate limits and endpoint restrictions.

If additional API access is required, configure a GitHub token in your local `.env` file:

```dotenv
GITHUB_TOKEN=your_github_token
```

Replace the placeholder with your actual token. Never commit this value or expose it in frontend code.

Use a token with only the permissions necessary for your intended repositories and operations.

### 4. Start the Backend

From the project root, run:

```powershell
.\run-backend.ps1
```

Once the backend starts, open the interactive API documentation:

**API Documentation:** http://127.0.0.1:8000/docs

### 5. Start the Frontend

Open a second PowerShell terminal in the project root:

```powershell
.\run-frontend.ps1
```

Open the application in your browser:

**DeployGuard Dashboard:** http://localhost:5173

## Connecting a GitHub Repository

Follow these steps to analyze a real repository.

1. Open DeployGuard in your browser.
2. Register a new account.
3. Sign in with your credentials.
4. Navigate to **Repositories**.
5. Enter the repository in either format:
   - `owner/repo`
   - `https://github.com/owner/repo`
6. Connect the repository.
7. Trigger synchronization.
8. Open **CI/CD Failures** to review imported failed jobs and their available analysis.

### Important Requirements

- The repository must have GitHub Actions workflow runs to import.
- Public workflow metadata is subject to GitHub API rate limits.
- Failed-job logs may not always be accessible.
- The dashboard may remain empty until a repository has been connected and synchronized.
- Only real workflow data returned by GitHub is imported; the application does not seed fabricated failures.

## How DeployGuard Works

The application follows this workflow:

1. **Repository Connection:** The user connects a GitHub repository.
2. **Workflow Synchronization:** DeployGuard requests recent GitHub Actions workflow runs.
3. **Failure Identification:** Failed workflow runs are identified for further investigation.
4. **Log Retrieval:** The backend attempts to retrieve available logs for failed jobs.
5. **Log Sanitization:** Retrieved logs are sanitized before analysis.
6. **Failure Classification:** Deterministic rules classify likely causes based on the available information.
7. **Dashboard Review:** Results are stored and displayed for the user to investigate.

### Current Implementation Limitations

- **AI Analysis:** Failure classification currently uses deterministic rules. Generative AI analysis should only be considered available when an AI provider is configured and integrated.
- **Log Availability:** GitHub may restrict access to particular logs. DeployGuard reports these cases rather than inventing log content.
- **Automated Fix Verification:** Verification remains unavailable until a real repository checkout is integrated with an isolated execution runner.
- **Automated Fix Execution:** Do not assume that fixes are automatically applied to a repository unless that functionality has been implemented and configured.

These limitations are intentional: the application distinguishes available functionality from features that still require integration.

## Troubleshooting

| Issue | Possible Cause | Recommended Action |
|---|---|---|
| `401 Unauthorized` from application endpoints | Missing or expired authentication token | Sign in again and verify that the frontend sends the stored token. |
| GitHub `403 Forbidden` | API rate limit or insufficient permissions | Check GitHub API usage and configure `GITHUB_TOKEN` if appropriate. |
| GitHub `404 Not Found` | Incorrect repository details or unavailable resource | Verify the owner, repository name, and availability of GitHub Actions runs. |
| No workflow runs displayed | Repository has no available runs or synchronization has not completed | Check the repository's Actions tab and review backend logs. |
| Failed-job logs unavailable | GitHub API restrictions or inaccessible log resources | Review the backend logs and the status reported by DeployGuard. |
| Frontend cannot connect to backend | Backend is stopped or API configuration is incorrect | Start the backend and verify the frontend API configuration. |
| Database connection errors | Incorrect database configuration or unavailable database file | Review `DATABASE_URL` and the backend startup logs. |

## Security Considerations

Security is important when connecting DeployGuard to real repositories.

- Keep `.env` out of version control.
- Never commit GitHub tokens, passwords, or private application secrets.
- Use a strong, unique application secret.
- Apply the principle of least privilege when configuring GitHub access.
- Sanitize retrieved logs before processing or displaying them.
- Do not assume logs are free of sensitive information.
- Use isolated execution environments for future repository checkout and fix-verification features.
- Avoid executing generated patches without review and appropriate safety controls.

## Project Structure

```text
CI-CD-Failure-Detection-Auto-Debugging/
├── .github/
│   └── workflows/
│       └── ci.yml
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── tests/
│   ├── pyproject.toml
│   └── requirements.txt
├── docs/
│   ├── architecture.md
│   ├── deployment.md
│   ├── evaluation.md
│   └── security.md
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── lib/
│   │   └── pages/
│   ├── package.json
│   └── vite.config.ts
├── .dockerignore
├── .gitignore
├── Dockerfile.backend
├── docker-compose.yml
├── run-backend.ps1
├── run-frontend.ps1
├── setup.ps1
└── README.md
```

## Testing

The backend includes tests covering areas such as:

- Failure classification
- GitHub service behavior
- Log parsing
- Patch safety
- Fix verification
- Webhook signature verification

Run the tests using the command supported by your project's test configuration. For a pytest-based setup, this is typically:

```powershell
python -m pytest backend/tests -v
```

A successful test run should be verified locally or in the project's configured CI pipeline.

## Roadmap

Potential future improvements include:

- Integrating a configured generative AI provider for richer root-cause analysis.
- Connecting repository checkouts to an isolated execution runner.
- Implementing real fix verification with test execution.
- Improving analysis of complex workflow logs.
- Expanding CI/CD observability and reporting.
- Adding more comprehensive integration tests for real GitHub repositories.

These items are future improvements, not claims that the functionality is already available.

## Contributing

Contributions, bug reports, and suggestions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Run the relevant tests.
5. Submit a pull request describing your changes.

## License

A license has not been specified in this README. Add a `LICENSE` file and update this section before distributing the project under a particular open-source license.

## Author

**Priyanshu Raj**

GitHub: [@Priyanshu87571](https://github.com/Priyanshu87571)

---

*DeployGuard — Making CI/CD failures easier to investigate through real workflow data, structured analysis, and transparent reporting.*
