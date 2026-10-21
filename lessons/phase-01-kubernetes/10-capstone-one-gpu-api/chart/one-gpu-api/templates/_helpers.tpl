{{- define "one-gpu-api.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "one-gpu-api.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "one-gpu-api.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | quote }}
app.kubernetes.io/name: {{ include "one-gpu-api.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: open-model-course
lesson.open-model-course/id: "10"
{{- end }}

{{- define "one-gpu-api.selectorLabels" -}}
app.kubernetes.io/name: {{ include "one-gpu-api.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "one-gpu-api.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "one-gpu-api.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "one-gpu-api.image" -}}
{{- if .Values.image.digest }}
{{- printf "%s@%s" .Values.image.repository .Values.image.digest }}
{{- else }}
{{- printf "%s:%s" .Values.image.repository .Values.image.tag }}
{{- end }}
{{- end }}

{{- define "one-gpu-api.claimName" -}}
{{- if .Values.cache.persistence.existingClaim }}
{{- .Values.cache.persistence.existingClaim }}
{{- else }}
{{- include "one-gpu-api.fullname" . }}
{{- end }}
{{- end }}

{{- define "one-gpu-api.testImage" -}}
{{- if .Values.test.image.digest }}
{{- printf "%s@%s" .Values.test.image.repository .Values.test.image.digest }}
{{- else }}
{{- printf "%s:%s" .Values.test.image.repository .Values.test.image.tag }}
{{- end }}
{{- end }}
