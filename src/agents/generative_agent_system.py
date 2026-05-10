"""
Generative Multi-Agent Chat System
Combines trained ML with Hugging Face for conversational energy recommendations
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import json
from datetime import datetime
from typing import List, Dict
from dataclasses import dataclass
import random

from src.llm.energy_fine_tuner import (
    generate_fine_tuned_response,
    get_energy_fine_tuner
)


# ============================================================
# SHARED MODEL LOADER (Better architecture)
# ============================================================

_SHARED_MODEL = None
_SHARED_TOKENIZER = None
_SHARED_GENERATOR = None


def get_shared_generator(model_name="microsoft/DialoGPT-medium"):
    """
    Load model only once and reuse across agents.
    Saves huge RAM/VRAM.
    """
    global _SHARED_MODEL
    global _SHARED_TOKENIZER
    global _SHARED_GENERATOR

    if _SHARED_GENERATOR is None:
        print(f"Loading shared model: {model_name}")

        _SHARED_TOKENIZER = AutoTokenizer.from_pretrained(model_name)

        _SHARED_MODEL = AutoModelForCausalLM.from_pretrained(model_name)

        _SHARED_GENERATOR = pipeline(
            "text-generation",
            model=_SHARED_MODEL,
            tokenizer=_SHARED_TOKENIZER,
            pad_token_id=_SHARED_TOKENIZER.eos_token_id
        )

        print("Shared model loaded successfully.")

    return _SHARED_GENERATOR


# ============================================================
# DATA CLASS
# ============================================================

@dataclass
class AgentMessage:
    agent_name: str
    role: str
    content: str
    timestamp: str
    confidence: float = 0.8


# ============================================================
# GENERATIVE AGENT
# ============================================================

class GenerativeAgent:

    def __init__(
        self,
        name: str,
        role: str,
        model_name: str = "microsoft/DialoGPT-medium"
    ):
        self.name = name
        self.role = role
        self.model_name = model_name

        self.generator = get_shared_generator(model_name)

        self.personality_prompt = self._get_personality_prompt()

        self.use_fine_tuned = False
        self.fine_tuner = None

    # --------------------------------------------------------

    def _get_personality_prompt(self) -> str:

        personalities = {
            'analyst':
                "You are an Energy Data Analyst. "
                "You are precise, analytical, and data-driven.",

            'planner':
                "You are an Energy Planning Strategist. "
                "You think systematically and operationally.",

            'recommender':
                "You are an Energy Efficiency Expert. "
                "You provide practical recommendations.",

            'critic':
                "You are an Energy Systems Critic. "
                "You identify flaws and risks.",

            'synthesizer':
                "You are an Energy Solutions Synthesizer. "
                "You combine insights into strategic plans."
        }

        return personalities.get(
            self.role,
            "You are an Energy Management Assistant."
        )

    # --------------------------------------------------------

    def generate_response(
        self,
        context: str,
        conversation_history: List[str] = None
    ) -> str:

        # ----------------------------------------------------
        # Fine-tuned model path
        # ----------------------------------------------------

        if self.use_fine_tuned:

            try:

                if self.fine_tuner is None:
                    self.fine_tuner = get_energy_fine_tuner()

                context_summary = self._extract_context_summary(context)

                fine_tuned_response = generate_fine_tuned_response(
                    self.role,
                    context_summary
                )

                if (
                    fine_tuned_response
                    and len(fine_tuned_response.strip()) > 10
                ):

                    enhanced = self._enhance_response_with_insight(
                        fine_tuned_response,
                        context
                    )

                    return self._clean_response(enhanced)

            except Exception as e:
                print(f"Fine-tuned model error ({self.name}): {e}")

        # ----------------------------------------------------
        # Hugging Face generation path
        # ----------------------------------------------------

        try:

            prompt = self._build_enhanced_prompt(
                context,
                conversation_history
            )

            responses = self.generator(
                prompt,
                max_new_tokens=150,
                temperature=0.8,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.2,
                num_return_sequences=1
            )

            generated_text = responses[0]["generated_text"]

            response = generated_text[len(prompt):].strip()

            enhanced = self._enhance_response_with_insight(
                response,
                context
            )

            if enhanced.strip():
                return self._clean_response(enhanced)

            return self._enhanced_fallback_response(context)

        except Exception as e:

            print(f"Generation error ({self.name}): {e}")

            return self._enhanced_fallback_response(context)

    # --------------------------------------------------------

    def _build_enhanced_prompt(
        self,
        context: str,
        conversation_history: List[str] = None
    ) -> str:

        prompt = f"""
{self.personality_prompt}

CONTEXT:
{context}

