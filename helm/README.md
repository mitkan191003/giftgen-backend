# GiftGen Helm

`helm/giftgen` is the first deployable backend chart.

Terraform bootstrap is expected to supply:

- image repositories and tags
- Cognito settings
- the RDS, Modal, and OpenAI secret ARNs
- the S3 assets bucket name
- the IRSA role annotation for the runtime service account

The chart currently manages:

- API deployment and service
- worker deployment
- cleanup `CronJob`
- pre-sync Alembic migration `Job`
- API `Ingress`

The chart does not yet install AWS Load Balancer Controller. The `Ingress` resource is already in place so that controller can be added in the next infra pass without reshaping the chart.
