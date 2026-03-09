from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Attempt, Problem
from app.schemas import AttemptResponse, LeetCodeProblem, LeetCodeSubmission, ProblemResponse

router = APIRouter(prefix="/api/leetcode", tags=["leetcode"])


@router.post("/problem", response_model=ProblemResponse, status_code=201)
async def track_leetcode_problem(data: LeetCodeProblem, db: AsyncSession = Depends(get_db)):
    """Create or update a LeetCode problem."""
    result = await db.execute(
        select(Problem).where(Problem.leetcode_slug == data.leetcode_slug)
    )
    problem = result.scalar_one_or_none()

    if problem:
        problem.title = data.title
        if data.description:
            problem.description = data.description
        if data.difficulty:
            problem.difficulty = data.difficulty
    else:
        problem = Problem(
            title=data.title,
            description=data.description,
            difficulty=data.difficulty,
            source="leetcode",
            leetcode_slug=data.leetcode_slug,
        )
        db.add(problem)

    await db.commit()
    await db.refresh(problem)
    return problem


@router.post("/submission", response_model=AttemptResponse, status_code=201)
async def track_leetcode_submission(data: LeetCodeSubmission, db: AsyncSession = Depends(get_db)):
    """Attach code to the latest in-progress attempt, or create a new one."""
    result = await db.execute(
        select(Problem).where(Problem.leetcode_slug == data.leetcode_slug)
    )
    problem = result.scalar_one_or_none()

    if not problem:
        raise HTTPException(
            status_code=404,
            detail=f"Problem with slug '{data.leetcode_slug}' not found. Track the problem first.",
        )

    # Look for the latest in-progress attempt for this problem
    active_result = await db.execute(
        select(Attempt)
        .where(Attempt.problem_id == problem.id, Attempt.status == "in_progress")
        .order_by(Attempt.created_at.desc())
        .limit(1)
    )
    attempt = active_result.scalar_one_or_none()

    language_note = f"Language: {data.language}" if data.language else None

    if attempt:
        # Attach code to existing active attempt
        attempt.code_submission = data.code
        if language_note:
            attempt.notes = language_note
    else:
        # No active attempt, create a new one
        attempt = Attempt(
            problem_id=problem.id,
            code_submission=data.code,
            notes=language_note,
            status="in_progress",
        )
        db.add(attempt)

    await db.commit()
    await db.refresh(attempt)
    return attempt
