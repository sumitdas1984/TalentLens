from fastmcp import FastMCP

from app.models import EvaluationResult
from app.service import EvaluationService

mcp = FastMCP("Candidate Evaluation Server")

_service = EvaluationService()


@mcp.tool()
async def evaluate_candidate(
    candidate_id: str,
    job_id: str,
    skills: list[str],
) -> EvaluationResult:
    """Evaluate a candidate against a job and return the evaluation result."""
    evaluation = _service.create_evaluation(
        candidate_id=candidate_id,
        job_id=job_id,
        skills=skills,
    )
    completed = await _service.run_evaluation(evaluation["evaluation_id"])
    return EvaluationResult(
        evaluation_id=completed["evaluation_id"],
        candidate_id=completed["candidate_id"],
        job_id=completed["job_id"],
        status=completed["status"],
        score=completed["score"],
    )


@mcp.tool()
async def get_evaluation(evaluation_id: str) -> EvaluationResult:
    """Retrieve an existing candidate evaluation by its ID."""
    evaluation = _service.get_evaluation(evaluation_id)
    if evaluation is None:
        raise ValueError(f"Evaluation '{evaluation_id}' not found.")
    return EvaluationResult(
        evaluation_id=evaluation["evaluation_id"],
        candidate_id=evaluation["candidate_id"],
        job_id=evaluation["job_id"],
        status=evaluation["status"],
        score=evaluation["score"],
    )


if __name__ == "__main__":
    mcp.run()