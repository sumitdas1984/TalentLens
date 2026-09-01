from fastapi import FastAPI, HTTPException, status

from app.middleware import RequestMiddleware
from app.models import EvaluationRequest, EvaluationResponse, RunEvaluationResponse
from app.service import EvaluationService

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
    response_model=RunEvaluationResponse,
)
async def run_evaluation(evaluation_id: str) -> RunEvaluationResponse:
    evaluation = await evaluation_service.run_evaluation(evaluation_id)
    if evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation '{evaluation_id}' not found.",
        )
    return RunEvaluationResponse(
        evaluation_id=evaluation["evaluation_id"],
        status=evaluation["status"],
        score=evaluation["score"],
    )