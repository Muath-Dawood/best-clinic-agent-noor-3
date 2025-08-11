from __future__ import annotations
import os
from agents import Agent, FileSearchTool, RunResult


VS_KB = (os.getenv("VECTOR_STORE_ID_KB") or "").strip()


def _build_filesearch():
    return FileSearchTool(vector_store_ids=[VS_KB]) if VS_KB else None


def _scrub_files_phrasing(text: str) -> str:
    if not text:
        return ""
    ar = ("ملف", "ملفات", "مرفق", "مرفقات", "المرفوع")
    en = (
        "file",
        "files",
        "upload",
        "uploads",
        "attachment",
        "attachments",
        "document",
        "documents",
    )
    keep = []
    for ln in text.splitlines():
        low = ln.lower()
        if any(t in low for t in en):  # drop any line that mentions files
            continue
        if any(t in ln for t in ar):
            continue
        keep.append(ln)
    return "\n".join(keep).strip()


# The mini-agent that owns FileSearch (Noor won’t see FileSearch directly)
_kb_agent = Agent(
    name="ClinicKBAgent",
    instructions=(
        "You MUST call FileSearch tool and retrieve official clinic or medical facts"
        "(address/phones/services/doctors/prices/hours/policies/conditions/treatments) as per input query. "
        "Answer concisely in the user's language as short bullet points (max 10 points). "
        "Do NOT mention tools, files, documents, uploads, or citations."
    ),
    tools=[t for t in [_build_filesearch()] if t],
    model="gpt-4o-mini",
)


# as_tool with a custom extractor that returns clean text back to Noor
async def _extract_clean_text(run_result: RunResult) -> str:
    text = (run_result.final_output or "").strip()
    return _scrub_files_phrasing(text)


def kb_tool_for_noor():
    """Return the tool object to plug into Noor.tools, or [] if KB is not configured."""
    if not VS_KB:
        return []
    return [
        _kb_agent.as_tool(
            tool_name="get_clinic_facts",
            tool_description="Retrieve concise, grounded clinic and sexual health medical facts (address/phones/services/doctors/prices/hours/policies/conditions/treatments).",
            custom_output_extractor=_extract_clean_text,
        )
    ]
