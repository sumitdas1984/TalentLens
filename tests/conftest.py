import pytest


@pytest.fixture(autouse=True)
def _reset_evaluation_service():
    """Clear the in-memory store between tests so IDs stay predictable."""
    from app.main import evaluation_service

    evaluation_service.evaluations.clear()
    yield
    evaluation_service.evaluations.clear()