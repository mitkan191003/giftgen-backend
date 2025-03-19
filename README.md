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

- Replace development auth with Cognito JWT validation.
- Set `DATABASE_URL` to the RDS connection string.
- Set `ASSET_STORAGE_MODE=s3` and `ASSET_BUCKET_NAME`.
- Configure `MODAL_API_URL` and Modal proxy auth headers if the endpoint requires them.
- Point `PUBLIC_SHARE_BASE_URL` at the frontend share domain.

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
