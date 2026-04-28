"""ADK agent for the Clinical Research Assistant (HTTP mode).

This agent talks to a deployed MCP server on Cloud Run. Two things
are different from the stdio version:

  1. We use StreamableHTTPConnectionParams (not Stdio).
  2. We mint a Google ID token and put it in the Authorization
     header so Cloud Run will let us in (since the service is
     deployed with --no-allow-unauthenticated).

The MCP server URL comes from the MCP_SERVER_URL env var. Locally
you `export` it from `gcloud run services describe ...`. In
production you pass it via `adk deploy --env_vars=MCP_SERVER_URL=...`.
"""
import os

import google.auth.transport.requests
from google.oauth2 import id_token

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StreamableHTTPConnectionParams,
)


# 1. Read the deployed MCP server URL.
#    Set this with: export MCP_SERVER_URL=$(gcloud run services
#    describe clinical-mcp --region=$REGION --format='value(status.url)')
MCP_URL = os.environ["MCP_SERVER_URL"]


# 2. Mint a Google ID token for the calling identity. The audience
#    MUST be the bare Cloud Run URL (no /mcp suffix), because that
#    is the audience Cloud Run validates against. fetch_id_token
#    finds credentials via Application Default Credentials.
auth_req = google.auth.transport.requests.Request()
token = id_token.fetch_id_token(auth_req, MCP_URL)


# 3. Point MCPToolset at the deployed /mcp endpoint and pass the
#    token in the Authorization header.
tools = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=f"{MCP_URL}/mcp",
        headers={"Authorization": f"Bearer {token}"},
    )
)


root_agent = LlmAgent(
    name="clinical_research_assistant",
    model="gemini-2.5-flash",
    description=(
        "A clinical research assistant that can look up clinical "
        "guidelines, FDA drug labels, and general medical "
        "background from Wikipedia."
    ),
    instruction="""
You help clinicians prepare for visits and help patients understand
their medications. You have three tools available:

  1. wikipedia_search           - background on any topic
  2. lookup_clinical_guideline  - clinical guideline summaries
  3. lookup_drug_info           - FDA drug label data (indications,
                                   dosing, warnings)

Pick the right tool for each request. If a question has multiple
parts, call multiple tools and combine the results. Always cite
which source you used (Wikipedia, USPSTF/CDC guideline, FDA label).

When the question sounds patient-facing (first person, plain
language, asking what a medication does or how to take it), drop
the clinical jargon and explain things simply. When the question
sounds clinician-facing (asking about screening criteria, risk
factors, dosing), keep the technical terms intact.

Never make up clinical information. If a tool returns "no result",
say so plainly.
""",
    tools=[tools],
)
