"""Candidate evaluation package.

Loads environment variables from a project-level ``.env`` file (if present)
on import. This is the standard idiom so any entry point — uvicorn, the
MCP server, programmatic startup — picks up ``OPENAI_API_KEY`` and friends
without manual ``export`` calls.

Keys are NOT committed: ``.env`` is listed in ``.gitignore``.
"""

from dotenv import load_dotenv

load_dotenv()