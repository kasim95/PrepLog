
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Attempt, Problem
from app.schemas import AttemptCreate, AttemptResponse, AttemptUpdate

router = APIRouter(tags=["attempts"])


@router.get("/api/problems/{problem_id}/attempts", response_model=list[AttemptResponse])
async def list_attempts(problem_id: int, db: AsyncSession = Depends(get_db)):
    problem = await db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    result = await db.execute(
        select(Attempt).where(Attempt.problem_id == problem_id).order_by(Attempt.created_at.asc())
    )
    return result.scalars().all()


@router.post("/api/problems/{problem_id}/attempts", response_model=AttemptResponse, status_code=201)
async def create_attempt(problem_id: int, data: AttemptCreate, db: AsyncSession = Depends(get_db)):
    problem = await db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    attempt = Attempt(problem_id=problem_id, **data.model_dump())
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return attempt


@router.get("/api/attempts/{attempt_id}", response_model=AttemptResponse)
async def get_attempt(attempt_id: int, db: AsyncSession = Depends(get_db)):
    attempt = await db.get(Attempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return attempt


@router.put("/api/attempts/{attempt_id}", response_model=AttemptResponse)
async def update_attempt(attempt_id: int, data: AttemptUpdate, db: AsyncSession = Depends(get_db)):
    attempt = await db.get(Attempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(attempt, key, value)
    await db.commit()
    await db.refresh(attempt)
    return attempt


@router.delete("/api/attempts/{attempt_id}", status_code=204)
async def delete_attempt(attempt_id: int, db: AsyncSession = Depends(get_db)):
    attempt = await db.get(Attempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    await db.delete(attempt)
    await db.commit()
