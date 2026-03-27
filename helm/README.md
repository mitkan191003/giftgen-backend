# GiftGen Helm

`helm/giftgen` is the first deployable backend chart.

Terraform bootstrap is expected to supply:

- image repositories
- Cognito settings
- the RDS, Modal, and OpenAI secret ARNs
- the S3 assets bucket name
- the IRSA role annotation for the runtime service account

Environment-specific placeholder image tags live in values files such as:

- `helm/giftgen/values-dev.yaml`
- `helm/giftgen/values-prod.yaml`

For the pipeline-managed dev path, ArgoCD overrides those tags with the source commit SHA at deploy time.

The chart currently manages:

- API deployment and service
- worker deployment
- cleanup `CronJob`
- Alembic migration `Job` ordered before the API and worker with Argo sync waves
- API `Ingress`

The chart expects the cluster bootstrap layer to install AWS Load Balancer Controller and ExternalDNS.
