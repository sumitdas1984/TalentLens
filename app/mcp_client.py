"""MCP client for the Candidate Evaluation server.

Connects to the FastMCP server defined in :mod:`app.mcp_server` and exposes
typed Python methods that wrap the underlying MCP tool calls.

Example:

    async with EvaluationMCPClient() as client:
        tools = await client.list_tools()
        result = await client.evaluate_candidate(
            candidate_id="C001",
            job_id="J100",
            skills=["python", "fastapi"],
        )

The client connects in-process (no subprocess), which keeps the test loop
simple. For stdio / HTTP transports, construct a :class:`fastmcp.Client`
yourself — this wrapper is intentionally minimal.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Client as FastMCPClient

from app.models import EvaluationSummary


class EvaluationMCPClient:
    """Async context manager wrapping an in-process MCP client.

    Lifecycle::

        async with EvaluationMCPClient() as client:
            await client.evaluate_candidate(...)
    """

    def __init__(self) -> None:
        self._client: FastMCPClient | None = None

    async def __aenter__(self) -> "EvaluationMCPClient":
        # Import here so importing this module does not require the
        # ``fastmcp`` package at module-load time — useful for tooling that
        # only needs the type hints.
        from app.mcp_server import mcp

        self._client = FastMCPClient(mcp)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.__aexit__(exc_type, exc, tb)
            self._client = None

    @property
    def _conn(self) -> FastMCPClient:
        if self._client is None:
            raise RuntimeError(
                "EvaluationMCPClient is not connected. "
                "Use 'async with EvaluationMCPClient() as client:'."
            )
        return self._client

    async def list_tools(self) -> list[Any]:
        """Discover the tools exposed by the MCP server."""
        return await self._conn.list_tools()

    async def evaluate_candidate(
        self,
        candidate_id: str,
        job_id: str,
        skills: list[str],
    ) -> EvaluationSummary:
        """Invoke the ``evaluate_candidate`` MCP tool."""
        result = await self._conn.call_tool(
            "evaluate_candidate",
            {
                "candidate_id": candidate_id,
                "job_id": job_id,
                "skills": skills,
            },
        )
        if result.is_error:
            raise RuntimeError(
                f"evaluate_candidate failed: {result.structured_content}"
            )
        return EvaluationSummary(**result.structured_content)

    async def get_evaluation(self, evaluation_id: str) -> EvaluationSummary:
        """Invoke the ``get_evaluation`` MCP tool."""
        result = await self._conn.call_tool(
            "get_evaluation",
            {"evaluation_id": evaluation_id},
        )
        if result.is_error:
            raise RuntimeError(
                f"get_evaluation failed: {result.structured_content}"
            )
        return EvaluationSummary(**result.structured_content)