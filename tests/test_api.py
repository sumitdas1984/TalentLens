import time

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio

VALID_PAYLOAD = {
    "candidate_id": "C001",
    "job_id": "J100",
    "skills": ["python", "fastapi", "aws"],
}


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


async def test_create_evaluation_returns_201(client):
    response = await client.post("/evaluations", json=VALID_PAYLOAD)
    assert response.status_code == 201

    body = response.json()
    assert body["evaluation_id"] == "E001"
    assert body["candidate_id"] == "C001"
    assert body["job_id"] == "J100"
    assert body["skills"] == ["python", "fastapi", "aws"]
    assert body["status"] == "pending"
    assert body["score"] is None


async def test_get_evaluation_returns_200(client):
    create = await client.post("/evaluations", json=VALID_PAYLOAD)
    evaluation_id = create.json()["evaluation_id"]

    response = await client.get(f"/evaluations/{evaluation_id}")
    assert response.status_code == 200
    assert response.json()["evaluation_id"] == evaluation_id


async def test_unknown_evaluation_returns_404(client):
    response = await client.get("/evaluations/E999")
    assert response.status_code == 404
    assert "E999" in response.json()["detail"]


async def test_run_evaluation_completes_with_score_85(client):
    create = await client.post("/evaluations", json=VALID_PAYLOAD)
    evaluation_id = create.json()["evaluation_id"]

    response = await client.post(f"/evaluations/{evaluation_id}/run")
    assert response.status_code == 200

    body = response.json()
    assert body["evaluation_id"] == evaluation_id
    assert body["status"] == "completed"
    assert body["score"] == 85


async def test_run_completed_evaluation_returns_409(client):
    create = await client.post("/evaluations", json=VALID_PAYLOAD)
    evaluation_id = create.json()["evaluation_id"]

    first = await client.post(f"/evaluations/{evaluation_id}/run")
    assert first.status_code == 200

    second = await client.post(f"/evaluations/{evaluation_id}/run")
    assert second.status_code == 409
    assert evaluation_id in second.json()["detail"]


async def test_invalid_request_returns_422(client):
    # empty candidate_id
    response = await client.post(
        "/evaluations",
        json={"candidate_id": "", "job_id": "J100", "skills": ["python"]},
    )
    assert response.status_code == 422

    # empty skills list
    response = await client.post(
        "/evaluations",
        json={"candidate_id": "C001", "job_id": "J100", "skills": []},
    )
    assert response.status_code == 422


async def test_middleware_headers_present(client):
    response = await client.get("/health")
    assert "x-request-id" in response.headers
    assert "x-process-time" in response.headers


async def test_run_evaluation_runs_concurrently(client):
    create = await client.post("/evaluations", json=VALID_PAYLOAD)
    evaluation_id = create.json()["evaluation_id"]

    start = time.perf_counter()
    response = await client.post(f"/evaluations/{evaluation_id}/run")
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    # Each analyzer sleeps 1s. Sequential would be ~3s; with asyncio.gather
    # the wall-clock should be ~1s. Allow generous slack for cold CI.
    assert elapsed < 2.0, (
        f"Expected concurrent execution (~1s), got {elapsed:.2f}s"
    )


async def test_rest_and_mcp_share_the_same_store(client):
    """A REST-created evaluation must be visible to the shared service.

    Verifies 9.1: the FastAPI app references the same EvaluationService
    singleton held in app.state (which the MCP server also imports).
    """
    from app.state import evaluation_service as shared

    create = await client.post("/evaluations", json=VALID_PAYLOAD)
    evaluation_id = create.json()["evaluation_id"]

    # The shared store — what the MCP server also sees — has the new ID.
    stored = shared.get_evaluation(evaluation_id)
    assert stored is not None
    assert stored["evaluation_id"] == evaluation_id


async def test_mcp_client_connects_and_invokes_tools():
    """Verifies 9.2: the MCP client can connect, list tools, and call them."""
    from app.mcp_client import EvaluationMCPClient

    async with EvaluationMCPClient() as mcp:
        tools = await mcp.list_tools()
        names = {t.name for t in tools}
        assert names == {"evaluate_candidate", "get_evaluation"}

        # Drive the full pipeline through MCP.
        result = await mcp.evaluate_candidate(
            candidate_id="C001",
            job_id="J100",
            skills=["python", "fastapi", "aws"],
        )
        assert result.evaluation_id == "E001"
        assert result.status == "completed"
        assert result.score == 85

        # Round-trip the same ID back through MCP.
        fetched = await mcp.get_evaluation(result.evaluation_id)
        assert fetched.evaluation_id == result.evaluation_id
        assert fetched.score == result.score


async def test_agent_evaluates_candidate_from_natural_language():
    """9.4: Agent uses LLM dispatch → evaluate_candidate MCP tool."""
    from app.agent import Agent
    from app.llm import FakeLLMClient, ToolDecision

    fake = FakeLLMClient(
        [
            ToolDecision(
                tool="evaluate_candidate",
                arguments={
                    "candidate_id": "C123",
                    "job_id": "Senior ML Engineer",
                    "skills": ["Python", "FastAPI", "RAG", "LLMOps"],
                },
            )
        ]
    )
    agent = Agent(llm=fake)

    reply = await agent.run(
        "Evaluate candidate C123 for the Senior ML Engineer position. "
        "Their skills are Python, FastAPI, RAG and LLMOps."
    )

    assert "C123" in reply
    assert "Senior ML Engineer" in reply
    assert "85" in reply
    # The LLM was actually called with the original message.
    assert len(fake.calls) == 1
    assert "C123" in fake.calls[0]


