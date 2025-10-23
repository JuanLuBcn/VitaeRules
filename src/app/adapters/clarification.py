"""
Intelligent clarification detection and handling for conversational flow.

Handles:
- Ambiguous statements that could have multiple interpretations
- User corrections ("no, I meant...", "actually...")
- Cancel/undo commands at any stage
"""

import logging
import re
from typing import Optional, Dict, Any, List
from enum import Enum

from ..llm.service import get_llm_service

logger = logging.getLogger(__name__)


class ClarificationType(Enum):
    """Types of clarification needed."""
    AMBIGUOUS_INTENT = "ambiguous_intent"  # Could be note, task, or question
    AMBIGUOUS_CONTEXT = "ambiguous_context"  # Missing key context
    CORRECTION = "correction"  # User correcting previous input
    CANCEL = "cancel"  # User wants to abort


class ClarificationDetector:
    """
    Detects when user input needs clarification.
    
    Uses both heuristics and LLM to identify:
    - Ambiguous statements that could mean multiple things
    - User corrections to previous inputs
    - Cancel/undo commands
    """
    
    # Cancel/undo keywords (case-insensitive)
    CANCEL_KEYWORDS = {
        # English
        'cancel', 'stop', 'abort', 'quit', 'exit', 'forget it', 'never mind', 'nevermind',
        # Spanish
        'cancelar', 'parar', 'abortar', 'salir', 'olvídalo', 'déjalo', 'dejalo'
    }
    
    # Correction patterns
    CORRECTION_PATTERNS = [
        # English
        r'\bno[,\s]+(i\s+)?meant?\b',
        r'\bno[,\s]+(that\'?s\s+)?not\s+what\s+i\b',
        r'\bactually[,\s]+',
        r'\bi\s+mean\b',
        r'\bwhat\s+i\s+meant\s+(was|is)\b',
        r'\blet\s+me\s+clarify\b',
        r'\bcorrection[:,-]\s+',
        # Spanish
        r'\bno[,\s]+quier(o|a)\s+decir\b',
        r'\bno[,\s]+es\s+eso\b',
        r'\bno[,\s]+me\s+refier(o|a)\b',
        r'\ben\s+realidad[,\s]+',
        r'\blo\s+que\s+quier(o|a)\s+decir\b',
        r'\bcorrecci[oó]n[:,-]\s+',
    ]
    
    def __init__(self):
        """Initialize clarification detector."""
        self.llm_service = get_llm_service()
        self._correction_regex = re.compile(
            '|'.join(self.CORRECTION_PATTERNS),
            re.IGNORECASE
        )
    
    def is_cancel_command(self, text: str) -> bool:
        """
        Check if text is a cancel/undo command.
        
        Args:
            text: User input text
            
        Returns:
            True if user wants to cancel the conversation
        """
        text_lower = text.lower().strip()
        
        # Check exact matches and word boundaries
        for keyword in self.CANCEL_KEYWORDS:
            if keyword in text_lower:
                # Simple word boundary check
                if len(text_lower) == len(keyword):
                    return True
                # Check if surrounded by non-letter chars
                idx = text_lower.find(keyword)
                if idx >= 0:
                    before_ok = idx == 0 or not text_lower[idx-1].isalpha()
                    after_ok = (idx + len(keyword) >= len(text_lower) or 
                               not text_lower[idx + len(keyword)].isalpha())
                    if before_ok and after_ok:
                        return True
        
        return False
    
    def is_correction(self, text: str) -> bool:
        """
        Check if text is a correction to previous input.
        
        Detects phrases like:
        - "No, I meant..."
        - "Actually..."
        - "That's not what I meant"
        
        Args:
            text: User input text
            
        Returns:
            True if user is correcting previous input
        """
        return bool(self._correction_regex.search(text))
    
    def extract_corrected_info(self, text: str) -> str:
        """
        Extract the corrected information from a correction statement.
        
        Examples:
        - "No, I meant Alice" -> "Alice"
        - "Actually, it was at the office" -> "it was at the office"
        
        Args:
            text: Correction text
            
        Returns:
            Extracted corrected information
        """
        # Try to extract what comes after correction phrases
        match = self._correction_regex.search(text)
        if match:
            # Get everything after the correction phrase
            corrected = text[match.end():].strip()
            # Remove common leading words
            corrected = re.sub(r'^(it\s+was|that\s+was|es|fue)\s+', '', corrected, flags=re.IGNORECASE)
            return corrected if corrected else text
        
        return text
    
    def detect_ambiguity(
        self,
        text: str,
        current_intent: Optional[str] = None,
        collected_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if the statement is ambiguous and needs clarification.
        
        Uses LLM to analyze if the user's intent could have multiple interpretations.
        
        Args:
            text: User input text
            current_intent: Currently detected intent (if any)
            collected_data: Data collected so far
            
        Returns:
            Dict with clarification info if ambiguous, None otherwise
            {
                'type': ClarificationType,
                'question': str,  # Question to ask user
                'options': List[Dict],  # List of interpretation options
                'confidence': float  # How confident we are it's ambiguous (0-1)
            }
        """
        # Skip if text is very clear (question marks, specific keywords)
        if '?' in text or len(text.split()) > 15:
            return None
        
        # Use LLM to detect ambiguity
        prompt = self._build_ambiguity_prompt(text, current_intent, collected_data)
        
        try:
            result = self.llm_service.generate_json(
                prompt=prompt,
                system_prompt="You are an ambiguity detector. Return ONLY valid JSON with no markdown formatting."
            )
            
            if not result.get('is_ambiguous', False):
                return None
            
            # Only return if confidence is high enough
            if result.get('confidence', 0) < 0.6:
                return None
            
            clarification_type = (
                ClarificationType.AMBIGUOUS_INTENT 
                if result.get('ambiguity_type') == 'intent'
                else ClarificationType.AMBIGUOUS_CONTEXT
            )
            
            return {
                'type': clarification_type,
                'question': result.get('question', 'Could you clarify what you mean?'),
                'options': result.get('options', []),
                'confidence': result.get('confidence', 0.6)
            }
            
        except Exception as e:
            logger.error(f"Error detecting ambiguity: {e}")
            return None
    
    def _build_ambiguity_prompt(
        self,
        text: str,
        current_intent: Optional[str],
        collected_data: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for ambiguity detection."""
        
        prompt = f"""Analyze if this user statement is ambiguous and needs clarification.

User statement: "{text}"
"""
        
        if current_intent:
            prompt += f"Currently detected intent: {current_intent}\n"
        
        if collected_data:
            prompt += f"Collected data so far: {collected_data}\n"
        
        prompt += """
Determine if the statement is ambiguous in one of these ways:

1. AMBIGUOUS INTENT: Could be interpreted as different actions
   - Could be a note to save OR a question to answer
   - Could be a task to create OR just information to remember
   - Could be a greeting OR a command
   
2. AMBIGUOUS CONTEXT: Missing critical context
   - References "it" or "that" without clear antecedent
   - Mentions "him" or "her" without specifying who
   - Says "there" or "then" without clear reference
   - Too vague to act on ("do that thing")

Return JSON:
{
    "is_ambiguous": true/false,
    "confidence": 0.0-1.0 (how confident you are it's ambiguous),
    "ambiguity_type": "intent" or "context",
    "question": "Natural question to ask the user for clarification",
    "options": [
        {"label": "Option 1", "interpretation": "What this would mean", "intent": "note_taking"},
        {"label": "Option 2", "interpretation": "Alternative meaning", "intent": "task_create"}
    ]
}

If NOT ambiguous (clear statement with obvious intent), return:
{
    "is_ambiguous": false,
    "confidence": 0.0
}

Examples:

AMBIGUOUS (intent):
"Lunch tomorrow" -> Could be:
- Save note: "I had/will have lunch tomorrow"
- Create task: "Remember to have lunch tomorrow"
- Question: "When is lunch tomorrow?"

NOT AMBIGUOUS:
"I had lunch with Alice today" -> Clear note
"When did I meet Alice?" -> Clear question
"Remind me to call John tomorrow" -> Clear task
"""
        
        return prompt


class CorrectionHandler:
    """
    Handles user corrections to previously collected information.
    
    When user says "No, I meant X", this updates the session data
    with the corrected information.
    """
    
    def __init__(self):
        """Initialize correction handler."""
        self.llm_service = get_llm_service()
    
    def apply_correction(
        self,
        correction_text: str,
        last_question: str,
        collected_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply a correction to the collected data.
        
        Uses LLM to understand what the user is correcting and update the data.
        
        Args:
            correction_text: User's correction ("No, I meant Alice")
            last_question: Last question we asked
            collected_data: Current collected data
            
        Returns:
            Updated collected data
        """
        prompt = f"""The user is correcting their previous response.

Last question asked: "{last_question}"
User's correction: "{correction_text}"

Current collected data:
{collected_data}

Understand what the user is correcting and return the updated data.
Extract the corrected information and merge it with existing data.

Return JSON with the same structure as collected_data, but with corrected values.
Only update fields that are being corrected, keep others unchanged.

Expected fields:
- title: string
- content: string
- people: list of strings
- places: list of strings
- tags: list of strings
- due_date: string or null
- priority: string or null
- follow_up_responses: list of strings (append correction here)
"""
        
        try:
            updated_data = self.llm_service.generate_json(
                prompt=prompt,
                system_prompt="You are a data correction assistant. Return ONLY valid JSON with no markdown formatting."
            )
            
            # Ensure we don't lose data - merge carefully
            result = collected_data.copy()
            for key, value in updated_data.items():
                if value is not None:
                    result[key] = value
            
            # Always append to follow_up_responses
            if 'follow_up_responses' not in result:
                result['follow_up_responses'] = []
            if correction_text not in result['follow_up_responses']:
                result['follow_up_responses'].append(f"[CORRECTION] {correction_text}")
            
            logger.info(f"Applied correction, updated fields: {list(updated_data.keys())}")
            return result
            
        except Exception as e:
            logger.error(f"Error applying correction: {e}")
            # Fallback: just append to content
            result = collected_data.copy()
            result['content'] = f"{collected_data.get('content', '')} [Correction: {correction_text}]".strip()
            if 'follow_up_responses' not in result:
                result['follow_up_responses'] = []
            result['follow_up_responses'].append(f"[CORRECTION] {correction_text}")
            return result
