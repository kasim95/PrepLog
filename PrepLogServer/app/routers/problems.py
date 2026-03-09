
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Problem
from app.schemas import ProblemCreate, ProblemResponse, ProblemUpdate

router = APIRouter(prefix="/api/problems", tags=["problems"])


@router.get("", response_model=list[ProblemResponse])
async def list_problems(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Problem).order_by(Problem.created_at.asc()))
    return result.scalars().all()


@router.post("", response_model=ProblemResponse, status_code=201)
async def create_problem(data: ProblemCreate, db: AsyncSession = Depends(get_db)):
    problem = Problem(**data.model_dump())
    db.add(problem)
    await db.commit()
    await db.refresh(problem)
    return problem


@router.get("/{problem_id}", response_model=ProblemResponse)
async def get_problem(problem_id: int, db: AsyncSession = Depends(get_db)):
    problem = await db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return problem


@router.put("/{problem_id}", response_model=ProblemResponse)
async def update_problem(problem_id: int, data: ProblemUpdate, db: AsyncSession = Depends(get_db)):
    problem = await db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(problem, key, value)
    await db.commit()
    await db.refresh(problem)
    return problem


@router.delete("/{problem_id}", status_code=204)
async def delete_problem(problem_id: int, db: AsyncSession = Depends(get_db)):
    problem = await db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    await db.delete(problem)
    await db.commit()
