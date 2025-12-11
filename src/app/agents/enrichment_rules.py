"""Enrichment rules - define when and how to ask for additional context."""

from .enrichment_types import EnrichmentRule


def _people_priority(data: dict) -> str:
    """Determine priority for asking about people."""
    text = data.get("text", "") or data.get("title", "") or data.get("item_text", "")
    text = text.lower()

    # High priority keywords indicate people involvement
    high_keywords = ["para", "con", "llamar", "reunión", "hablar", "enviar", "decir"]
    if any(word in text for word in high_keywords):
        return "high"

    # Medium priority - might involve people
    medium_keywords = ["compartir", "avisar", "recordar"]
    if any(word in text for word in medium_keywords):
        return "medium"

    return "low"


def _location_priority(data: dict) -> str:
    """Determine priority for asking about location."""
    text = data.get("text", "") or data.get("title", "") or data.get("item_text", "")
    text = text.lower()

    # High priority - clearly location-based
    high_keywords = [
        "comprar",
        "ir a",
        "en el",
        "en la",
        "reunión",
        "visitar",
        "recoger",
        "llevar",
    ]
    if any(word in text for word in high_keywords):
        return "high"

    # Medium priority - might benefit from location
    medium_keywords = ["encontrar", "buscar", "conseguir"]
    if any(word in text for word in medium_keywords):
        return "medium"

    return "low"


def _tags_priority(data: dict) -> str:
    """Determine priority for asking about tags."""
    # Tags are always low priority (nice to have)
    # Only ask if we have extra turns available
    return "low"


def _due_date_priority(data: dict) -> str:
    """Determine priority for asking about due date (tasks only)."""
    # Tasks should almost always have a due date
    text = data.get("title", "")
    text = text.lower()

    # Some tasks are clearly time-sensitive
    urgent_keywords = ["urgente", "hoy", "mañana", "pronto", "ya"]
    if any(word in text for word in urgent_keywords):
        return "high"

    return "medium"  # Still ask, but less urgently


def _priority_level_priority(data: dict) -> str:
    """Determine if we should ask about task priority."""
    # Only if task seems urgent
    text = data.get("title", "")
    text = text.lower()

    urgent_keywords = ["urgente", "importante", "crítico", "ya"]
    if any(word in text for word in urgent_keywords):
        return "skip"  # Already clear it's high priority

    return "low"  # Nice to have


# Define all enrichment rules
PEOPLE_RULE = EnrichmentRule(
    field_name="people",
    agent_types=["list", "task", "note"],
    priority_fn=_people_priority,
    question_template="¿Con quién está relacionado esto? 👥",
    follow_up="Puedes mencionar varios nombres: 'Juan y María' (o escribe 'nadie')",
    examples=["Juan", "María", "Juan y Pedro", "el equipo", "nadie"],
)

LOCATION_RULE = EnrichmentRule(
    field_name="location",
    agent_types=["list", "task", "note"],
    priority_fn=_location_priority,
    question_template="¿En qué lugar? 📍",
    follow_up="Ejemplo: 'Mercadona Gran Vía' o comparte tu ubicación (o escribe 'ninguno')",
    examples=["Mercadona", "Oficina central", "Casa de Juan", "ninguno"],
)

TAGS_RULE = EnrichmentRule(
    field_name="tags",
    agent_types=["list", "task", "note"],
    priority_fn=_tags_priority,
    question_template="¿Quieres añadir etiquetas? 🏷️",
    follow_up="Ejemplo: 'urgente, trabajo' (o escribe 'no')",
    examples=["urgente", "trabajo", "personal", "salud", "no"],
)

DUE_DATE_RULE = EnrichmentRule(
    field_name="due_at",
    agent_types=["task"],
    priority_fn=_due_date_priority,
    question_template="¿Para cuándo es esta tarea? 📅",
    follow_up="Ejemplo: 'mañana', 'viernes', 'en 3 días', '25/10/2025'",
    examples=["mañana", "el viernes", "en 2 días", "25/10/2025"],
)

PRIORITY_RULE = EnrichmentRule(
    field_name="priority",
    agent_types=["task"],
    priority_fn=_priority_level_priority,
    question_template="¿Qué tan importante es? ⚡",
    follow_up="Opciones: baja, media, alta, urgente",
    examples=["baja", "media", "alta", "urgente"],
)


# All rules in priority order (ask high priority first)
ALL_RULES = [
    DUE_DATE_RULE,  # Tasks: deadline first
    LOCATION_RULE,  # Then location (often important)
    PEOPLE_RULE,  # Then people involved
    PRIORITY_RULE,  # Priority level
    TAGS_RULE,  # Tags last (least important)
]


def get_rules_for_agent(agent_type: str) -> list[EnrichmentRule]:
    """Get applicable rules for an agent type."""
    return [rule for rule in ALL_RULES if agent_type in rule.agent_types]


def get_rule_by_field(field_name: str) -> EnrichmentRule | None:
    """Get rule for a specific field."""
    for rule in ALL_RULES:
        if rule.field_name == field_name:
            return rule
    return None
