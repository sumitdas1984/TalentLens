from fastmcp import FastMCP

from app.models import EvaluationSummary
from app.state import evaluation_service

mcp = FastMCP("Candidate Evaluation Server")


@mcp.tool()
async def evaluate_candidate(
    candidate_id: str,
    job_id: str,
    skills: list[str],
) -> EvaluationSummary:
    """Evaluate a candidate against a job and return the evaluation result."""
    evaluation = evaluation_service.create_evaluation(
        candidate_id=candidate_id,
        job_id=job_id,
        skills=skills,
    )
    completed = await evaluation_service.run_evaluation(evaluation["evaluation_id"])
    return EvaluationSummary(
        evaluation_id=completed["evaluation_id"],
        candidate_id=completed["candidate_id"],
        job_id=completed["job_id"],
        status=completed["status"],
        score=completed["score"],
    )


@mcp.tool()
async def get_evaluation(evaluation_id: str) -> EvaluationSummary:
    """Retrieve an existing candidate evaluation by its ID."""
    evaluation = evaluation_service.get_evaluation(evaluation_id)
    if evaluation is None:
        raise ValueError(f"Evaluation '{evaluation_id}' not found.")
    return EvaluationSummary(
        evaluation_id=evaluation["evaluation_id"],
        candidate_id=evaluation["candidate_id"],
        job_id=evaluation["job_id"],
        status=evaluation["status"],
        score=evaluation["score"],
    )


if __name__ == "__main__":
    mcp.run()