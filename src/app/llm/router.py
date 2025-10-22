"""Conversational router with LLM-based intent detection."""

from dataclasses import dataclass
from enum import Enum

from app.llm import LLMService
from app.tracing import get_tracer

logger = get_tracer()


class ConversationIntent(str, Enum):
    """Intent classification for conversational routing."""

    # Primary intents
    NOTE_TAKING = "note_taking"  # User wants to record information, memories, thoughts
    QUESTION = "question"  # User asking for information from their memory
    TASK_CREATE = "task_create"  # User wants to create a task
    TASK_QUERY = "task_query"  # User asking about tasks
    LIST_MANAGE = "list_manage"  # User managing lists (create, add items)
    REMINDER = "reminder"  # User wants to be reminded of something
    
    # Meta intents
    GREETING = "greeting"  # Casual greeting, small talk
    HELP = "help"  # User needs help using the bot
    UNCLEAR = "unclear"  # Cannot determine intent


@dataclass
class ConversationContext:
    """Context for conversation routing."""

    user_message: str
    chat_id: str
    user_id: str
    conversation_history: list[dict[str, str]] | None = None


@dataclass
class RoutingDecision:
    """Decision from conversational router."""

    intent: ConversationIntent
    confidence: float  # 0.0 to 1.0
    conversational_response: str  # Natural language response to user
    extracted_entities: dict[str, any]  # Entities extracted from message
    reasoning: str  # Why this intent was chosen
    requires_action: bool  # Whether to route to a crew
    target_crew: str | None  # "capture" or "retrieval" or None


class ConversationalRouter:
    """
    LLM-powered conversational router.
    
    Analyzes user messages to:
    1. Detect intent naturally
    2. Generate conversational responses
    3. Extract entities
    4. Decide on crew routing
    """

    def __init__(self, llm_service: LLMService):
        """Initialize router with LLM service."""
        self.llm = llm_service

    def route(self, context: ConversationContext) -> RoutingDecision:
        """
        Route a user message with conversational understanding.

        Args:
            context: Conversation context with message and history

        Returns:
            Routing decision with intent, response, and crew target
        """
        # No logging here - handled by telegram adapter

        # Build prompt for intent detection with conversation history
        prompt = self._build_routing_prompt(context)

        # Get LLM decision
        try:
            response = self.llm.generate_json(prompt, self._get_system_prompt())
            
            return RoutingDecision(
                intent=ConversationIntent(response.get("intent", "unclear")),
                confidence=response.get("confidence", 0.5),
                conversational_response=response.get("response", "I understand. Let me help you with that."),
                extracted_entities=response.get("entities", {}),
                reasoning=response.get("reasoning", ""),
                requires_action=response.get("requires_action", False),
                target_crew=response.get("target_crew"),
            )

        except Exception as e:
            print(f"  ⚠️  Routing fallback due to error: {str(e)}")
            # Fallback to safe response
            return RoutingDecision(
                intent=ConversationIntent.UNCLEAR,
                confidence=0.0,
                conversational_response="I'm not sure I understood that correctly. Could you rephrase?",
                extracted_entities={},
                reasoning=f"Error: {str(e)}",
                requires_action=False,
                target_crew=None,
            )

    def _get_system_prompt(self) -> str:
        """System prompt defining the router's personality and behavior."""
        return """You are a helpful, conversational AI assistant focused on note-taking and memory.

Your primary role is to help users:
1. Capture notes, memories, and thoughts naturally
2. Retrieve information from their personal memory
3. Manage tasks and reminders when needed

Personality:
- Warm and genuinely interested in the user's life
- Ask clarifying questions to understand context
- Show empathy and engagement
- Be concise but friendly

When analyzing messages, you must respond with VALID JSON (no comments, no trailing commas) containing:
{
  "intent": "note_taking|question|task_create|task_query|list_manage|reminder|greeting|help|unclear",
  "confidence": 0.0-1.0,
  "response": "Natural, conversational response to the user",
  "entities": {
    "title": "extracted title/topic",
    "content": "main content",
    "people": ["mentioned people"],
    "places": ["mentioned places"],
    "tags": ["relevant tags"],
    "priority": "high|medium|low",
    "due_date": "extracted date if any"
  },
  "reasoning": "Brief explanation of why you chose this intent",
  "requires_action": true,
  "target_crew": "capture"
}

CRITICAL: 
- Return ONLY valid JSON
- NO comments (// or /* */)
- NO trailing commas
- Use "null" for missing values
- All strings in double quotes

Intent Guidelines (CHECK IN THIS ORDER):

1. "list_manage": User managing lists - THIS IS CRITICAL TO DETECT FIRST
   - Keywords: "add to list", "añade a la lista", "a la lista de", "to the list", "from the list"
   - Examples: "Add milk to shopping list", "Añade mantequilla a la lista de la compra"
   - Spanish: "añade", "agrega", "quita" + "lista" = list_manage
   - English: "add", "remove" + "list" = list_manage
   → ALWAYS set requires_action=true and target_crew="capture"

2. "task_create": Explicit task creation (but NOT if it mentions "list")
   - Keywords: "remind me", "I need to", "I have to", "create task"
   - Examples: "Remind me to call John", "I need to finish the report"
   - CRITICAL: If message contains "list" or "lista" → use "list_manage" instead
   → ALWAYS set requires_action=true and target_crew="capture"

3. "note_taking": User shares information, memories, experiences, thoughts
   - Keywords: "remember that", "note:", general information sharing
   - Examples: "Remember that John likes coffee", "Note: meeting went well"
   → ALWAYS set requires_action=true and target_crew="capture"

4. "question": User asks "what", "when", "who", etc. about their past
   → ALWAYS set requires_action=true and target_crew="retrieval"

5. "task_query": Asking about existing tasks
   → ALWAYS set requires_action=true and target_crew="retrieval"

6. "reminder": Setting reminders for future
   → ALWAYS set requires_action=true and target_crew="capture"

7. "greeting": Casual chat, hello, how are you
   → Set requires_action=false and target_crew=null

8. "help": User needs instructions
   → Set requires_action=false and target_crew=null

9. "unclear": Cannot determine intent
   → Set requires_action=false and target_crew=null

CRITICAL RULES:
1. If message contains "a la lista" OR "to the list" OR "to list" OR "from list" → MUST be "list_manage"
2. If message contains "añade" + "lista" OR "add" + "list" → MUST be "list_manage", NOT "task_create"
3. Ignore politeness words ("por favor", "please") when detecting intent
4. If intent is note_taking, question, task_create, task_query, list_manage, or reminder → requires_action=true
5. Only greeting, help, and unclear should have requires_action=false

Response Guidelines:
- For notes: Show interest! "That sounds [interesting/important/exciting]! I've saved that."
- For questions: "Let me search my memory for that..."
- For tasks: "I'll help you track that. Should this be high priority?"
- For greetings: Be warm and friendly
- For unclear: Gently ask for clarification

Be CONVERSATIONAL, not robotic. This is a genuine conversation."""

    def _build_routing_prompt(self, context: ConversationContext) -> str:
        """Build the routing prompt with context."""
        prompt = f"User message: \"{context.user_message}\"\n\n"

        # Add conversation history if available
        if context.conversation_history and len(context.conversation_history) > 0:
            prompt += "Recent conversation:\n"
            for msg in context.conversation_history[-3:]:  # Last 3 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prompt += f"{role}: {content}\n"
            prompt += "\n"

        prompt += "Analyze this message and provide your routing decision in JSON format."

        return prompt
