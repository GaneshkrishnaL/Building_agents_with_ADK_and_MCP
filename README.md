# Buidling ADK agents with MCP via Stdio and http

A clinical research assistant built with Google ADK and MCP. It can
brief a clinician before a patient visit and explain medications to
a patient in plain language. Three tools, all using public APIs that
need no API key:

1. `wikipedia_search` — Wikipedia REST API
2. `lookup_clinical_guideline` — bundled USPSTF/CDC summaries
3. `lookup_drug_info` — openFDA drug label endpoint

The same agent is built twice with the same code structure so you can
compare both transports side by side:

- `agent_stdio/` — for local development. The MCP server runs as a
  child process and the agent talks to it over stdin/stdout.
- `agent_http/` — for production. The MCP server runs on Cloud Run
  and the agent calls it over HTTPS with an ID token.

## Folder layout

```
clinical_research_assistant/
├─ .env.example
├─ .gitignore
├─ test_local.py              # programmatic smoke test for stdio
├─ agent_stdio/
│  ├─ __init__.py
│  ├─ agent.py                # uses StdioConnectionParams
│  ├─ mcp_server.py           # the three tools
│  └─ requirements.txt
└─ agent_http/
   ├─ __init__.py
   ├─ agent.py                # uses StreamableHTTPConnectionParams
   ├─ deploy_mcp.sh           # build + deploy MCP to Cloud Run
   ├─ deploy_agent.sh         # deploy agent to Agent Engine
   ├─ requirements.txt
   └─ mcp_server/
      ├─ server.py            # same tools, HTTP transport
      ├─ Dockerfile
      └─ requirements.txt
```

## Setup (one-time)

1. Authenticate with gcloud and set your project.

   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. Enable the APIs you'll need.

   ```bash
   gcloud services enable \
       aiplatform.googleapis.com \
       run.googleapis.com \
       cloudbuild.googleapis.com \
       artifactregistry.googleapis.com \
       iamcredentials.googleapis.com
   ```

3. Copy the env template and fill in your values.

   ```bash
   cp .env.example .env
   # edit .env: set PROJECT_ID, REGION, GOOGLE_CLOUD_PROJECT
   ```

4. Install the local dependencies.

   ```bash
   pip install -r agent_stdio/requirements.txt
   ```

## Test locally (stdio mode)

Two ways to test, pick whichever you prefer.

**A. Web playground.** Run from this folder (the parent of
`agent_stdio/`):

```bash
adk web
```

Open http://127.0.0.1:8000 in a browser, pick
`clinical_research_assistant` from the dropdown, and try a prompt:

> Brief me on type 2 diabetes screening guidelines. Then explain
> metformin to a patient who is starting it for the first time.

You should see the agent pick `lookup_clinical_guideline` for the
first half and `lookup_drug_info` for the second.

**B. Programmatic test.** Same idea, no browser:

```bash
python3 test_local.py
```

It runs two prompts (one clinician-facing, one patient-facing) and
prints the agent's final responses. If both come back with real
content, the local stack is working.

## Deploy to Google Cloud

The deploy is a two-step dance: ship the MCP server to Cloud Run
first, then ship the agent to Agent Engine pointing at the deployed
URL.

### 1. Deploy the MCP server to Cloud Run

```bash
cd agent_http
export PROJECT_ID=your-project-id
export REGION=us-central1

bash deploy_mcp.sh
```

This creates a dedicated `mcp-server-sa` service account, builds the
container from `mcp_server/Dockerfile`, and deploys to Cloud Run with
`--no-allow-unauthenticated` (no public access).

When it finishes it prints the service URL. Export it so the agent
can find the deployed server:

```bash
export MCP_SERVER_URL=https://clinical-mcp-xxxxx-uc.a.run.app
```

### 2. Deploy the agent to Agent Engine

From the project root (`clinical_research_assistant/`):

```bash
cd ..   # back to clinical_research_assistant/
bash agent_http/deploy_agent.sh
```

This creates a separate `agent-sa` service account, binds it to
`roles/run.invoker` on the Cloud Run service, then runs
`adk deploy agent_engine` with the agent SA attached and
`MCP_SERVER_URL` passed as an env var.

When it finishes you'll have a Reasoning Engine resource. List it:

```bash
gcloud ai reasoning-engines list --region=$REGION
```

The console URL printed by `adk deploy` opens a live playground for
the deployed agent.

### 3. Connect to Gemini Enterprise (optional)

Once the agent is on Agent Engine you can surface it through Gemini
Enterprise:

1. Note the Reasoning Engine resource name from the list above.
2. In the Gemini Enterprise console, add a connection of type
   "Reasoning Engine" and paste the resource name.
3. Bind the Gemini Enterprise service identity (provided by Google,
   shown in the console) with `roles/aiplatform.reasoningEngineUser`
   on the engine.

End users now see the clinical research assistant in their Workspace
agents list.

## The IAM model

Two service accounts, one binding. That's the whole security story.

| Service account | Attached to | Roles |
|---|---|---|
| `mcp-server-sa` | Cloud Run service (the MCP server) | Whatever the tools need. For this demo: nothing extra (Wikipedia and openFDA are public). |
| `agent-sa` | Reasoning Engine (the ADK agent) | `roles/run.invoker` on the MCP Cloud Run service. Nothing else. |

If the agent ever gets compromised, it can only call `/mcp`. It
can't read your databases, hit Secret Manager, or talk to any
downstream API. Blast radius is exactly one HTTP endpoint.

## Troubleshooting

| Error | Fix |
|---|---|
| `ValueError: No API key was provided` | Set `GOOGLE_GENAI_USE_VERTEXAI=TRUE` in `.env`. |
| `401 Unauthorized` from `/mcp` | The ID token audience is wrong (must be the bare Cloud Run URL, no `/mcp`). |
| `403 Forbidden` from `/mcp` | The agent SA is missing `roles/run.invoker`. Re-run `deploy_agent.sh`. |
| `KeyError: 'MCP_SERVER_URL'` | You forgot to `export MCP_SERVER_URL=...` after running `deploy_mcp.sh`. |
| `404 Publisher Model not found` | The `gemini-2.5-flash` model isn't enabled in your region. Try `gemini-2.0-flash` in `agent.py`. |
| `adk deploy` build error | A package in `requirements.txt` doesn't exist on PyPI. Run `pip install -r agent_http/requirements.txt` locally first to confirm. |
| Tools don't show up in `adk web` | Run `adk web` from the parent folder of `agent_stdio/`, not from inside it. |
