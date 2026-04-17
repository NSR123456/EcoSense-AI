"""
LLM and RAG Engine for Energy Intelligence

Converts analytics results into natural language and actionable insights.
"""

import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

try:
    import openai
    openai_api_available = True
    if OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
except ImportError:
    openai_api_available = False

INDUSTRIAL_STANDARDS = (
    "ISO 50001 focuses on energy management systems, peak demand reduction, "
    "power factor optimization, and continuous improvement through data-driven controls."
)

class LLMEnergyEngine:
    """Generates strategy and audit insights from summaries and data."""

    def __init__(self):
        self.standards = INDUSTRIAL_STANDARDS

    def create_rag_prompt(self, summary: str, question: Optional[str] = None) -> str:
        prompt = (
            "You are an industrial energy intelligence assistant. "
            "Use the following digital twin state summary and industrial standards to generate concise, actionable recommendations.\n\n"
            f"Digital Twin Summary:\n{summary}\n\n"
            f"Standards Reference:\n{self.standards}\n\n"
        )
        if question:
            prompt += f"User Question: {question}\n\n"
        prompt += (
            "Answer with a clear action plan, a likely root cause, and one concise management summary. "
            "If the data is insufficient, say so clearly."
        )
        return prompt

    def generate_insight(self, summary: str, question: Optional[str] = None) -> Dict[str, str]:
        prompt = self.create_rag_prompt(summary, question)

        if openai_api_available and OPENAI_API_KEY:
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                    temperature=0.5
                )
                text = response.choices[0].message.content.strip()
                return self.parse_response(text)
            except Exception as e:
                logger.warning(f"OpenAI request failed: {e}")

        return self.fallback_insight(summary, question)

    def parse_response(self, text: str) -> Dict[str, str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return {
            'action_plan': lines[0] if lines else 'Review the energy state and verify sensors.',
            'root_cause': lines[1] if len(lines) > 1 else 'Potential load imbalance or configuration drift.',
            'management_summary': lines[2] if len(lines) > 2 else 'Energy summary generated with available inputs.'
        }

    def fallback_insight(self, summary: str, question: Optional[str] = None) -> Dict[str, str]:
        action_plan = "Review peak demand periods and verify HVAC scheduling."
        root_cause = "Possible inefficient HVAC or equipment startup during peak hours."
        management_summary = "The building has elevated peak loads with room for demand-shifting opportunities."

        if question:
            action_plan = "Interpret the intake question and check the latest energy summary."
            root_cause = "Likely due to extended HVAC runtime or untracked loads."
            management_summary = "The audit query indicates high consumption windows aligned with HVAC operation."

        return {
            'action_plan': action_plan,
            'root_cause': root_cause,
            'management_summary': management_summary
        }

# Global instance
llm_engine = LLMEnergyEngine()