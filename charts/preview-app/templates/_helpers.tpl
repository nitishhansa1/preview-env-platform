{{/*
==============================================================================
_helpers.tpl - Reusable Template Helpers
==============================================================================
Why: DRY principle. These named templates produce consistent names and labels
     across every Kubernetes resource so selectors always match.
==============================================================================
*/}}

{{/*
Produce a truncated, DNS-safe release name (max 63 chars).
Used as the prefix for every resource name in this release.
*/}}
{{- define "preview-app.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Chart name used in labels (chart: preview-app-0.1.0)
*/}}
{{- define "preview-app.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels applied to every resource.
Includes: pr-number for easy `kubectl get all -l pr-number=42` queries.
*/}}
{{- define "preview-app.labels" -}}
helm.sh/chart: {{ include "preview-app.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
preview.env/pr-number: {{ .Values.prNumber | quote }}
preview.env/git-sha: {{ .Values.gitSha | quote }}
{{- end }}

{{/*
Selector labels used in Deployment.spec.selector and Service.spec.selector.
Only stable labels that never change between upgrades.
*/}}
{{- define "preview-app.selectorLabels" -}}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Build the DATABASE_URL for the backend, pointing to the headless Postgres service.
Format: postgresql+psycopg2://<user>:<password>@<host>:<port>/<db>
The host is the headless service name in the same namespace.
*/}}
{{- define "preview-app.databaseURL" -}}
{{- printf "postgresql+psycopg2://%s:$(DB_PASSWORD)@%s-postgres:%d/%s"
    .Values.postgres.user
    (include "preview-app.fullname" .)
    (5432 | int)
    .Values.postgres.db }}
{{- end }}
