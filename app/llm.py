"""LLM client — picks which MCP tool to call from natural language.

This is the dispatch layer of the agent. The LLM does not run the tool —
that's the MCP client's job. It only decides *which* tool to call and
extracts the arguments.

Backed by the OpenAI Python SDK; default model is ``gpt-4o-mini``. Reads
``OPENAI_API_KEY`` from the environment.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI


DEFAULT_MODEL = "gpt-4o-mini"


SYSTEM_PROMPT = (
    "You are an agent that maps natural-language requests to MCP tool "
    "calls for a candidate evaluation service.\n\n"
    "If the user asks to evaluate a candidate, call evaluate_candidate.\n"
    "If the user asks to look up an existing evaluation by ID, call "
    "get_evaluation.\n\n"
    "If the request is missing required information (no candidate ID, "
    "no job, no skills for an evaluation; no evaluation ID for a "
    "lookup), do NOT call a tool. Instead, briefly respond explaining "
    "what information is missing and ask the user to provide it.\n\n"
    "Keep your responses concise — a single sentence is usually enough."
)


# OpenAI tool-calling format: each tool is {type: "function", function: {name, description, parameters}}
TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "evaluate_candidate",
            "description": "Create and run a candidate evaluation against a job.",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_id": {
                        "type": "string",
                        "description": "Candidate identifier (e.g. 'C001').",
                    },
                    "job_id": {
                        "type": "string",
                        "description": (
                            "Job identifier or title "
                            "(e.g. 'J100' or 'Senior ML Engineer')."
                        ),
                    },
                    "skills": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Non-empty list of skills the candidate has.",
                        "minItems": 1,
                    },
                },
                "required": ["candidate_id", "job_id", "skills"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_evaluation",
            "description": "Retrieve an existing candidate evaluation by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "evaluation_id": {
                        "type": "string",
                        "description": "Evaluation identifier in E### format.",
                        "pattern": r"E\d{3,}",
                    },
                },
                "required": ["evaluation_id"],
                "additionalProperties": False,
            },
        },
    },
]


@dataclass
class ToolDecision:
    """Result of one LLM dispatch call."""

    tool: str | None = None  # tool name, or None if GPT responded with text
    arguments: dict[str, Any] = field(default_factory=dict)
    text: str | None = None  # GPT's conversational reply when no tool was called


class LLMClient:
    """Async wrapper around the OpenAI SDK that picks MCP tools.

    One call → one ``ToolDecision``. The caller is responsible for invoking
    the chosen tool and producing the user-visible reply.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self._model = model
        # Zero-arg constructor picks up OPENAI_API_KEY from env.
        self._client = client or AsyncOpenAI()

    async def dispatch(self, message: str) -> ToolDecision:
        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            tools=TOOLS,
        )

        choice = response.choices[0].message
        tool_name: str | None = None
        tool_input: dict[str, Any] = {}
        text: str | None = choice.content

        if choice.tool_calls:
            call = choice.tool_calls[0]
            tool_name = call.function.name
            # OpenAI returns arguments as a JSON string; parse it.
            raw = call.function.arguments
            tool_input = json.loads(raw) if raw else {}

        return ToolDecision(
            tool=tool_name,
            arguments=tool_input,
            text=text,
        )


class FakeLLMClient:
    """In-memory LLM client for tests.

    Returns scripted ``ToolDecision`` objects in order. Records every
    message it was called with so tests can assert on dispatch behavior.
    """

    def __init__(self, script: list[ToolDecision]) -> None:
        self._script = list(script)
        self.calls: list[str] = []

    async def dispatch(self, message: str) -> ToolDecision:
        self.calls.append(message)
        if not self._script:
            raise AssertionError(
                f"FakeLLMClient ran out of scripted responses "
                f"(called with: {message!r})"
            )
        return self._script.pop(0)