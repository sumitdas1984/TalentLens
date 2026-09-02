from fastapi import FastAPI, HTTPException, status

from app.middleware import RequestMiddleware
from app.models import EvaluationRequest, EvaluationResponse, EvaluationSummary
from app.service import (
    EvaluationNotFound,
    EvaluationService,
    InvalidStateTransition,
)

app = FastAPI(
    title="Candidate Evaluation API",
    version="1.0.0"
)

app.add_middleware(RequestMiddleware)

evaluation_service = EvaluationService()


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post(
    "/evaluations",
    response_model=EvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_evaluation(payload: EvaluationRequest) -> EvaluationResponse:
    evaluation = evaluation_service.create_evaluation(
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        skills=payload.skills,
    )
    return EvaluationResponse(**evaluation)


@app.get(
    "/evaluations/{evaluation_id}",
    response_model=EvaluationResponse,
)
async def get_evaluation(evaluation_id: str) -> EvaluationResponse:
    evaluation = evaluation_service.get_evaluation(evaluation_id)
    if evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation '{evaluation_id}' not found.",
        )
    return EvaluationResponse(**evaluation)


@app.post(
    "/evaluations/{evaluation_id}/run",
    response_model=EvaluationSummary,
)
async def run_evaluation(evaluation_id: str) -> EvaluationSummary:
    try:
        evaluation = await evaluation_service.run_evaluation(evaluation_id)
    except EvaluationNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation '{evaluation_id}' not found.",
        )
    except InvalidStateTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return EvaluationSummary(
        evaluation_id=evaluation["evaluation_id"],
        candidate_id=evaluation["candidate_id"],
        job_id=evaluation["job_id"],
        status=evaluation["status"],
        score=evaluation["score"],
    )