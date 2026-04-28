#!/usr/bin/env bash
# Deploy the MCP server to Cloud Run.
# Run from: clinical_research_assistant/agent_http/
#
# Required env vars (set them in your shell or in .env):
#   PROJECT_ID  - your GCP project ID
#   REGION      - e.g. us-central1
#
# What this script does:
#   1. Creates a dedicated mcp-server-sa service account (idempotent).
#   2. Builds the Docker image and deploys to Cloud Run.
#   3. Locks the service down so only authenticated callers can hit it.
#   4. Prints the service URL so you can `export MCP_SERVER_URL=...`.

set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID first: export PROJECT_ID=...}"
: "${REGION:?Set REGION first: export REGION=us-central1}"

SERVICE_NAME="clinical-mcp"
SERVER_SA_NAME="mcp-server-sa"
SERVER_SA="${SERVER_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "==> Creating service account ${SERVER_SA_NAME} (if missing)"
gcloud iam service-accounts create "${SERVER_SA_NAME}" \
    --display-name="MCP server" \
    --project="${PROJECT_ID}" \
    2>/dev/null || echo "    Already exists, continuing."

echo
echo "==> Deploying ${SERVICE_NAME} to Cloud Run in ${REGION}"
gcloud run deploy "${SERVICE_NAME}" \
    --source=./mcp_server \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --service-account="${SERVER_SA}" \
    --no-allow-unauthenticated \
    --memory=512Mi

echo
echo "==> Reading service URL"
MCP_SERVER_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format='value(status.url)')

echo
echo "Deployed: ${MCP_SERVER_URL}"
echo
echo "Run this in your shell so the agent can find it:"
echo "  export MCP_SERVER_URL=${MCP_SERVER_URL}"
