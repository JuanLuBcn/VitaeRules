"""Conversational enrichment for gathering complete information."""

from typing import Any

from app.llm import get_llm_service
from app.tracing import get_tracer

logger = get_tracer()


class InformationEnricher:
    """
    Intelligently asks follow-up questions to enrich captured information.
    
    Analyzes user input to detect missing details and generates natural
    follow-up questions to gather complete context.
    """
    
    def __init__(self):
        """Initialize enricher."""
        self.llm_service = get_llm_service()
    
    def needs_enrichment(self, intent: str, collected_data: dict[str, Any]) -> bool:
        """
        Determine if the information needs enrichment.
        
        Args:
            intent: User's intent (note_taking, task_create, etc.)
            collected_data: Data collected so far
            
        Returns:
            True if follow-up questions would be beneficial
        """
        # Skip enrichment for certain intents
        if intent in ["question", "greeting", "help", "unclear"]:
            return False
        
        # For note_taking - check if we have basic details
        if intent == "note_taking":
            title = collected_data.get("title", "")
            content = collected_data.get("content", "")
            
            # If it's very short, might benefit from more details
            if len(content) < 20:
                return True
            
            # Check if it mentions people/places but doesn't extract them
            text = f"{title} {content}".lower()
            has_people_mentions = any(word in text for word in ["with", "con", "met", "vi a"])
            has_location_mentions = any(word in text for word in ["at", "en", "visited", "visité"])
            
            people = collected_data.get("people", [])
            places = collected_data.get("places", [])
            
            if has_people_mentions and not people:
                return True
            if has_location_mentions and not places:
                return True
        
        # For tasks - check if we have due date
        if intent in ["task_create", "task.create"]:
            due_date = collected_data.get("due_date") or collected_data.get("due_at")
            if not due_date:
                return True
        
        return False
    
    def generate_follow_up_questions(
        self, intent: str, original_message: str, collected_data: dict[str, Any], follow_up_count: int
    ) -> str | None:
        """
        Generate intelligent follow-up questions using LLM.
        
        Args:
            intent: User's intent
            original_message: Original user message
            collected_data: Data collected so far
            follow_up_count: Number of follow-ups already asked
            
        Returns:
            Follow-up question or None if no more questions needed
        """
        # Maximum 2-3 questions
        if follow_up_count >= 2:
            return None
        
        # Build prompt for LLM
        prompt = self._build_enrichment_prompt(intent, original_message, collected_data, follow_up_count)
        
        system_prompt = """You are a helpful assistant that asks clarifying questions to gather complete information.
Ask natural, conversational questions - one at a time.
If the user has already provided enough detail, return "SKIP" to proceed without more questions.
Be brief and friendly."""
        
        try:
            response = self.llm_service.generate(prompt, system_prompt)
            
            # Check if LLM says to skip
            if response.strip().upper() == "SKIP" or "skip" in response.lower()[:20]:
                return None
            
            return response.strip()
        
        except Exception as e:
            logger.error(f"Follow-up generation failed: {e}")
            return None
    
    def _build_enrichment_prompt(
        self, intent: str, original_message: str, collected_data: dict[str, Any], follow_up_count: int
    ) -> str:
        """Build prompt for generating follow-up questions."""
        
        if intent == "note_taking":
            return f"""User wants to save this memory: "{original_message}"

Already collected:
- Title: {collected_data.get('title', 'N/A')}
- Content: {collected_data.get('content', original_message)}
- People: {collected_data.get('people', [])}
- Places: {collected_data.get('places', [])}
- Tags: {collected_data.get('tags', [])}

This is follow-up #{follow_up_count + 1}.

Generate ONE brief, natural question to gather more useful context.
Focus on:
- Who was involved (if people mentioned but not extracted)
- Where it happened (if location mentioned but not extracted)  
- Any important details they might want to remember

If the information is already complete enough, respond with "SKIP".

Your question:"""
        
        elif intent in ["task_create", "task.create"]:
            return f"""User wants to create this task: "{original_message}"

Already collected:
- Task: {collected_data.get('title', original_message)}
- Due date: {collected_data.get('due_date', 'Not specified')}
- Priority: {collected_data.get('priority', 'medium')}

This is follow-up #{follow_up_count + 1}.

Generate ONE brief question to gather missing details.
Focus on:
- When does this need to be done? (if no due date)
- How important/urgent is this? (if unclear)

If enough information is provided, respond with "SKIP".

Your question:"""
        
        else:
            # Generic enrichment
            return f"""User said: "{original_message}"
Intent: {intent}
Already collected: {collected_data}

This is follow-up #{follow_up_count + 1}.

Generate ONE brief, natural clarifying question to gather more complete information.
If already complete, respond with "SKIP".

Your question:"""
    
    def extract_info_from_response(
        self, intent: str, follow_up_response: str, collected_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Extract structured information from a follow-up response.
        
        Args:
            intent: User's intent
            follow_up_response: User's response to follow-up question
            collected_data: Existing collected data
            
        Returns:
            Updated collected data with extracted information
        """
        # Use LLM to extract information from the response
        prompt = f"""Extract structured information from this follow-up response:

Response: "{follow_up_response}"

Context - User is trying to {intent}.
Already collected: {collected_data}

Extract and return ONLY a JSON object with any new information found:
{{
    "people": ["list of people mentioned"],
    "places": ["list of places mentioned"],
    "tags": ["relevant tags"],
    "due_date": "extracted date if any",
    "priority": "high/medium/low if mentioned",
    "additional_context": "any other important details"
}}

If nothing significant to extract, return {{}}.

JSON:"""
        
        system_prompt = """You extract structured information from text.
Return ONLY valid JSON, no explanations or markdown formatting."""
        
        try:
            response = self.llm_service.generate_json(prompt, system_prompt)
            
            # Merge with existing data
            updated_data = collected_data.copy()
            
            # Merge people
            if response.get("people"):
                existing_people = set(updated_data.get("people", []))
                new_people = set(response["people"])
                updated_data["people"] = list(existing_people | new_people)
            
            # Merge places
            if response.get("places"):
                existing_places = set(updated_data.get("places", []))
                new_places = set(response["places"])
                updated_data["places"] = list(existing_places | new_places)
            
            # Merge tags
            if response.get("tags"):
                existing_tags = set(updated_data.get("tags", []))
                new_tags = set(response["tags"])
                updated_data["tags"] = list(existing_tags | new_tags)
            
            # Update other fields
            if response.get("due_date"):
                updated_data["due_date"] = response["due_date"]
            
            if response.get("priority"):
                updated_data["priority"] = response["priority"]
            
            if response.get("additional_context"):
                # Append to content
                current_content = updated_data.get("content", "")
                additional = response["additional_context"]
                updated_data["content"] = f"{current_content}\n{additional}".strip()
            
            # Store the follow-up response itself
            follow_up_responses = updated_data.get("follow_up_responses", [])
            follow_up_responses.append(follow_up_response)
            updated_data["follow_up_responses"] = follow_up_responses
            
            return updated_data
        
        except Exception as e:
            logger.error(f"Info extraction failed: {e}")
            # Just append the response as additional context
            updated_data = collected_data.copy()
            follow_up_responses = updated_data.get("follow_up_responses", [])
            follow_up_responses.append(follow_up_response)
            updated_data["follow_up_responses"] = follow_up_responses
            
            current_content = updated_data.get("content", "")
            updated_data["content"] = f"{current_content}\n{follow_up_response}".strip()
            
            return updated_data
