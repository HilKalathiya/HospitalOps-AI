"""
HospitalOps AI — Agent Planner & Decision Synthesis (Milestone 5, Chunks 5.1 & 5.3).

Orchestrates:
1. Task understanding and structured initial plan formulation (`AgentTaskPlan`).
2. Multi-step reasoning and tool selection (`PlannerDecision`).
3. Evidence-driven continuation/completion decisions.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.agents.contracts import AgentTaskPlan, PlannerDecision
from app.agents.evidence import AgentEvidenceCollector
from app.agents.tools.base import AgentTool
from app.knowledge.generation.provider import LLMMessage, LLMProvider, MockLLMProvider

logger = logging.getLogger(__name__)

TASK_UNDERSTANDING_PROMPT = """You are the Lead Operational Planner for HospitalOps AI.
Analyze the user's operational inquiry and formulate a structured, user-safe task plan.

Operating Rules:
1. Identify the core objective and domain: 'COMPARATIVE', 'FORECAST', 'SIMULATION', 'OPTIMIZATION', 'KNOWLEDGE', or 'GENERAL'.
2. Determine if tools are required. General platform questions or greetings do not require tools.
3. Select only eligible candidate tools from the available tool specs. Never invent tool names.
4. Keep the reasoning summary concise and user-safe. Do not include raw scratchpad or private deliberations.

Available Tools:
%s

Inquiry:
%s

Respond with a strict JSON object:
{
  "objective": "<concise operational goal>",
  "task_type": "<COMPARATIVE|FORECAST|SIMULATION|OPTIMIZATION|KNOWLEDGE|GENERAL>",
  "requires_tools": true,
  "reasoning_summary": "<user-safe summary of analytical approach>",
  "required_evidence": ["<evidence type 1>", "<evidence type 2>"],
  "candidate_tool_ids": ["<tool_name 1>", "<tool_name 2>"],
  "expected_result": "<expected operational deliverable>"
}
"""

PLANNER_SYSTEM_PROMPT = """You are the Hospital Operations Analyst Agent for HospitalOps AI.
Your role is to investigate operational hospital questions using authorized, read-only tools.

Core Operating Principles:
1. Operational Intelligence Only: You analyze hospital operations, bed capacity, forecasts, what-if simulations, and resource allocations. Never diagnose patients, prescribe medication, or provide clinical treatment advice.
2. Grounded in Evidence: Never invent database records, forecasts, or optimization results. Gather evidence using available tools.
3. Strict Read-Only: All tools are read-only. You cannot mutate live hospital data.
4. Structured Decisions: At every step, you must respond with a strict JSON object matching one of two decisions:

Option A — Call an authorized tool to gather evidence:
{
  "decision": "CALL_TOOL",
  "tool_name": "<registered_tool_name>",
  "arguments": { <valid_tool_arguments> },
  "reason": "<clear explanation why this tool is needed>"
}

Option B — Provide the final answer when sufficient evidence has been gathered:
{
  "decision": "FINAL_ANSWER",
  "answer": "<evidence-grounded operational response>",
  "limitations": [ "<known constraints or assumptions>" ]
}

