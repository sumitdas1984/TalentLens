from pydantic import BaseModel


class EvaluationRequest(BaseModel):
    candidate_id: str
    job_id: str
    skills: list[str]
