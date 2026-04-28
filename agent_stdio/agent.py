"""ADK agent for the Clinical Research Assistant (stdio mode).

This module exposes `root_agent`, which is what ADK looks for at
import time. Do NOT wrap the agent in an async function or factory;
Agent Engine imports this name during bundling and a wrapped
definition will fail to load.
"""
import os

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
)
from mcp import StdioServerParameters


# Resolve the absolute path of this file so the agent works no matter
# where you run `adk web` from.
HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)


tools = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python3",
            # `-m agent_stdio.mcp_server` runs the server as a module
            # so its imports resolve correctly. cwd is set to the
            # parent of agent_stdio/ so Python can find the package.
            args=["-m", "agent_stdio.mcp_server"],
            cwd=PARENT,
        )
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
