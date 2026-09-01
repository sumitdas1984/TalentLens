from pydantic import BaseModel


class EvaluationRequest(BaseModel):
    candidate_id: str
    job_id: str
    skills: list[str]


class EvaluationResponse(BaseModel):
    evaluation_id: str
    candidate_id: str
    job_id: str
    skills: list[str]
    status: str
    score: float | None = None


class RunEvaluationResponse(BaseModel):
    evaluation_id: str
    status: str | None = None
    score: float | None = None
