"""EnrichmentAgent - Intelligently asks follow-up questions for richer context."""

import json
from typing import Any

from app.llm import LLMService
from app.tracing import get_tracer

from .enrichment_rules import ALL_RULES, get_rule_by_field, get_rules_for_agent
from .enrichment_state import ConversationStateManager
from .enrichment_types import AgentResponse, EnrichmentContext


class EnrichmentAgent:
    """
    Agent that asks smart follow-up questions to gather missing context.

    This agent analyzes user input and determines what additional information
    would be valuable (people, location, tags, etc.), then conducts a natural
    multi-turn conversation to gather it.
    """

    def __init__(self, llm_service: LLMService):
        """
        Initialize EnrichmentAgent.

        Args:
            llm_service: LLM service for intelligent extraction
        """
        self.llm = llm_service
        self.tracer = get_tracer()
        self.state_manager = ConversationStateManager()

    async def analyze_and_start(
        self, agent_type: str, operation: str, data: dict, chat_id: str
    ) -> AgentResponse | None:
        """
        Analyze data and potentially start enrichment conversation.

        Args:
            agent_type: Type of agent (list, task, note)
            operation: Operation to perform
            data: Extracted data from user input
            chat_id: Chat identifier

        Returns:
            AgentResponse with enrichment question, or None if no enrichment needed
        """
        self.tracer.debug(f"Analyzing for enrichment: {agent_type}/{operation}")

        # Detect missing fields
        missing_fields = await self._detect_missing_fields(agent_type, data)

        if not missing_fields:
            self.tracer.debug("No enrichment needed - all fields present")
            return None

        # Create enrichment context
        context = await self.state_manager.create_context(
            chat_id=chat_id, agent_type=agent_type, operation=operation, data=data
        )
        context.missing_fields = missing_fields

        # Generate first question
        response = await self._generate_next_question(context)

        if response:
            await self.state_manager.update_context(chat_id, context)
            return response

        return None

    async def process_response(
        self, user_message: str, chat_id: str
    ) -> AgentResponse:
        """
        Process user's response to an enrichment question.

        Args:
            user_message: User's response
            chat_id: Chat identifier

        Returns:
            AgentResponse with next question or completion
        """
        context = await self.state_manager.get_context(chat_id)

        if not context:
            raise ValueError(f"No active enrichment context for chat {chat_id}")

        # Check if user wants to skip
        if self._is_skip_response(user_message):
            self.tracer.info("User requested to skip enrichment")
            return await self._complete_enrichment(context)

        # Extract data from response
        current_field = context.asked_fields[-1] if context.asked_fields else None

        if current_field:
            extracted_value = await self._extract_field_value(
                current_field, user_message
            )

            if extracted_value is not None:
                context.add_gathered_data(current_field, extracted_value)
                self.tracer.debug(
                    f"Extracted {current_field} = {extracted_value}"
                )

        # Check if we're done
        if context.is_complete():
            return await self._complete_enrichment(context)

        # Ask next question
        response = await self._generate_next_question(context)

        if response:
            await self.state_manager.update_context(chat_id, context)
            return response

        # No more questions, complete
        return await self._complete_enrichment(context)

    async def _detect_missing_fields(
        self, agent_type: str, data: dict
    ) -> list[str]:
        """
        Detect which fields are missing and should be enriched.

        Args:
            agent_type: Type of agent
            data: Current data

        Returns:
            List of missing field names in priority order
        """
        missing = []
        rules = get_rules_for_agent(agent_type)

        for rule in rules:
            if rule.should_ask(agent_type, data):
                priority = rule.get_priority(data)
                if priority != "skip":
                    missing.append(rule.field_name)
                    self.tracer.debug(
                        f"Missing field: {rule.field_name} (priority: {priority})"
                    )

        return missing

    async def _generate_next_question(
        self, context: EnrichmentContext
    ) -> AgentResponse | None:
        """
        Generate the next enrichment question.

        Args:
            context: Current enrichment context

        Returns:
            AgentResponse with question, or None if no more questions
        """
        next_field = context.next_field_to_ask()

        if not next_field:
            return None

        rule = get_rule_by_field(next_field)

        if not rule:
            return None

        # Mark this field as asked
        context.mark_field_asked(next_field)

        # Build question message
        message = rule.question_template

        if rule.follow_up and context.turn_count == 1:
            # Show examples on first question
            message += f"\n\n💡 {rule.follow_up}"

        self.tracer.info(f"Asking about field: {next_field}")

        return AgentResponse(
            message=message,
            success=True,
            needs_enrichment=True,
        )

    async def _extract_field_value(
        self, field_name: str, user_response: str
    ) -> Any:
        """
        Extract structured value from user's free-text response.

        Args:
            field_name: Field being extracted
            user_response: User's text response

        Returns:
            Extracted value (can be string, list, None)
        """
        # Check for negative responses
        negative_responses = [
            "no",
            "nadie",
            "ninguno",
            "ninguna",
            "omitir",
            "skip",
            "nada",
        ]
        if user_response.lower().strip() in negative_responses:
            return None

        # Use LLM for intelligent extraction
        prompt = self._build_extraction_prompt(field_name, user_response)

        try:
            result = self.llm.generate(prompt)
            extracted = self._parse_extraction_result(result, field_name)
            return extracted

        except Exception as e:
            self.tracer.error(f"Failed to extract {field_name}: {e}")
            # Fallback: use raw response
            return self._fallback_extraction(field_name, user_response)

    def _build_extraction_prompt(self, field_name: str, user_response: str) -> str:
        """Build LLM prompt for extracting field value."""
        if field_name == "people":
            return f"""
Extrae los nombres de personas de esta respuesta.

RESPUESTA DEL USUARIO: "{user_response}"

Devuelve SOLO un array JSON de nombres, por ejemplo: ["Juan", "María"]
Si no hay nombres, devuelve: []

Ejemplos:
"Juan y María" → ["Juan", "María"]
"Juan" → ["Juan"]
"el equipo" → ["el equipo"]
"nadie" → []
"""

        elif field_name == "location":
            return f"""
Extrae el nombre del lugar de esta respuesta.

RESPUESTA DEL USUARIO: "{user_response}"

Devuelve SOLO el nombre del lugar como string, por ejemplo: "Mercadona Gran Vía"
Si no hay lugar específico, devuelve: null

Ejemplos:
"Mercadona de Gran Vía" → "Mercadona Gran Vía"
"en la oficina" → "la oficina"
"ninguno" → null
"""

        elif field_name == "tags":
            return f"""
Extrae etiquetas/categorías de esta respuesta.

RESPUESTA DEL USUARIO: "{user_response}"

Devuelve SOLO un array JSON de etiquetas, por ejemplo: ["urgente", "trabajo"]
Si no hay etiquetas, devuelve: []

Ejemplos:
"urgente y trabajo" → ["urgente", "trabajo"]
"personal" → ["personal"]
"no" → []
"""

        elif field_name == "due_at":
            return f"""
Extrae la fecha/plazo de esta respuesta.

RESPUESTA DEL USUARIO: "{user_response}"

Devuelve el plazo en formato ISO o descripción textual.

Ejemplos:
"mañana" → "mañana"
"el viernes" → "viernes"
"25/10/2025" → "2025-10-25"
"en 3 días" → "en 3 días"
"""

        elif field_name == "priority":
            return f"""
Extrae el nivel de prioridad de esta respuesta.

RESPUESTA DEL USUARIO: "{user_response}"

Devuelve un número: 0=baja, 1=media, 2=alta, 3=urgente

Ejemplos:
"baja" → 0
"media" → 1
"alta" → 2
"urgente" → 3
"""

        # Default
        return f'Extrae "{field_name}" de: "{user_response}"'

    def _parse_extraction_result(self, llm_result: str, field_name: str) -> Any:
        """Parse LLM extraction result."""
        llm_result = llm_result.strip()

        # Handle null/None
        if llm_result.lower() in ["null", "none"]:
            return None

        # Try to parse as JSON (for arrays)
        if llm_result.startswith("[") or llm_result.startswith("{"):
            try:
                return json.loads(llm_result)
            except json.JSONDecodeError:
                pass

        # Priority is a number
        if field_name == "priority":
            try:
                return int(llm_result)
            except ValueError:
                # Map text to number
                priority_map = {"baja": 0, "media": 1, "alta": 2, "urgente": 3}
                return priority_map.get(llm_result.lower(), 1)

        # Default: return as string
        return llm_result

    def _fallback_extraction(self, field_name: str, user_response: str) -> Any:
        """Simple fallback extraction without LLM."""
        response = user_response.strip()

        if field_name == "people":
            # Split by common separators
            names = [
                name.strip()
                for name in response.replace(" y ", ",").split(",")
                if name.strip()
            ]
            return names if names else []

        elif field_name == "tags":
            # Split by commas or spaces
            tags = [
                tag.strip()
                for tag in response.replace(",", " ").split()
                if tag.strip()
            ]
            return tags if tags else []

        # Default: return as-is
        return response

    def _is_skip_response(self, message: str) -> bool:
        """Check if user wants to skip enrichment."""
        skip_keywords = [
            "cancelar",
            "omitir",
            "skip",
            "no más",
            "ya está",
            "suficiente",
            "listo",
        ]
        message_lower = message.lower().strip()
        return any(keyword in message_lower for keyword in skip_keywords)

    async def _complete_enrichment(
        self, context: EnrichmentContext
    ) -> AgentResponse:
        """
        Complete enrichment and return final data.

        Args:
            context: Enrichment context

        Returns:
            AgentResponse with completion message and final data
        """
        # Remove context from active
        await self.state_manager.complete_context(context.chat_id)

        final_data = context.get_final_data()

        self.tracer.info(
            f"Enrichment complete. Gathered: {list(context.gathered_data.keys())}"
        )

        # Build summary message
        summary_parts = []
        if context.gathered_data.get("people"):
            people = context.gathered_data["people"]
            if isinstance(people, list):
                summary_parts.append(f"👥 Con: {', '.join(people)}")
            else:
                summary_parts.append(f"👥 Con: {people}")

        if context.gathered_data.get("location"):
            summary_parts.append(f"📍 En: {context.gathered_data['location']}")

        if context.gathered_data.get("tags"):
            tags = context.gathered_data["tags"]
            if isinstance(tags, list):
                summary_parts.append(f"🏷️ Tags: {', '.join(tags)}")

        summary = "\n".join(summary_parts) if summary_parts else ""

        message = "¡Perfecto! " + (summary or "Continuando...")

        return AgentResponse(
            message=message,
            success=True,
            needs_enrichment=False,
            extracted_data=final_data,
            operation=context.operation,
        )
