# Backend Architecture

## Overview

The backend is the application core of GiftGen. It owns authenticated API traffic, generation job state, asset metadata, sharing, and background processing.

This repository is deployed as multiple workloads from one codebase:

- an API service for HTTP traffic
- a generation worker for asynchronous model creation
- a cleanup worker for scheduled data retention tasks

The code is kept together because the API, worker, and cleanup logic all depend on the same data model and the same provider integrations.

## Runtime Responsibilities

### API

The API is responsible for:

- user identity resolution
- thread and message APIs
- creation submission
- job status reads
- share creation and revocation
- private and public asset delivery
- health and readiness endpoints

### Generation Worker

The generation worker is responsible for:

- selecting queued generation jobs from Postgres
- moving jobs through their lifecycle
- calling the generation provider
- storing generated files
- creating asset records
- marking creations as ready or failed

### Cleanup Worker

The cleanup worker is responsible for:

- expiring stale queued or running jobs
- removing expired asset files
- deleting old failed or deleted creations according to retention rules

## Data Model

The main relational entities are:

- `users`
- `chat_threads`
- `chat_messages`
- `creations`
- `generation_jobs`
- `assets`
- `shares`

`generation_jobs` is the durable record of asynchronous work. The worker reads queued jobs from the database and updates them in place as work progresses.

## Authentication

The backend supports two auth modes:

- `development`
- `cognito`

In development mode, a caller can identify itself with `X-Dev-User-Email`. In deployed environments, the API validates Cognito bearer tokens and maps requests to application users by Cognito subject.

## Generation Flow

The generation flow is:

1. the API accepts a creation request
2. the API writes a `creation` and a queued `generation_job`
3. the worker claims the next queued job
4. the worker calls the generation provider
5. generated files are stored and linked to the creation
6. the creation moves to `ready` or `failed`
7. the frontend polls job status and then loads the finished gift

## Providers And Services

The backend isolates external integrations behind service classes:

- `PromptRefiner` shapes user prompts into generation-ready text
- `ModalGenerationClient` calls the model endpoint
- `AssetStore` writes and deletes stored assets

That separation keeps provider-specific behavior out of the API and worker flow.

## Storage

The backend supports two storage modes:

- local filesystem storage for local development
- S3-backed storage for deployed environments

Asset metadata always lives in Postgres. The binary files live either on disk or in S3 depending on configuration.

## Deployment Shape

The backend is packaged as:

- an API container image
- a worker container image
- one Helm chart that defines the API, worker, migrations job, cleanup job, service account, config, and ingress

Runtime configuration is passed in through environment variables, Terraform-managed values, and AWS Secrets Manager.

## Observability

The backend emits:

- structured application logs
- request correlation IDs
- CloudWatch Embedded Metric Format metrics
- optional Sentry events

That applies across API traffic, background generation work, and cleanup jobs.
