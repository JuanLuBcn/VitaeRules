"""
Query contract for Retrieval Crew.

Defines structured queries for searching memory and generating grounded answers.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class QueryIntent(str, Enum):
    """Intent classification for user queries."""

    FACTUAL = "factual"  # What, who, where facts
    TEMPORAL = "temporal"  # When, time-based questions
    LIST = "list"  # List all X
    SUMMARY = "summary"  # Summarize, overview questions
    UNKNOWN = "unknown"  # Could not classify


class DateRange(BaseModel):
    """Date range filter for temporal queries."""

    start: datetime | None = None
    end: datetime | None = None


class QueryFilters(BaseModel):
    """Filters to narrow memory search."""

    people: list[str] = Field(default_factory=list)
    places: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    date_range: DateRange | None = None
    sections: list[str] = Field(default_factory=list)  # diary, task, note, etc.


class Query(BaseModel):
    """
    Structured query for searching memory.

    Produced by QueryPlanner, consumed by Retriever.
    """

    query_text: str = Field(description="Original user question")
    intent: QueryIntent = Field(default=QueryIntent.UNKNOWN)
    filters: QueryFilters = Field(default_factory=QueryFilters)
    max_results: int = Field(default=10, ge=1, le=100)
    reasoning: str | None = Field(
        default=None, description="Agent's reasoning for classification"
    )


class Citation(BaseModel):
    """Citation reference for a memory item."""

    memory_id: str
    title: str | None = None
    created_at: datetime | None = None
    excerpt: str | None = None  # Relevant excerpt from content


class GroundedAnswer(BaseModel):
    """
    Answer with citations enforcing zero-evidence policy.

    If no relevant memories found, answer should explicitly state that.
    """

    query: str = Field(description="Original user question")
    answer: str = Field(description="Grounded answer with inline citations")
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    has_evidence: bool = Field(
        default=False, description="Whether answer is backed by memories"
    )
    reasoning: str | None = Field(
        default=None, description="How answer was composed from sources"
    )
