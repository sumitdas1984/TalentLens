"""Shared application state.

Holds the singleton :class:`EvaluationService` instance that both the FastAPI
REST interface (``app.main``) and the FastMCP server (``app.mcp_server``)
import. This ensures evaluations created via one interface are visible to
the other — without it, each module instantiates its own service and the
two stores drift apart.
"""

from app.service import EvaluationService

evaluation_service = EvaluationService()