import asyncio


class EvaluationNotFound(Exception):
    """Raised when an evaluation ID does not exist."""

    def __init__(self, evaluation_id: str):
        self.evaluation_id = evaluation_id
        super().__init__(f"Evaluation '{evaluation_id}' not found.")


class InvalidStateTransition(Exception):
    """Raised when an evaluation cannot move to the requested status."""

    def __init__(self, evaluation_id: str, current_status: str):
        self.evaluation_id = evaluation_id
        self.current_status = current_status
        super().__init__(
            f"Evaluation '{evaluation_id}' cannot be run from status "
            f"'{current_status}'."
        )


async def analyze_skills() -> float:
    """Simulate an I/O-bound skill analysis and return a score."""
    await asyncio.sleep(1)
    return 80


async def analyze_resume() -> float:
    """Simulate an I/O-bound resume analysis and return a score."""
    await asyncio.sleep(1)
    return 90


async def analyze_experience() -> float:
    """Simulate an I/O-bound experience analysis and return a score."""
    await asyncio.sleep(1)
    return 85


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

    async def run_evaluation(self, evaluation_id: str) -> dict:
        """Run all analyzers concurrently and finalize the evaluation.

        Only ``pending`` evaluations can transition to ``running``. Raises
        :class:`EvaluationNotFound` if the ID is unknown and
        :class:`InvalidStateTransition` if the evaluation is already
        ``running`` or ``completed``.
        """
        evaluation = self.evaluations.get(evaluation_id)
        if evaluation is None:
            raise EvaluationNotFound(evaluation_id)

        if evaluation["status"] != "pending":
            raise InvalidStateTransition(evaluation_id, evaluation["status"])

        evaluation["status"] = "running"

        skill_score, resume_score, experience_score = await asyncio.gather(
            analyze_skills(),
            analyze_resume(),
            analyze_experience(),
        )

        evaluation["score"] = (
            skill_score + resume_score + experience_score
        ) / 3
        evaluation["status"] = "completed"
        return evaluation