async def test_agent_gets_evaluation_from_natural_language():
    """9.4: Agent routes 'look up E001' to get_evaluation."""
    from app.agent import Agent
    from app.llm import FakeLLMClient, ToolDecision

    fake = FakeLLMClient(
        [
            # First call seeds an evaluation through the agent path.
            ToolDecision(
                tool="evaluate_candidate",
                arguments={
                    "candidate_id": "C001",
                    "job_id": "J100",
                    "skills": ["Python", "FastAPI"],
                },
            ),
            # Second call looks it up.
            ToolDecision(
                tool="get_evaluation",
                arguments={"evaluation_id": "E001"},
            ),
        ]
    )
    agent = Agent(llm=fake)

    await agent.run(
        "Evaluate candidate C001 for job J100. Skills are Python and FastAPI."
    )
    reply = await agent.run("What was the result of evaluation E001?")

    assert "E001" in reply
    assert "completed" in reply
    assert "85" in reply


async def test_agent_returns_llm_text_when_no_tool_called():
    """9.4: when the LLM responds conversationally (missing info), the
    agent returns that text instead of raising."""
    from app.agent import Agent
    from app.llm import FakeLLMClient, ToolDecision

    fake = FakeLLMClient(
        [
            ToolDecision(
                tool=None,
                arguments={},
                text="Please provide a candidate ID, job, and skills.",
            )
        ]
    )
    agent = Agent(llm=fake)

    reply = await agent.run("Evaluate John")
    assert "candidate ID" in reply
    assert "skills" in reply


async def test_chat_endpoint_delegates_to_agent(monkeypatch):
    """9.5: POST /chat passes the message to agent.run() and returns its reply."""
    from app.llm import FakeLLMClient, ToolDecision
    from app.main import app

    fake = FakeLLMClient(
        [
            ToolDecision(
                tool="evaluate_candidate",
                arguments={
                    "candidate_id": "C777",
                    "job_id": "ML Engineer",
                    "skills": ["Python", "PyTorch"],
                },
            )
        ]
    )
    # Replace the module-level Agent with one that uses our fake.
    from app.agent import Agent as RealAgent

    monkeypatch.setattr("app.main.agent", RealAgent(llm=fake))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        response = await ac.post(
            "/chat",
            json={
                "message": "Evaluate candidate C777 for the ML Engineer role. "
                "Skills are Python and PyTorch.",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert "response" in body
    assert "C777" in body["response"]
    assert "85" in body["response"]
    # The agent was called with the user's raw message.
    assert len(fake.calls) == 1
    assert "C777" in fake.calls[0]


async def test_chat_endpoint_passes_through_llm_text(monkeypatch):
    """9.5: when the agent returns Claude's conversational text, /chat
    surfaces it in the response field."""
    from app.agent import Agent as RealAgent
    from app.llm import FakeLLMClient, ToolDecision
    from app.main import app

    fake = FakeLLMClient(
        [
            ToolDecision(
                tool=None,
                arguments={},
                text="Please provide a candidate ID, job, and skills.",
            )
        ]
    )
    monkeypatch.setattr("app.main.agent", RealAgent(llm=fake))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        response = await ac.post("/chat", json={"message": "Evaluate John"})

    assert response.status_code == 200
    assert "candidate ID" in response.json()["response"]


async def test_chat_endpoint_rejects_empty_message(client):
    """9.5: empty message → 422 (Pydantic validation)."""
    response = await client.post("/chat", json={"message": ""})
    assert response.status_code == 422

    response = await client.post("/chat", json={})
    assert response.status_code == 422


async def test_agent_asks_for_missing_required_args():
    """9.6: LLM picks a tool with empty required args → agent asks, doesn't dispatch."""
    from app.agent import Agent
    from app.llm import FakeLLMClient, ToolDecision

    fake = FakeLLMClient(
        [
            # LLM picks evaluate_candidate but only fills candidate_id.
            ToolDecision(
                tool="evaluate_candidate",
                arguments={"candidate_id": "C001"},
            )
        ]
    )
    agent = Agent(llm=fake)

    reply = await agent.run("Evaluate C001")
    assert "job_id" in reply
    assert "skills" in reply
    # The tool should NOT have been called — no evaluation created.
    from app.state import evaluation_service

    assert evaluation_service.evaluations == {}


async def test_agent_handles_llm_failure_gracefully():
    """9.6: LLM raises → agent returns a helpful retry message."""
    from app.agent import Agent

    class _ExplodingLLM:
        async def dispatch(self, message: str):
            raise RuntimeError("simulated API outage")

    agent = Agent(llm=_ExplodingLLM())
    reply = await agent.run("anything")

    assert "try again" in reply.lower() or "trouble" in reply.lower()


async def test_agent_handles_mcp_failure_gracefully(monkeypatch):
    """9.6: MCP tool raises → agent returns a helpful rephrase message."""
    from app.agent import Agent
    from app.llm import FakeLLMClient, ToolDecision

    fake = FakeLLMClient(
        [
            ToolDecision(
                tool="evaluate_candidate",
                arguments={
                    "candidate_id": "C001",
                    "job_id": "J100",
                    "skills": ["Python"],
                },
            )
        ]
    )
    agent = Agent(llm=fake)

    # Make EvaluationMCPClient fail inside the agent's import path.
    class _ExplodingMCP:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def evaluate_candidate(self, **kwargs):
            raise RuntimeError("simulated MCP outage")

    monkeypatch.setattr("app.agent.EvaluationMCPClient", _ExplodingMCP)

    reply = await agent.run("Evaluate C001 for J100 with Python")
    assert "rephras" in reply.lower() or "try" in reply.lower()