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

Observability-related envs:

```env
SERVICE_NAME=giftgen-api
LOG_LEVEL=INFO
METRIC_NAMESPACE=GiftGen/Application
REQUEST_ID_HEADER_NAME=X-Request-Id
SENTRY_DSN=
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_ENABLE_LOGS=false
```

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

## Observability

The backend now emits:

- structured JSON logs for API, worker, and cleanup
- request IDs on every API response
- CloudWatch Embedded Metric Format metrics for request, auth, generation, Modal, prompt refinement, and cleanup activity
- optional Sentry events if `SENTRY_DSN` is set

The request correlation path is:

1. frontend generates `X-Request-Id`
2. API returns the same request ID in the response header
3. backend logs include `request_id`
4. worker logs include `job_id` and `creation_id`

Use the log and metric names documented in [Observability.md](/home/mithrak/giftgen/Observability.md).

## Containers And Helm

This repo now includes:

- `Dockerfile.api`
- `Dockerfile.worker`
- `buildspec.images.yml`
- `buildspec.deploy.yml`
- `helm/giftgen`
- `scripts/check_runtime_config.py`

The Helm chart deploys:

- API deployment and service
- worker deployment
- cleanup `CronJob`
- Alembic migration `Job` ordered before the API and worker with Argo sync waves
- optional API `Ingress`

If you enable the AWS delivery path in Terraform, CodeBuild uses `buildspec.images.yml` to build and push both backend images using the source commit SHA as the image tag. If you also enable the optional refresh stage, `buildspec.deploy.yml` updates the ArgoCD `Application` to use that same commit SHA for both `targetRevision` and the Helm image-tag overrides before syncing.

For a cheap local guardrail before pushing, run:

```bash
cd backend
python3 scripts/check_runtime_config.py
```

That validates the resolved runtime settings and ensures SQLAlchemy can parse and construct an engine from the computed database URL without making a live database connection.

To validate the deployed AWS path instead of the local sqlite default, run it with the same DB env shape the pod uses, for example:

```bash
cd backend
DATABASE_URL= \
DATABASE_SECRET_ID=<rds-secret-arn-or-name> \
DATABASE_ENDPOINT=<rds-endpoint> \
python3 scripts/check_runtime_config.py
```

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
