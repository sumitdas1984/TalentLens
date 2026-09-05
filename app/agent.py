"""LLM-backed agent — natural language → MCP tool → natural-language reply.

The dispatch layer (which tool to call + argument extraction) is handled by
an :class:`app.llm.LLMClient`. This module owns:

1. Calling the LLM to get a tool decision.
2. Validating the decision has all required arguments — if not, returning
   a "please provide X, Y, Z" message instead of dispatching a tool with
   garbage arguments.
3. Routing the decision through the MCP client to actually run the tool.
4. Formatting a templated natural-language reply from the tool result.
5. Catching LLM / MCP failures and returning graceful messages so the
   ``/chat`` endpoint never crashes mid-request.
"""

from __future__ import annotations

import logging

from app.llm import LLMClient, ToolDecision
from app.mcp_client import EvaluationMCPClient

logger = logging.getLogger(__name__)


# Required arguments per tool. Mirrors the schemas in app.llm.TOOLS.
_REQUIRED_ARGS: dict[str, tuple[str, ...]] = {
    "evaluate_candidate": ("candidate_id", "job_id", "skills"),
    "get_evaluation": ("evaluation_id",),
}


class Agent:
    """LLM-driven dispatcher from natural language to MCP tools."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()

    async def run(self, message: str) -> str:
        # 1. Ask the LLM which tool to call.
        try:
            decision = await self._llm.dispatch(message)
        except Exception as exc:
            logger.warning("LLM dispatch failed: %s", exc)
            return (
                "I'm having trouble reaching the language model right now. "
                "Please try again in a moment."
            )

        # 2. If the LLM picked a tool, make sure all required arguments
        #    are present before we waste an MCP round-trip.
        if decision.tool is not None:
            missing = _missing_required_args(decision)
            if missing:
                return (
                    "I need a bit more information to help. "
                    f"Please provide: {', '.join(missing)}."
                )

        # 3. Execute (or surface the LLM's conversational reply).
        try:
            return await self._execute(decision)
        except Exception as exc:
            logger.warning("Tool execution failed: %s", exc)
            return (
                "Something went wrong while I was working on that. "
                "Please try rephrasing your request."
            )

    async def _execute(self, decision: ToolDecision) -> str:
        if decision.tool == "evaluate_candidate":
            async with EvaluationMCPClient() as client:
                summary = await client.evaluate_candidate(**decision.arguments)
            return (
                f"Candidate {summary.candidate_id} received a score of "
                f"{summary.score} for job {summary.job_id}."
            )

        if decision.tool == "get_evaluation":
            async with EvaluationMCPClient() as client:
                summary = await client.get_evaluation(**decision.arguments)
            return (
                f"Evaluation {summary.evaluation_id} has status "
                f"'{summary.status}' with score {summary.score}."
            )

        # No tool called — Claude responded conversationally (e.g. asking
        # for missing information). Surface that reply to the user.
        if decision.text:
            return decision.text
        return (
            "I'm not sure how to help with that. Try asking me to "
            "'evaluate candidate C001 for job J100 with skills Python' "
            "or 'look up evaluation E001'."
        )


def _missing_required_args(decision: ToolDecision) -> list[str]:
    """Return the names of required arguments the LLM failed to provide."""
    required = _REQUIRED_ARGS.get(decision.tool or "", ())
    missing: list[str] = []
    for name in required:
        value = decision.arguments.get(name)
        if value is None or value == "" or value == []:
            missing.append(name)
    return missing