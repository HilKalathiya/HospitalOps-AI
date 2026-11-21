"""
HospitalOps AI — Agent Planner & Decision Synthesis (Milestone 5, Chunk 5.1).

Orchestrates multi-step reasoning, tool selection, structured decision parsing,
and evidence-grounded final answer synthesis using LLM providers or deterministic logic.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.agents.contracts import PlannerDecision
from app.agents.tools.base import AgentTool
from app.knowledge.generation.provider import LLMMessage, LLMProvider, MockLLMProvider

logger = logging.getLogger(__name__)

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
    """Manages reasoning steps and prompts for the agent execution loop."""

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

    async def plan_next_action(
        self,
        task: str,
        execution_history: list[dict[str, Any]],
        step_index: int,
    ) -> PlannerDecision:
        """
        Evaluate the task and prior tool executions to choose the next action.
        """
        # If using MockLLMProvider, provide deterministic multi-step planning
        if isinstance(self.provider, MockLLMProvider):
            return self._plan_deterministic_mock(task, execution_history, step_index)

        # Real LLM generation
        messages: list[LLMMessage] = [self._build_system_message()]
        messages.append(LLMMessage(role="user", content=f"Operational Task: {task}"))

        for step in execution_history:
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
            # Fallback if text contains an answer
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
        """
        Deterministic multi-step planning engine for mock mode, offline testing, and CI.
        Demonstrates genuine multi-step tool sequences based on task semantics.
        """
        task_lower = task.lower()
        called_tools = [s.get("tool_name") for s in execution_history]

        # Check for unsupported tasks (e.g. non-hospital tasks)
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
            # Both tools have run! Synthesize comparative answer
            policy_summary = next((s["output_summary"] for s in execution_history if "knowledge" in s.get("tool_name", "")), "Documented operational guidance")
            forecast_summary = next((s["output_summary"] for s in execution_history if "forecast" in s.get("tool_name", "")), "Projected demand")
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
                # Extract potential ID if present
                sim_match = re.search(r"sim-[\w-]+", task_lower)
                sim_id = sim_match.group(0) if sim_match else None
                return PlannerDecision(
                    decision="CALL_TOOL",
                    tool_name="get_simulation_result",
                    arguments={"simulation_id": sim_id, "limit": 3},
                    reason="Inspect what-if simulation results to evaluate hypothetical scenario outcomes.",
                )
            sim_summary = next((s["output_summary"] for s in execution_history if s.get("tool_name") == "get_simulation_result"), "")
            return PlannerDecision(
                decision="FINAL_ANSWER",
                answer=(
                    f"Simulation Investigation Summary:\n\n{sim_summary}\n\n"
                    f"Analysis: The evaluated scenario highlights prospective capacity strain. "
                    f"These results reflect hypothetical modeling and should be compared against active resource allocations."
                ),
                limitations=["Hypothetical simulation outcomes; not current operational hospital state."],
            )

        # Scenario 3: Optimization explanation
        if any(w in task_lower for w in ["optimization", "milp", "allocate", "allocation", "solver", "binding constraint"]):
            if "get_optimization_explanation" not in called_tools:
                opt_match = re.search(r"opt-[\w-]+", task_lower)
                run_id = opt_match.group(0) if opt_match else None
                return PlannerDecision(
                    decision="CALL_TOOL",
                    tool_name="get_optimization_explanation",
                    arguments={"run_id": run_id, "limit": 3},
                    reason="Inspect MILP optimization plan, objective deconstruction, and binding constraint bottlenecks.",
                )
            opt_summary = next((s["output_summary"] for s in execution_history if s.get("tool_name") == "get_optimization_explanation"), "")
            return PlannerDecision(
                decision="FINAL_ANSWER",
                answer=(
                    f"Optimization Plan Analysis:\n\n{opt_summary}\n\n"
                    f"Recommendation Rationale: The MILP optimizer prioritizes departments facing high deficit penalties "
                    f"within available surge and equipment inventory bounds."
                ),
                limitations=["Advisory recommendation requiring operational leadership approval prior to execution."],
            )

        # Scenario 4: Forecast inspection
        if any(w in task_lower for w in ["forecast", "demand", "projection", "predict"]):
            if "get_existing_forecast" not in called_tools:
                f_type = "icu" if "icu" in task_lower else "admissions"
                return PlannerDecision(
                    decision="CALL_TOOL",
                    tool_name="get_existing_forecast",
                    arguments={"forecast_type": f_type},
                    reason=f"Retrieve verified {f_type.upper()} operational demand forecast.",
                )
            fc_summary = next((s["output_summary"] for s in execution_history if s.get("tool_name") == "get_existing_forecast"), "")
            return PlannerDecision(
                decision="FINAL_ANSWER",
                answer=f"Verified Operational Forecast Analysis:\n\n{fc_summary}",
                limitations=["Forecast projections subject to model uncertainty intervals."],
            )

        # Scenario 5: Policy / Knowledge inquiry (Default)
        if "search_hospital_knowledge" not in called_tools and "answer_from_hospital_knowledge" not in called_tools:
            return PlannerDecision(
                decision="CALL_TOOL",
                tool_name="search_hospital_knowledge",
                arguments={"query": task, "top_k": 4},
                reason="Search hospital knowledge base for relevant policy documents and SOPs.",
            )

        kn_summary = next((s["output_summary"] for s in execution_history if "knowledge" in s.get("tool_name", "")), "")
        return PlannerDecision(
            decision="FINAL_ANSWER",
            answer=(
                f"Operational Knowledge Analysis:\n\n{kn_summary}\n\n"
                f"Summary: The retrieved hospital documentation provides authoritative guidelines regarding this operational procedure."
            ),
            limitations=["Based on ingested hospital documentation versions."],
        )
