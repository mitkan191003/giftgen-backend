{{- define "giftgen.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "giftgen.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "giftgen.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "giftgen.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" -}}
{{- end -}}

{{- define "giftgen.labels" -}}
helm.sh/chart: {{ include "giftgen.chart" . }}
app.kubernetes.io/name: {{ include "giftgen.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "giftgen.selectorLabels" -}}
app.kubernetes.io/name: {{ include "giftgen.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "giftgen.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (printf "%s-runtime" (include "giftgen.fullname" .)) .Values.serviceAccount.name -}}
{{- else -}}
{{- required "serviceAccount.name is required when serviceAccount.create is false" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "giftgen.apiImage" -}}
{{- $repo := required "api.image.repository is required" .Values.api.image.repository -}}
{{- printf "%s:%s" $repo .Values.api.image.tag -}}
{{- end -}}

{{- define "giftgen.workerImage" -}}
{{- $repo := required "worker.image.repository is required" .Values.worker.image.repository -}}
{{- printf "%s:%s" $repo .Values.worker.image.tag -}}
{{- end -}}

{{- define "giftgen.cleanupImage" -}}
{{- $repo := default .Values.worker.image.repository .Values.cleanup.image.repository -}}
{{- $tag := default .Values.worker.image.tag .Values.cleanup.image.tag -}}
{{- if or (eq $repo "") (eq $tag "") -}}
{{- fail "cleanup image repository and tag could not be resolved" -}}
{{- end -}}
{{- printf "%s:%s" $repo $tag -}}
{{- end -}}

{{- define "giftgen.migrationsImage" -}}
{{- $repo := default .Values.api.image.repository .Values.migrations.image.repository -}}
{{- $tag := default .Values.api.image.tag .Values.migrations.image.tag -}}
{{- if or (eq $repo "") (eq $tag "") -}}
{{- fail "migrations image repository and tag could not be resolved" -}}
{{- end -}}
{{- printf "%s:%s" $repo $tag -}}
{{- end -}}