INSTRUCTIONS:
1. Give professional analysis
2. Provide actionable insights
3. Explain reasoning clearly
4. Include implementation suggestions
5. Keep response detailed and realistic
"""

        if conversation_history:

            prompt += "\nRECENT CONVERSATION:\n"

            for msg in conversation_history[-2:]:
                prompt += f"- {msg}\n"

        prompt += f"\nResponse from {self.name}:"

        return prompt

    # --------------------------------------------------------

    def _enhance_response_with_insight(
        self,
        response: str,
        context: str
    ) -> str:

        if len(response.strip()) < 40:
            return self._add_domain_insight(response, context)

        if (
            "energy" in context.lower()
            and self.role == "recommender"
        ):
            response = self._add_energy_specifics(response)

        if (
            "recommendation" in context.lower()
            or "action" in context.lower()
        ):
            response = self._add_implementation_steps(response)

        return response

    # --------------------------------------------------------

    def _add_domain_insight(
        self,
        response: str,
        context: str
    ) -> str:

        building_id = self._extract_building_id(context)

        if self.role == "analyst":

            return (
                f"{response} "
                f"Historical analysis for {building_id} indicates "
                f"consumption deviations likely tied to HVAC "
                f"inefficiencies and occupancy fluctuations."
            )

        elif self.role == "recommender":

            return (
                f"{response} "
                f"Recommended actions for {building_id} include "
                f"HVAC optimization, smart scheduling, and "
                f"LED retrofitting with expected savings of 15-25%."
            )

        elif self.role == "planner":

            return (
                f"{response} "
                f"Implementation should follow phased deployment "
                f"with monitoring checkpoints and ROI evaluation."
            )

        return (
            f"{response} "
            f"This evaluation follows modern energy management "
            f"best practices."
        )

    # --------------------------------------------------------

    def _add_energy_specifics(self, response: str) -> str:

        return (
            f"{response} "
            f"Similar facilities achieved 20-30% savings using "
            f"building automation systems and predictive maintenance."
        )

    # --------------------------------------------------------

    def _add_implementation_steps(self, response: str) -> str:

        return (
            f"{response} "
            f"Implementation steps include baseline assessment, "
            f"technology deployment, pilot testing, monitoring, "
            f"and optimization."
        )

    # --------------------------------------------------------

    def _extract_building_id(self, context: str) -> str:

        for line in context.split("\n"):

            if "B00" in line:

                try:
                    return "B00" + line.split("B00")[1].split()[0]

                except Exception:
                    return "B001"

        return "B001"

    # --------------------------------------------------------

    def _enhanced_fallback_response(self, context: str) -> str:
        """
        Detailed fallback response.
        """

        building_id = self._extract_building_id(context)

        if self.role == "analyst":

            return f"""
Energy analysis for {building_id} reveals abnormal consumption
patterns exceeding baseline expectations by significant margins.

Primary investigation areas include:
- HVAC system inefficiencies
- Equipment scheduling issues
- Occupancy-related consumption spikes
- Sensor calibration problems

Data suggests the need for real-time monitoring and anomaly tracking.
"""

        elif self.role == "recommender":

            return f"""
Recommended optimization strategy for {building_id}:

Phase 1:
- Smart thermostats
- LED lighting upgrades
- HVAC schedule optimization

Phase 2:
- Building automation systems
- Predictive maintenance
- Energy analytics dashboard

Expected impact:
20-30% reduction in energy usage with 2-4 year ROI.
"""

        elif self.role == "planner":

            return f"""
Strategic implementation plan for {building_id}:

Short-term:
- Energy audit
- Baseline establishment
- Quick-win improvements

Medium-term:
- Infrastructure modernization
- Automation integration

Long-term:
- Renewable integration
- Net-zero readiness
- Continuous optimization
"""

        return f"""
Comprehensive energy strategy for {building_id}
requires technology modernization, operational
optimization, and continuous monitoring.

Expected benefits include reduced operating costs,
improved sustainability performance, and enhanced
system reliability.
"""

    # --------------------------------------------------------

    def _extract_context_summary(self, context: str) -> str:

        lines = context.split('\n')

        important = []

        for line in lines:

            if any(
                key in line.lower()
                for key in [
                    'building',
                    'consumption',
                    'energy',
                    'anomaly',
                    'deviation'
                ]
            ):
                important.append(line.strip())

        return " ".join(important[:2])

    # --------------------------------------------------------

    def _clean_response(self, response: str) -> str:

        response = response.strip()

        sentences = response.split('.')

        cleaned = []

        for sentence in sentences:

            sentence = sentence.strip()

            if len(sentence) > 10:
                cleaned.append(sentence)

        if cleaned:
            return '. '.join(cleaned[:4]) + '.'

        return response[:200]


# ============================================================
# GENERATIVE AGENT TEAM
# ============================================================

class GenerativeAgentTeam:

    def __init__(self):

        self.agents = {

            'analyst':
                GenerativeAgent("Data Analyst", "analyst"),

            'planner':
                GenerativeAgent("Strategic Planner", "planner"),

            'recommender':
                GenerativeAgent("Energy Expert", "recommender"),

            'critic':
                GenerativeAgent("Systems Critic", "critic"),

            'synthesizer':
                GenerativeAgent(
                    "Solution Synthesizer",
                    "synthesizer"
                )
        }

        self.conversation_history = []

    # --------------------------------------------------------

    def analyze_energy_anomaly(
        self,
        building_id: str,
        consumption_kwh: float,
        baseline: float,
        deviation_pct: float,
        anomaly_context: str = ""
    ) -> List[AgentMessage]:

        print(f"Starting analysis for {building_id}")

        messages = []

        context = f"""
