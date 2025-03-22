# GiftGen Backend

FastAPI application for chat orchestration, creation metadata, sharing, and generation job management.

## Architecture

The backend is intentionally split into two runtime paths that share one codebase:

- `giftgen-api`: user-facing HTTP API for threads, creations, shares, and health endpoints
- `giftgen-worker`: background worker that processes queued generation jobs and persists assets

The production target is EKS. For local development this scaffold defaults to SQLite and local asset storage so the app can run before RDS, S3, and Cognito are wired.

## Local Development

1. Create a virtual environment and install dependencies.
2. Set `AUTH_MODE=development`.
3. Run the API with `uvicorn app.main:app --reload`.
4. Optionally run the worker with `python -m app.workers.generation --watch`.

Example environment:

```env
DATABASE_URL=sqlite+pysqlite:///./giftgen.db
AUTH_MODE=development
MODAL_API_URL=
ASSET_STORAGE_MODE=local
PUBLIC_SHARE_BASE_URL=http://localhost:3000/share
```

Authenticated routes accept `X-Dev-User-Email` while `AUTH_MODE=development`.

## Production Notes

- For Cognito-backed environments set:

```env
AUTH_MODE=cognito
COGNITO_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_...
COGNITO_CLIENT_ID=...
COGNITO_DOMAIN=https://your-prefix.auth.us-east-1.amazoncognito.com
```

- The backend verifies Cognito JWTs and maps users by the stable Cognito subject claim.
- The frontend should send the Cognito ID token as the bearer token for API requests.
- Set `DATABASE_URL` to the RDS connection string.
- Set `ASSET_STORAGE_MODE=s3` and `ASSET_BUCKET_NAME`.
- Configure `MODAL_API_URL` and Modal proxy auth headers if the endpoint requires them.
- Point `PUBLIC_SHARE_BASE_URL` at the frontend share domain.

For the deployed EKS path, the preferred runtime inputs are:

- `DATABASE_SECRET_ID`
- `DATABASE_ENDPOINT`
- `MODAL_SECRET_ID`
- `OPENAI_SECRET_ID`

The application resolves those values from AWS Secrets Manager at startup, so the first deployment path does not need handwritten Kubernetes secrets for database or provider credentials.

Database note:

- RDS-managed Secrets Manager payloads are not treated as the sole source of connection metadata anymore.
- The runtime can now combine `DATABASE_SECRET_ID` with `DATABASE_ENDPOINT`, which makes startup resilient if the secret only contains credentials and not the hostname.

## Containers And Helm

This repo now includes:

- `Dockerfile.api`
- `Dockerfile.worker`
- `helm/giftgen`

The Helm chart deploys:

- API deployment and service
- worker deployment
- cleanup `CronJob`
- pre-sync Alembic migration `Job`
- optional API `Ingress`

## Initial Surface

- `GET /healthz`
- `GET /readyz`
- `POST /api/v1/threads`
- `GET /api/v1/threads`
- `GET /api/v1/threads/{thread_id}`
- `POST /api/v1/threads/{thread_id}/messages`
- `POST /api/v1/creations`
- `GET /api/v1/creations`
- `GET /api/v1/jobs/{job_id}`
- `POST /api/v1/shares`
- `POST /api/v1/shares/{share_id}/revoke`
- `GET /api/v1/public/shares/{slug}`
- `GET /api/v1/assets/{asset_id}/content`
- `GET /api/v1/public/assets/{asset_id}`
