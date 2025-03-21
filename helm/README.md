# GiftGen Helm

`helm/giftgen` is the first deployable backend chart.

Terraform bootstrap is expected to supply:

- image repositories
- Cognito settings
- the RDS, Modal, and OpenAI secret ARNs
- the S3 assets bucket name
- the IRSA role annotation for the runtime service account

Environment-specific image tags now live in Git-managed values files such as:

- `helm/giftgen/values-dev.yaml`

The chart currently manages:

- API deployment and service
- worker deployment
- cleanup `CronJob`
- pre-sync Alembic migration `Job`
- API `Ingress`

The chart expects the cluster bootstrap layer to install AWS Load Balancer Controller and ExternalDNS.
