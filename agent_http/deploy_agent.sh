#!/usr/bin/env bash
# Deploy the ADK agent to Vertex AI Agent Engine (Reasoning Engine).
# Run from: clinical_research_assistant/
#
# Required env vars:
#   PROJECT_ID      - your GCP project ID
#   REGION          - e.g. us-central1
#   MCP_SERVER_URL  - from deploy_mcp.sh output
#
# What this script does:
#   1. Creates a dedicated agent-sa service account (idempotent).
#   2. Binds roles/run.invoker on the MCP Cloud Run service so the
#      agent can call /mcp.
#   3. Calls `adk deploy agent_engine` with the agent SA attached
#      and MCP_SERVER_URL passed in as an env var.

set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID first: export PROJECT_ID=...}"
: "${REGION:?Set REGION first: export REGION=us-central1}"
: "${MCP_SERVER_URL:?Set MCP_SERVER_URL first: export MCP_SERVER_URL=...}"

AGENT_SA_NAME="agent-sa"
AGENT_SA="${AGENT_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
MCP_SERVICE_NAME="clinical-mcp"

echo "==> Creating service account ${AGENT_SA_NAME} (if missing)"
gcloud iam service-accounts create "${AGENT_SA_NAME}" \
    --display-name="ADK agent" \
    --project="${PROJECT_ID}" \
    2>/dev/null || echo "    Already exists, continuing."

echo
echo "==> Granting agent SA invoke permission on ${MCP_SERVICE_NAME}"
gcloud run services add-iam-policy-binding "${MCP_SERVICE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --member="serviceAccount:${AGENT_SA}" \
    --role="roles/run.invoker"

echo
echo "==> Deploying agent to Agent Engine"
adk deploy agent_engine \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --display_name="Clinical Research Assistant" \
    --service_account="${AGENT_SA}" \
    --env_vars="MCP_SERVER_URL=${MCP_SERVER_URL}" \
    ./agent_http

echo
echo "Deploy complete. List your engines with:"
echo "  gcloud ai reasoning-engines list --region=${REGION}"
