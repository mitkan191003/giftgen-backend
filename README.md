# GiftGen Backend

GiftGen Backend is the application layer behind GiftGen, a 3D gift generation experience built around text prompts, asynchronous generation jobs, and shareable results.

This repository contains the API, the background worker, the cleanup job, and the Helm chart used to deploy the backend into Kubernetes. In production, it sits between the frontend and the rest of the platform. It accepts user requests, manages job state, talks to external generation services, stores metadata in Postgres, stores generated assets in S3, and exposes the data the frontend needs to render finished gifts.

## Related Repositories

- [giftgen-frontend](https://github.com/mitkan191003/giftgen-frontend) for the web application
- [giftgen-infra](https://github.com/mitkan191003/giftgen-infra) for AWS, Kubernetes, delivery, DNS, and environment setup

## Role In The Architecture

The backend is responsible for turning a user request into a durable generation workflow.

A typical request moves through the system like this:

1. The frontend sends a creation request to the API.
2. The API validates the request, writes metadata to Postgres, and creates a queued generation job.
3. The worker picks up that job and calls the generation provider.
4. Generated files are stored in S3 or local storage, depending on environment.
5. The API exposes the finished creation, asset, and share data back to the frontend.

The codebase is organized as a modular backend that is deployed as two runtime workloads:

- an API service for user-facing HTTP traffic
- a worker for asynchronous generation jobs
- a scheduled cleanup job for data retention

That keeps the business rules in one place while allowing the API and background processing to scale separately.

## What’s In This Repository

- `app/` for the FastAPI application, worker logic, models, services, and observability code
- `alembic/` for database migrations
- `helm/` for the Kubernetes chart used in deployed environments
- `Dockerfile.api` and `Dockerfile.worker` for container builds
- `buildspec.*.yml` for the AWS delivery pipeline
- `tests/` for backend test coverage

## Running It Locally

The backend is set up to be usable without standing up the full cloud environment first. Local development defaults to SQLite, local file storage, and development auth.

### Requirements

- Python 3.12
- a virtual environment tool

### Basic Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

Start the API:

```bash
uvicorn app.main:app --reload
```

If you want to process queued jobs locally, run the worker in a second shell:

```bash
source venv/bin/activate
python -m app.workers.generation --watch
```

## Configuration

Most local configuration lives in `.env`. The main pieces are:

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

This repository contains the application artifacts needed for deployment, but it does not provision the platform by itself.

In deployed environments:

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
