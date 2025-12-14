"""Pydantic models for Chat Crew structured outputs."""

from pydantic import BaseModel, Field
from typing import Literal


class IntentClassification(BaseModel):
    """Structured intent classification result.
    
    Binary classification of user intent:
    - SEARCH: User wants to retrieve/query existing information
    - ACTION: User wants to store/modify data or communicate (default)
    """
    
    intent: Literal["SEARCH", "ACTION"] = Field(
        ...,
        description="The classified intent. SEARCH for information retrieval, ACTION for everything else"
    )
    
    reasoning: str = Field(
        ...,
        description="Brief explanation of why this intent was chosen based on semantic analysis"
    )
    
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 (uncertain) to 1.0 (very confident)"
    )