Energy Anomaly Analysis

Building: {building_id}
Current Consumption: {consumption_kwh:.1f} kWh
Baseline Consumption: {baseline:.1f} kWh
Deviation: {deviation_pct:.1f}%
Context: {anomaly_context}
"""

        workflow = [
            ("analyst", "Data Analyst"),
            ("planner", "Strategic Planner"),
            ("recommender", "Energy Expert"),
            ("critic", "Systems Critic"),
            ("synthesizer", "Solution Synthesizer")
        ]

        running_context = context

        for role_key, display_name in workflow:

            response = self.agents[role_key].generate_response(
                running_context,
                self._get_recent_messages()
            )

            message = AgentMessage(
                agent_name=display_name,
                role=role_key,
                content=response,
                timestamp=datetime.now().strftime("%H:%M:%S")
            )

            messages.append(message)

            self.conversation_history.append(
                f"{display_name}: {response}"
            )

            running_context += (
                f"\n\n{display_name} Response:\n{response}"
            )

        print("Analysis completed.")

        return messages

    # --------------------------------------------------------

    def _get_recent_messages(self) -> List[str]:

        return self.conversation_history[-10:]

    # --------------------------------------------------------

    def chat_with_user(
        self,
        user_message: str,
        building_context: str = ""
    ) -> str:

        intent = self._analyze_user_intent(user_message)

        role = self._select_agent_for_intent(intent)

        context = f"""
User Question: {user_message}

Building Context:
{building_context}

Intent:
{intent}
"""

        response = self.agents[role].generate_response(
            context,
            self._get_recent_messages()
        )

        response = self._add_response_variety(
            response,
            intent
        )

        self.conversation_history.append(
            f"User: {user_message}"
        )

        self.conversation_history.append(
            f"Assistant: {response}"
        )

        return response

    # --------------------------------------------------------

    def _analyze_user_intent(self, message: str) -> str:

        text = message.lower()

        if any(
            w in text for w in
            ["count", "number", "agents"]
        ):
            return "count_agents"

        elif any(
            w in text for w in
            ["execute", "action", "follow"]
        ):
            return "execute_action"

        elif any(
            w in text for w in
            ["save", "reduce", "efficiency"]
        ):
            return "energy_saving"

        elif any(
            w in text for w in
            ["what", "why", "how"]
        ):
            return "information"

        elif any(
            w in text for w in
            ["hello", "hi", "chat"]
        ):
            return "greeting"

        return "general"

    # --------------------------------------------------------

    def _select_agent_for_intent(self, intent: str) -> str:

        mapping = {
            "count_agents": "synthesizer",
            "execute_action": "planner",
            "energy_saving": "recommender",
            "information": "analyst",
            "greeting": "recommender",
            "general": "recommender"
        }

        return mapping.get(intent, "recommender")

    # --------------------------------------------------------

    def _add_response_variety(
        self,
        response: str,
        intent: str
    ) -> str:

        variations = {
            "count_agents": [
                "My system currently uses 5 specialized agents:",
                "The architecture contains 5 AI agents:"
            ],

            "execute_action": [
                "Executing coordinated agent workflow:",
                "Launching multi-agent execution:"
            ],

            "energy_saving": [
                "Energy optimization assessment:",
                "Efficiency recommendation summary:"
            ]
        }

        if len(response.strip()) < 30:

            prefix = random.choice(
                variations.get(intent, ["Analysis:"])
            )

            response = f"{prefix} {response}"

        return response

    # --------------------------------------------------------

    def get_suggestions(
        self,
        building_id: str,
        energy_profile: Dict
    ) -> List[str]:

        context = f"""
Building: {building_id}

Energy Profile:
{json.dumps(energy_profile, indent=2)}

Provide 3 energy optimization suggestions.
"""

        response = self.agents[
            'recommender'
        ].generate_response(context)

        suggestions = []

        for sentence in response.split('.'):

            sentence = sentence.strip()

            if len(sentence) > 20:
                suggestions.append(sentence)

            if len(suggestions) >= 3:
                break

        if suggestions:
            return suggestions

        return [
            "Conduct energy audits",
            "Optimize HVAC schedules",
            "Implement smart automation systems"
        ]


# ============================================================
# GLOBAL ACCESSORS
# ============================================================

_generative_team = None


def get_generative_team():

    global _generative_team

    if _generative_team is None:
        _generative_team = GenerativeAgentTeam()

    return _generative_team


# ============================================================
# MAIN INTERFACE
# ============================================================

def run_generative_analysis(
    building_id: str,
    consumption_kwh: float,
    baseline: float,
    deviation_pct: float,
    anomaly_context: str = ""
) -> List[Dict]:

    team = get_generative_team()

    messages = team.analyze_energy_anomaly(
        building_id,
        consumption_kwh,
        baseline,
        deviation_pct,
        anomaly_context
    )

    return [
        {
            "agent": msg.agent_name,
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp,
            "type": "generative_chat"
        }
        for msg in messages
    ]