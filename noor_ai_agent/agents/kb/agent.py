"""
Knowledge base agent for retrieving clinic information.
"""

import os
from typing import List
from agents import Agent, FileSearchTool, RunResult

from ...config import get_settings


class KnowledgeBaseAgent:
    """Agent for retrieving clinic knowledge from vector store."""

    def __init__(self):
        self.settings = get_settings()
        self.vector_store_id = self.settings.vector_store_id_kb
        self.agent = self._create_agent()

    def _create_agent(self) -> Agent:
        """Create the knowledge base agent."""
        tools = []

        if self.vector_store_id:
            file_search_tool = FileSearchTool(vector_store_ids=[self.vector_store_id])
            tools.append(file_search_tool)

        return Agent(
            name="ClinicKBAgent",
            instructions=(
                "You MUST call the FileSearch tool and retrieve official clinic or medical facts "
                "(address/phones/services/doctors/prices/hours/policies/conditions/treatments) as per input query. "
                "Answer concisely in the user's language as short bullet points (no more than 10 points). "
                "Present answers plainly. **Never mention tools, search, "files," "documents," "uploads," or "vector stores."**"
                "If a fact isn't available, don't guess—offer to confirm or apologize."
            ),
            tools=tools,
            model="gpt-4o-mini",
        )

    def get_tools(self) -> List:
        """Get tools for integration with other agents."""
        if not self.vector_store_id:
            return []

        return [
            self.agent.as_tool(
                tool_name="get_clinic_facts",
                tool_description="Retrieve concise, grounded clinic and sexual health medical facts (address/phones/services/doctors/prices/hours/policies/conditions/treatments).",
                custom_output_extractor=self._extract_clean_text,
            )
        ]

    def _extract_clean_text(self, run_result: RunResult) -> str:
        """Extract clean text from knowledge base search results."""
        text = (run_result.final_output or "").strip()
        return self._scrub_files_phrasing(text)

    def _scrub_files_phrasing(self, text: str) -> str:
        """Remove file-related phrasing from text."""
        if not text:
            return ""

        ar_keywords = ("ملف", "ملفات", "مرفق", "مرفقات", "المرفوع")
        en_keywords = (
            "file", "files", "upload", "uploads",
            "attachment", "attachments", "document", "documents"
        )

        lines = []
        for line in text.splitlines():
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in en_keywords):
                continue
            if any(keyword in line for keyword in ar_keywords):
                continue
            lines.append(line)

        return "\n".join(lines).strip()
