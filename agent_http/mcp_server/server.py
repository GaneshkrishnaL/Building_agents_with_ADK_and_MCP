"""MCP server for the Clinical Research Assistant (HTTP transport).

Same three tools as the stdio version. The only difference is the
last few lines: `mcp.run(transport="streamable-http", ...)` instead
of `mcp.run()`. This makes the server listen on an HTTP port at
/mcp instead of communicating over stdin/stdout.

Designed to run on Cloud Run, which provides the PORT env var.
"""
import os
import requests
from fastmcp import FastMCP

mcp = FastMCP("clinical-research-assistant")


GUIDELINES = {
    "type 2 diabetes screening": (
        "USPSTF (2021): screen adults 35 to 70 who are overweight "
        "or obese for prediabetes and type 2 diabetes. Repeat every "
        "3 years if the result is normal."
    ),
    "hypertension": (
        "ACC/AHA (2017): adults with stage 1 hypertension and a "
        "10-year ASCVD risk of 10% or higher should start "
        "antihypertensive therapy in addition to lifestyle changes."
    ),
    "statin therapy": (
        "USPSTF (2022): adults 40 to 75 with at least one CVD risk "
        "factor and a 10-year ASCVD risk of 10% or higher should be "
        "offered a statin."
    ),
    "colorectal cancer screening": (
        "USPSTF (2021): screen adults 45 to 75 for colorectal "
        "cancer. Options include colonoscopy every 10 years, FIT "
        "every year, or stool DNA every 1 to 3 years."
    ),
    "tobacco cessation": (
        "USPSTF (2021): ask all adults about tobacco use. Provide "
        "behavioral interventions and FDA-approved pharmacotherapy "
        "to adults who use tobacco."
    ),
}


@mcp.tool()
def wikipedia_search(topic: str) -> str:
    """Look up a short Wikipedia summary for any topic.

    Use this when the user asks for background on a clinical trial,
    condition, drug class, or any general medical concept that is
    not specifically covered by the other two tools.

    Args:
        topic: The article title to look up, for example
               "SPRINT trial" or "metformin".
    """
    url = (
        "https://en.wikipedia.org/api/rest_v1/page/summary/"
        + requests.utils.quote(topic)
    )
    try:
        r = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "adk-mcp-demo/1.0"},
        )
    except requests.RequestException as e:
        return f"Wikipedia request failed: {e}"

    if r.status_code != 200:
        return f"No Wikipedia article found for '{topic}'."
    data = r.json()
    return data.get("extract", "No summary available.")


@mcp.tool()
def lookup_clinical_guideline(topic: str) -> str:
    """Return a short, plain-language clinical guideline summary.

    Use this when the user asks how to screen, diagnose, or manage
    a condition, or asks what the guideline says about something.

    Args:
        topic: A short topic name, for example
               "type 2 diabetes screening" or "hypertension".
    """
    key = topic.strip().lower()
    if key in GUIDELINES:
        return GUIDELINES[key]
    matches = [k for k in GUIDELINES if key in k or k in key]
    if matches:
        return GUIDELINES[matches[0]]
    return (
        f"No guideline on file for '{topic}'. "
        "Available topics: " + ", ".join(GUIDELINES)
    )


@mcp.tool()
def lookup_drug_info(drug_name: str) -> str:
    """Look up indications, dosing, and warnings for a drug.

    Backed by the openFDA drug label endpoint. No API key required.
    Use this when the user asks what a medication is for, how to
    take it, or what side effects to watch for.

    Args:
        drug_name: Generic or brand name, for example "metformin"
                   or "lisinopril".
    """
    url = "https://api.fda.gov/drug/label.json"
    try:
        r = requests.get(
            url,
            timeout=15,
            params={
                "search": f"openfda.generic_name:{drug_name}",
                "limit": 1,
            },
        )
    except requests.RequestException as e:
        return f"openFDA request failed: {e}"

    if r.status_code != 200:
        return f"openFDA lookup failed for '{drug_name}'."
    results = r.json().get("results") or []
    if not results:
        return f"No FDA label found for '{drug_name}'."

    label = results[0]
    parts = []
    for field, heading in [
        ("indications_and_usage", "Indications"),
        ("dosage_and_administration", "Dosing"),
        ("warnings", "Warnings"),
    ]:
        text = label.get(field)
        if text:
            parts.append(f"{heading}: {text[0][:400]}")
    return "\n\n".join(parts) if parts else "Label found but empty."


if __name__ == "__main__":
    # Cloud Run injects PORT. Locally we default to 8080.
    port = int(os.environ.get("PORT", 8080))
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
        path="/mcp",
    )
