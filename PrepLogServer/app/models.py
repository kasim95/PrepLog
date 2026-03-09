from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    difficulty = Column(String, nullable=True)
    source = Column(String, nullable=False, default="custom")
    leetcode_slug = Column(String, nullable=True, unique=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    attempts = relationship("Attempt", back_populates="problem", cascade="all, delete-orphan")


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    code_submission = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="in_progress")  # in_progress, paused, completed
    started_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    problem = relationship("Problem", back_populates="attempts")
    recordings = relationship("Recording", back_populates="attempt", cascade="all, delete-orphan")


class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    attempt_id = Column(Integer, ForeignKey("attempts.id"), nullable=False)
    file_path = Column(String, nullable=False)
    duration_seconds = Column(Float, nullable=True)
    transcription = Column(Text, nullable=True)
    transcription_status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    attempt = relationship("Attempt", back_populates="recordings")
