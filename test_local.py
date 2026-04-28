"""Quick programmatic smoke test for the stdio agent.

Run this from the clinical_research_assistant/ folder:

    python3 test_local.py

It loads .env, picks up the agent_stdio package, and asks the agent
two questions: one clinician-facing and one patient-facing. The
agent should call lookup_clinical_guideline and lookup_drug_info
respectively. If you see real text back from both, the whole local
stack works.
"""
import asyncio
from dotenv import load_dotenv

load_dotenv()  # picks up GOOGLE_GENAI_USE_VERTEXAI etc.

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agent_stdio.agent import root_agent


PROMPTS = [
    "Brief me on type 2 diabetes screening guidelines.",
    "What is metformin used for and what should I watch out for?",
]


async def main():
    sessions = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="clinical_test",
        session_service=sessions,
    )

    for i, prompt in enumerate(PROMPTS, start=1):
        session_id = f"test_session_{i}"
        await sessions.create_session(
            app_name="clinical_test",
            user_id="local_tester",
            session_id=session_id,
        )

        msg = types.Content(
            role="user",
            parts=[types.Part(text=prompt)],
        )

        print("=" * 70)
        print(f"PROMPT {i}: {prompt}")
        print("=" * 70)

        async for event in runner.run_async(
            user_id="local_tester",
            session_id=session_id,
            new_message=msg,
        ):
            if event.is_final_response():
                print(event.content.parts[0].text)
                print()


if __name__ == "__main__":
    asyncio.run(main())
