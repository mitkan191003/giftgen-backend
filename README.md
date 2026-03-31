# GiftGen Backend

GiftGen Backend is the application layer behind GiftGen, a 3D gift generation experience built around text prompts, asynchronous generation jobs, and shareable results.

This repository contains the API, the background worker, the cleanup job, and the Helm chart used to deploy the backend into Kubernetes. In production, it sits between the frontend and the rest of the platform. It accepts user requests, manages job state, talks to external generation services, stores metadata in Postgres, stores generated assets in S3, and exposes the data the frontend needs to render finished gifts.

## Related Repositories

- [giftgen-frontend](https://github.com/mitkan191003/giftgen-frontend): the Next.js application used by end users
- [giftgen-infra](https://github.com/mitkan191003/giftgen-infra): Terraform and delivery infrastructure for AWS, ArgoCD, and environment setup

## Where This Repo Fits

At a high level, the system looks like this:

1. A user signs in and starts a generation flow in the frontend.
2. The frontend sends requests to this backend.
3. The backend refines prompts, creates generation jobs, and hands work off to the worker.
4. The worker calls the external model service, stores the resulting files, and marks the job complete.
5. The backend exposes those results back to the frontend for previewing, sharing, and download.

The codebase is organized as a modular backend that is deployed as two runtime workloads:

- `giftgen-api` for HTTP traffic
- `giftgen-worker` for background processing

That split keeps the domain model in one repository without forcing long-running generation work and user-facing API traffic into the same process.

## What’s In This Repository

- FastAPI application code
- SQLAlchemy models and Alembic migrations
- generation worker and scheduled cleanup worker
- storage and provider adapters
- container build files
- Helm chart for Kubernetes deployment
- basic architecture notes and test coverage

## Getting Started

The backend is designed so it can run locally without a full cloud environment. Local development uses SQLite and local asset storage by default.

### Requirements

- Python 3.12
- a virtual environment tool of your choice

### Local Setup

1. Create and activate a virtual environment.
2. Install the package and development dependencies.
3. Copy `.env.example` to `.env` and adjust values if needed.
4. Run the API.
5. Run the worker separately if you want to process generation jobs locally.

Example:

```bash
python -m venv venv
source venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
uvicorn app.main:app --reload
```

To run the worker in another shell:

```bash
source venv/bin/activate
python -m app.workers.generation --watch
```

By default, local development uses:

- SQLite for relational data
- local filesystem storage for generated assets
- development auth instead of Cognito

That keeps the repository approachable when you want to work on API behavior, job flow, or data models without standing up the full AWS stack first.

## Configuration

The main runtime settings live in `.env`. A few of the most important ones are:

- `DATABASE_URL`
- `AUTH_MODE`
- `MODAL_API_URL`
- `ASSET_STORAGE_MODE`
- `PUBLIC_SHARE_BASE_URL`

For deployed environments, the backend can also resolve database and provider credentials from AWS Secrets Manager using:

- `DATABASE_SECRET_ID`
- `DATABASE_ENDPOINT`
- `MODAL_SECRET_ID`
- `OPENAI_SECRET_ID`

## Deployment

Production deployment is handled outside this repository:

- images are built and pushed by the delivery pipeline from the infrastructure repo
- ArgoCD deploys the Helm chart
- Kubernetes runtime configuration is assembled from Terraform-managed infrastructure outputs and AWS secrets

This repository includes the deployment artifacts needed for that flow:

- `Dockerfile.api`
- `Dockerfile.worker`
- `helm/giftgen`
- `buildspec.images.yml`
- `buildspec.deploy.yml`

## Useful Entry Points

- `GET /healthz`
- `GET /readyz`
- `POST /api/v1/creations`
- `GET /api/v1/creations`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/assets/{asset_id}/content`
- `GET /api/v1/public/shares/{slug}`

## Further Reading

- [docs/architecture.md](docs/architecture.md)
- [helm/README.md](helm/README.md)
