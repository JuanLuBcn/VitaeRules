from pydantic import BaseModel, Field
from typing import Optional

class SourceStrategy(BaseModel):
    """Strategy for a specific data source."""
    relevant: bool = Field(description="Whether this source should be searched")
    priority: str = Field(description="Priority level: HIGH, MEDIUM, or LOW")
    search_query: Optional[str] = Field(description="The specific search query to use for this source", default=None)
    reasoning: str = Field(description="Why this source is relevant or not")

class SearchStrategy(BaseModel):
    """Complete search strategy determining which sources to query."""
    memory: SourceStrategy = Field(description="Strategy for Memory source (notes, facts, history)")
    tasks: SourceStrategy = Field(description="Strategy for Tasks source (todos, deadlines)")
    lists: SourceStrategy = Field(description="Strategy for Lists source (shopping, collections)")
    overall_reasoning: str = Field(description="High-level explanation of the search strategy")
