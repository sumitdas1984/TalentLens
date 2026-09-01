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