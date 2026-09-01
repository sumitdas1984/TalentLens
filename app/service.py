class EvaluationService:

    def __init__(self):
        self.evaluations: dict[str, dict] = {}

    def _next_evaluation_id(self) -> str:
        """Generate the next evaluation ID in the sequence E001, E002, ..."""
        next_number = len(self.evaluations) + 1
        return f"E{next_number:03d}"

    def create_evaluation(
        self,
        candidate_id: str,
        job_id: str,
        skills: list[str],
    ) -> dict:
        """Create a new evaluation and store it in memory."""
        evaluation_id = self._next_evaluation_id()
        evaluation = {
            "evaluation_id": evaluation_id,
            "candidate_id": candidate_id,
            "job_id": job_id,
            "skills": skills,
            "status": "pending",
            "score": None,
        }
        self.evaluations[evaluation_id] = evaluation
        return evaluation

    def get_evaluation(self, evaluation_id: str) -> dict | None:
        """Retrieve an evaluation by its ID, or None if not found."""
        return self.evaluations.get(evaluation_id)