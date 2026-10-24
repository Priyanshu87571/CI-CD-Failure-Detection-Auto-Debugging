# Deployment checklist

## Before publishing

- [ ] Set a long random `SECRET_KEY` and strong unique PostgreSQL password in your host's secret manager.
- [ ] Confirm no test/demo credentials are configured and use a dedicated production database.
- [ ] Configure HTTPS and a production domain; update `FRONTEND_URL` and `CORS_ORIGINS` to that origin.
- [ ] Configure database backups and test restoration.
- [ ] Configure AI provider and GitHub App only if those integrations are required.
- [ ] Keep GitHub private keys outside the image and repository.
- [ ] Review the verification runner before allowing untrusted code execution.
- [ ] Smoke-test registration, login, protected routes, failure analysis, and health/readiness after deployment.
- [ ] Review the localStorage JWT limitation in `README.md`; use secure HttpOnly cookies and CSRF protections for a hardened public deployment.

## Docker Compose smoke test

```bash
docker compose config
docker compose up --build -d
docker compose ps
curl -fsS http://localhost:8080/api/v1/health
curl -fsS http://localhost:8080/api/v1/ready
```

The API startup currently initializes tables from SQLAlchemy metadata for the MVP. Add and review Alembic migrations before evolving a production schema.
