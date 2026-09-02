from pydantic import BaseModel, Field


class EvaluationRequest(BaseModel):
    candidate_id: str = Field(..., min_length=1)
    job_id: str = Field(..., min_length=1)
    skills: list[str] = Field(..., min_length=1)


class EvaluationResponse(BaseModel):
    evaluation_id: str
    candidate_id: str
    job_id: str
    skills: list[str]
    status: str
    score: float | None = None


class EvaluationSummary(BaseModel):
    """Compact evaluation record returned by the /run endpoint and MCP tools.

    Omits ``skills`` because the caller already supplied them when the
    evaluation was created.
    """

    evaluation_id: str
    candidate_id: str
    job_id: str
    status: str
    score: float | None = None
