# Backend Architecture

## Service Boundaries

This repo keeps a modular monolith at the code level but deploys two workloads:

- API deployment
  - Handles authenticated HTTP traffic
  - Owns thread, creation, share, and job status APIs
  - Produces queued generation jobs
- Worker deployment
  - Polls queued jobs
  - Calls Modal
  - Stores artifacts
  - Updates job and creation state

This keeps the data model and business rules in one place while still separating latency-sensitive API traffic from long-running generation work.

## Auth Strategy

Production auth should be Cognito-backed JWT validation. Each deployed environment should use its own Cognito configuration and stable frontend origin. This scaffold currently exposes a development-only identity dependency that auto-provisions a user from `X-Dev-User-Email`. That keeps local iteration unblocked without contaminating the production design.

## Persistence

Canonical relational entities:

- `users`
- `chat_threads`
- `chat_messages`
- `creations`
- `generation_jobs`
- `assets`
- `shares`

The job table is the durable state machine. Even if SQS is introduced later for dispatch, job truth still lives in Postgres.

## Async Model

The intended production flow is:

1. API creates `creations` and `generation_jobs` rows in one transaction.
2. API publishes the job ID to a queue.
3. Worker claims the job, marks it `running`, calls Modal, stores artifacts, and marks completion.
4. Frontend polls job status or upgrades to SSE later.

This scaffold ships the durable parts first: schemas, statuses, and a worker that can process queued jobs directly. The queue transport can be added without reshaping the domain model.

## Guardrails

Prompt inspection happens before:

- chat message persistence when the message is obviously malicious
- creation submission

The current implementation is heuristic and intentionally conservative. It exists to create the right control point, not to be the final moderation system.

## Provider Adapters

The service layer is split behind adapters:

- `PromptRefiner`: placeholder for OpenAI-backed prompt refinement
- `ModalGenerationClient`: HTTP adapter for the existing Modal service
- `AssetStore`: local filesystem or S3-backed artifact persistence

These boundaries let the worker stay stable when provider details change.

## Deployment Shape

The first GitOps deployment slice packages the backend as:

- an API image
- a worker image
- one Helm chart that defines API, worker, migrations, cleanup, and ingress

Runtime configuration comes from Terraform outputs and AWS Secrets Manager instead of handwritten Kubernetes secrets:

- Terraform bootstrap creates an IRSA role for the runtime service account
- the chart passes secret ARNs as environment variables
- the application resolves database, Modal, and OpenAI settings from Secrets Manager at startup