Available Registered Tools:
%s
"""


class AgentPlanner:
    """Manages task understanding, reasoning steps, and prompts for the agent execution loop."""

    def __init__(self, provider: LLMProvider, tools: list[AgentTool]) -> None:
        self.provider = provider
        self.tools = {t.name: t for t in tools}
        self.tools_list = tools

    def _render_tool_specs(self) -> str:
        specs = []
        for t in self.tools_list:
            specs.append(json.dumps(t.get_spec(), indent=2))
        return "\n\n".join(specs)

    def _build_system_message(self) -> LLMMessage:
        content = PLANNER_SYSTEM_PROMPT % self._render_tool_specs()
        return LLMMessage(role="system", content=content)

    async def understand_and_plan(
        self,
        task: str,
        available_tools: list[AgentTool] | None = None,
    ) -> AgentTaskPlan:
        """
        Formulate an initial structured operational plan (Chunk 5.3).
        Identifies objective, domain, required evidence, candidate tools, and tool necessity.
        """
        tools_to_use = available_tools if available_tools is not None else self.tools_list

        if isinstance(self.provider, MockLLMProvider):
            return self._plan_task_mock(task, tools_to_use)

        specs_str = "\n\n".join([json.dumps(t.get_spec(), indent=2) for t in tools_to_use])
        messages = [
            LLMMessage(role="system", content=TASK_UNDERSTANDING_PROMPT % (specs_str, task)),
            LLMMessage(role="user", content=f"Generate the structured task plan for: {task}"),
        ]

        try:
            raw_text, _, _ = await self.provider.generate(
                messages=messages,
                temperature=0.0,
                max_output_tokens=800,
            )
            return self._parse_task_plan(raw_text, task, tools_to_use)
        except Exception as exc:
            logger.warning("LLM task planning failed (%s). Falling back to heuristic plan.", exc)
            return self._plan_task_mock(task, tools_to_use)

    def _parse_task_plan(
        self,
        text: str,
        fallback_task: str,
        tools: list[AgentTool],
    ) -> AgentTaskPlan:
        clean = text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean)
        if match:
            clean = match.group(1).strip()

        try:
            data = json.loads(clean)
            # Filter candidate tools against registered allowlist
            allowed_names = {t.name for t in tools}
            candidates = [c for c in data.get("candidate_tool_ids", []) if c in allowed_names]
            data["candidate_tool_ids"] = candidates
            return AgentTaskPlan.model_validate(data)
        except Exception as exc:
            logger.warning("Failed to parse task plan JSON (%s). Using fallback plan.", exc)
            return self._plan_task_mock(fallback_task, tools)

    def _plan_task_mock(self, task: str, tools: list[AgentTool]) -> AgentTaskPlan:
        """Deterministic task understanding for tests and mock environments."""
        task_lower = task.lower()
        tool_names = {t.name for t in tools}

        unsupported_keywords = ["pizza", "weather", "stock price", "sports", "compile linux", "bitcoin"]
        if any(w in task_lower for w in unsupported_keywords):
            return AgentTaskPlan(
                objective=f"Evaluate request: {task[:60]}",
                task_type="UNSUPPORTED",
                requires_tools=False,
                reasoning_summary="The query is outside hospital operational decision intelligence.",
                required_evidence=[],
                candidate_tool_ids=[],
                expected_result="Standard out-of-scope advisory response.",
            )

        # General greeting or platform capabilities
        clean_task = re.sub(r"[^\w\s]", " ", task_lower).strip()
        words = set(clean_task.split())
        if (
            words.intersection({"hello", "hi", "hey", "help"})
            or "what can you do" in task_lower
            or "who are you" in task_lower
        ):
            return AgentTaskPlan(
                objective="Introduce platform capabilities and operational tools.",
                task_type="GENERAL",
                requires_tools=False,
                reasoning_summary="General inquiry regarding HospitalOps AI operational intelligence capabilities.",
                required_evidence=[],
                candidate_tool_ids=[],
                expected_result="Overview of available operational domains and decision tools.",
            )

        # Comparative inquiry
        if any(w in task_lower for w in ["compare", "versus", "vs", "policy with", "guidance and forecast"]):
            candidates = [t for t in ["search_hospital_knowledge", "get_existing_forecast"] if t in tool_names]
            return AgentTaskPlan(
                objective="Compare documented operational protocols against projected demand forecasts.",
                task_type="COMPARATIVE",
                requires_tools=True,
                reasoning_summary="Synthesize policy thresholds with empirical forecast trajectories.",
                required_evidence=["Documented policy guidelines", "Statistical forecast demand points"],
                candidate_tool_ids=candidates,
                expected_result="Multi-source operational alignment analysis.",
            )

        # Simulation
        if any(w in task_lower for w in ["simulation", "what-if", "what if", "scenario"]):
            candidates = [t for t in ["get_simulation_result"] if t in tool_names]
            return AgentTaskPlan(
                objective="Analyze what-if simulation run parameters and bottleneck indicators.",
                task_type="SIMULATION",
                requires_tools=True,
                reasoning_summary="Inspect hypothetical surge scenario outcomes and shortage durations.",
                required_evidence=["Simulated daily occupancy trajectory", "Resource bottleneck metrics"],
                candidate_tool_ids=candidates,
                expected_result="Simulation impact assessment and risk evaluation.",
            )

        # Optimization
        if any(w in task_lower for w in ["optimization", "optimizer", "allocation", "equipment", "surge beds", "ventilator"]):
            candidates = [t for t in ["get_optimization_explanation"] if t in tool_names]
            return AgentTaskPlan(
                objective="Explain resource optimization allocation rationale and binding constraints.",
                task_type="OPTIMIZATION",
                requires_tools=True,
                reasoning_summary="Retrieve MILP solver rationale, department priority, and slack diagnostics.",
                required_evidence=["Allocation breakdown", "Binding constraint explanations"],
                candidate_tool_ids=candidates,
                expected_result="Evidence-based optimization plan explanation.",
            )

        # Forecast
        if any(w in task_lower for w in ["forecast", "project", "admissions", "icu occupancy", "predict"]):
            candidates = [t for t in ["get_existing_forecast"] if t in tool_names]
            return AgentTaskPlan(
                objective="Retrieve verified statistical demand forecast.",
                task_type="FORECAST",
                requires_tools=True,
                reasoning_summary="Consult verified Hero DMC daily or NHSN HRD weekly ICU projections.",
                required_evidence=["Forecast trajectory points", "Prediction intervals"],
                candidate_tool_ids=candidates,
                expected_result="Forecast summary and operational capacity horizon.",
            )

        # Policy / Knowledge
        candidates = [t for t in ["search_hospital_knowledge", "answer_from_hospital_knowledge"] if t in tool_names]
        return AgentTaskPlan(
            objective="Retrieve verified operational hospital knowledge and policies.",
            task_type="KNOWLEDGE",
            requires_tools=True,
            reasoning_summary="Search hospital SOPs, operational guidelines, and clinical protocols.",
            required_evidence=["Documented SOP excerpts", "Citation references"],
            candidate_tool_ids=candidates,
            expected_result="Grounded administrative policy answer.",
        )

    async def plan_next_action(
        self,
        task: str,
        execution_history: list[dict[str, Any]] | None = None,
        step_index: int = 1,
        task_plan: AgentTaskPlan | None = None,
        evidence_collector: AgentEvidenceCollector | None = None,
    ) -> PlannerDecision:
        """
        Evaluate current progress and decide whether to call another tool or finalize.
        """
        history = execution_history or []

        # If using MockLLMProvider, provide deterministic multi-step planning
        if isinstance(self.provider, MockLLMProvider):
            return self._plan_deterministic_mock(task, history, step_index)

        # Real LLM generation
        messages: list[LLMMessage] = [self._build_system_message()]
        plan_context = f"Task: {task}"
        if task_plan:
            plan_context += f"\nInitial Strategy: {task_plan.reasoning_summary}"
        messages.append(LLMMessage(role="user", content=plan_context))

        for step in history:
            tool_name = step.get("tool_name", "")
            args = step.get("arguments", {})
            result_summary = step.get("output_summary", "")
            step_reason = step.get("reason", "")
            assistant_content = json.dumps(
                {
                    "decision": "CALL_TOOL",
                    "tool_name": tool_name,
                    "arguments": args,
                    "reason": step_reason,
                }
            )
            messages.append(LLMMessage(role="assistant", content=assistant_content))
            messages.append(
                LLMMessage(
                    role="user",
                    content=f"Tool Execution Result for '{tool_name}':\n{result_summary}\n\nWhat is your next step?",
                )
            )

        try:
            raw_text, _, _ = await self.provider.generate(
                messages=messages,
                temperature=0.0,
                max_output_tokens=1500,
            )
            return self._parse_decision_text(raw_text)
        except Exception as exc:
            logger.warning("LLM planner call failed | err=%s. Falling back to deterministic final answer.", exc)
            return PlannerDecision(
                decision="FINAL_ANSWER",
                answer=f"Could not complete multi-step reasoning due to provider error: {exc}",
                limitations=["Provider communication failure"],
            )

    def _parse_decision_text(self, text: str) -> PlannerDecision:
        """Strip markdown fences and parse structured JSON decision."""
        clean = text.strip()
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean)
        if fence_match:
            clean = fence_match.group(1).strip()

        try:
            data = json.loads(clean)
            return PlannerDecision.model_validate(data)
        except Exception as exc:
            logger.warning("Failed to parse structured planner decision: %s | text: %s", exc, text[:200])
            return PlannerDecision(
                decision="FINAL_ANSWER",
                answer=text[:1000],
                limitations=["Parsed from unstructured output"],
            )

    def _plan_deterministic_mock(
        self,
        task: str,
        execution_history: list[dict[str, Any]],
        step_index: int,
    ) -> PlannerDecision:
        """Deterministic multi-step planning engine for mock mode, offline testing, and CI."""
        task_lower = task.lower()
        called_tools = [s.get("tool_name") for s in execution_history]

        unsupported_keywords = ["pizza", "weather", "stock price", "sports", "compile linux", "bitcoin"]
        if any(w in task_lower for w in unsupported_keywords):
            return PlannerDecision(
                decision="FINAL_ANSWER",
                answer=(
                    f"The requested task '{task}' is outside the operational capabilities of HospitalOps AI. "
                    "I am specialized in hospital operations intelligence, including bed capacity, "
                    "demand forecasting, what-if simulation, resource optimization, and hospital policy knowledge."
                ),
                limitations=["Task unsupported by registered tool catalog"],
            )

        # Scenario 1: Multi-source comparison (Policy + Forecast)
        is_comparison = any(w in task_lower for w in ["compare", "versus", "vs", "guidance and forecast", "policy with"])
        if is_comparison:
            if "search_hospital_knowledge" not in called_tools and "answer_from_hospital_knowledge" not in called_tools:
                return PlannerDecision(
                    decision="CALL_TOOL",
                    tool_name="search_hospital_knowledge",
                    arguments={"query": task, "top_k": 3},
                    reason="Gather documented hospital policy guidance for the comparison.",
                )
            if "get_existing_forecast" not in called_tools:
                f_type = "icu" if "icu" in task_lower else "admissions"
                return PlannerDecision(
                    decision="CALL_TOOL",
                    tool_name="get_existing_forecast",
                    arguments={"forecast_type": f_type, "horizon": 7 if f_type == "admissions" else 2},
                    reason=f"Retrieve verified {f_type.upper()} demand forecast to compare against documented policy.",
                )
            policy_summary = next(
                (s["output_summary"] for s in execution_history if "knowledge" in s.get("tool_name", "")),
                "Documented operational guidance",
            )
            forecast_summary = next(
                (s["output_summary"] for s in execution_history if "forecast" in s.get("tool_name", "")),
                "Projected demand",
            )
            return PlannerDecision(
                decision="FINAL_ANSWER",
                answer=(
                    f"Operational Comparison Synthesis:\n\n"
                    f"1. Documented Operational Guidance:\n{policy_summary[:350]}...\n\n"
                    f"2. Verified Demand Forecast:\n{forecast_summary[:350]}...\n\n"
                    f"Conclusion: Documented capacity escalation protocols align with the forecast trajectory, "
                    f"indicating that surge threshold buffers should be monitored as projected demand approaches capacity limits."
                ),
                limitations=[
                    "Comparison synthesized from documented guidelines and statistical projections.",
                    "Real-world operational decisions require administrative verification.",
                ],
            )

        # Scenario 2: Simulation inspection
        if any(w in task_lower for w in ["simulation", "what-if", "what if", "scenario"]):
            if "get_simulation_result" not in called_tools:
                sim_match = re.search(r"sim-[\w-]+", task_lower)
                sim_id = sim_match.group(0) if sim_match else None
                return PlannerDecision(
                    decision="CALL_TOOL",
                    tool_name="get_simulation_result",
                    arguments={"simulation_id": sim_id, "limit": 3},
                    reason="Inspect what-if simulation results to evaluate hypothetical scenario outcomes.",
                )
            sim_summary = next(
                (s["output_summary"] for s in execution_history if s.get("tool_name") == "get_simulation_result"),
                "",
            )
            return PlannerDecision(
                decision="FINAL_ANSWER",
                answer=(
                    f"Simulation Investigation Summary:\n\n{sim_summary}\n\n"
                    f"Analysis: The evaluated scenario highlights prospective capacity strain. "
                    f"These results reflect hypothetical modeling and should be compared against active resource allocations."
                ),
                limitations=[
                    "Simulation results reflect hypothetical modeling and unconstrained demand assumptions.",
                    "Hospital administrators should verify active staffing buffers prior to operational changes.",
                ],
            )

        # Scenario 3: Optimization explanation
        if any(w in task_lower for w in ["optimization", "optimizer", "allocation", "equipment", "surge beds", "ventilator"]):
            if "get_optimization_explanation" not in called_tools:
                opt_match = re.search(r"opt-[\w-]+", task_lower)
                opt_id = opt_match.group(0) if opt_match else None
                return PlannerDecision(
                    decision="CALL_TOOL",
                    tool_name="get_optimization_explanation",
                    arguments={"run_id": opt_id},
                    reason="Inspect MILP optimization explanation to review allocation trade-offs and binding constraints.",
                )
            opt_summary = next(
                (s["output_summary"] for s in execution_history if s.get("tool_name") == "get_optimization_explanation"),
                "",
            )
            return PlannerDecision(
                decision="FINAL_ANSWER",
                answer=(
                    f"Optimization Plan Analysis Summary:\n\n{opt_summary}\n\n"
                    f"Decision Rationale: Algorithmic resource allocations prioritize units experiencing acute capacity strain. "
                    f"Administrators must review physical bed availability and nursing ratios before enacting relocations."
                ),
                limitations=[
                    "Recommendations are generated algorithmically under mathematical constraints.",
                    "Requires human operational approval before enacting real-world resource reassignments.",
                ],
            )

        # Scenario 4: Forecast inquiry
        if any(w in task_lower for w in ["forecast", "project", "admissions", "icu occupancy", "predict"]):
            if "get_existing_forecast" not in called_tools:
                f_type = "icu" if "icu" in task_lower else "admissions"
                return PlannerDecision(
                    decision="CALL_TOOL",
                    tool_name="get_existing_forecast",
                    arguments={"forecast_type": f_type, "horizon": 7 if f_type == "admissions" else 2},
                    reason=f"Retrieve verified {f_type.upper()} demand forecast.",
                )
            f_summary = next(
                (s["output_summary"] for s in execution_history if s.get("tool_name") == "get_existing_forecast"),
                "",
            )
            return PlannerDecision(
                decision="FINAL_ANSWER",
                answer=(
                    f"Demand Forecast Summary:\n\n{f_summary}\n\n"
                    f"Operational Guidance: Review staffing assignments across the forecast horizon."
                ),
                limitations=[
                    "Statistical projections reflect historical patterns and carry uncertainty intervals.",
                    "Surge conditions or sudden epidemic shifts may alter actual bed requirements.",
                ],
            )

        # Scenario 5: Knowledge inquiry
        if "search_hospital_knowledge" not in called_tools and "answer_from_hospital_knowledge" not in called_tools:
            return PlannerDecision(
                decision="CALL_TOOL",
                tool_name="search_hospital_knowledge",
                arguments={"query": task, "top_k": 3},
                reason="Search authorized hospital operational policies and administrative protocols.",
            )

        k_summary = next(
            (s["output_summary"] for s in execution_history if "knowledge" in s.get("tool_name", "")),
            "",
        )
        return PlannerDecision(
            decision="FINAL_ANSWER",
            answer=(
                f"Hospital Knowledge Investigation:\n\n{k_summary}\n\n"
                f"Conclusion: Documented hospital policies provide verified guidance for this inquiry."
            ),
            limitations=[
                "Guidance retrieved from approved hospital policy documents.",
                "Clinical staff and operational leadership retain final authority over implementation.",
            ],
        )
