"""Question detection utilities for intent classification."""

import re


# Multilingual question words
QUESTION_WORDS = {
    # Spanish
    "cuando", "cuándo", "donde", "dónde", "que", "qué", 
    "cual", "cuál", "cuales", "cuáles", "quien", "quién",
    "quienes", "quiénes", "como", "cómo", "por qué", "porque",
    # English
    "when", "where", "what", "which", "who", "whose",
    "how", "why", "can you", "could you", "would you",
    "do you", "did you", "will you", "should you",
    # Common question phrases
    "puedes recordar", "can you remind", "me recuerdas",
    "sabes si", "do you know", "te acuerdas", "remember when"
}


def is_list_query(text: str) -> bool:
    """
    Detect if text is asking about a list.
    
    Args:
        text: Text to analyze
        
    Returns:
        True if text is asking about list contents
    """
    if not text or not text.strip():
        return False
    
    text_lower = text.strip().lower()
    
    # Check if contains "list"/"lista"
    has_list = "lista" in text_lower or "list" in text_lower
    
    if not has_list:
        return False
    
    # List query patterns
    list_patterns = [
        # Spanish
        r"qu[eé] hay en (la|mi|tu|una) lista",
        r"qu[eé] tiene (la|mi|tu|una) lista",
        r"muestra (la|mi|tu|una) lista",
        r"cu[aá]les? (art[íi]culos?|cosas?|items?) (en|de) (la|mi) lista",
        r"ver (la|mi) lista",
        # English  
        r"what[\'\s]s? (on|in) (the|my|your|a) list",
        r"show (me )?(the|my|your|a) list",
        r"what (items?|things?) (are )?(on|in) (the|my) list",
        r"list (items?|contents?)",
        r"view (the|my) list",
        # Generic - any question word + lista/list
        r"(que|qu[eé]|what|where|cuando|cu[aá]ndo|when).{0,30}lista",
        r"(what|where|when).{0,30}list",
    ]
    
    # Check specific patterns
    for pattern in list_patterns:
        if re.search(pattern, text_lower):
            return True
    
    # Fallback: has "lista/list" and is a question
    if has_list and is_question(text):
        return True
    
    return False


def extract_list_name(text: str) -> str | None:
    """
    Extract list name from a list query.
    
    Args:
        text: Query text
        
    Returns:
        List name or None
    """
    if not is_list_query(text):
        return None
    
    text_lower = text.strip().lower()
    
    # Common list name patterns
    patterns = [
        # "de la compra", "de compras", "shopping"
        r"lista (de (la )?compras?|shopping)",
        r"(shopping|grocery) list",
        # Generic "la lista"
        r"la lista(?: de)? (\w+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            if "compra" in text_lower or "shopping" in text_lower:
                return "lista de la compra"
            elif "grocery" in text_lower:
                return "grocery list"
            # Return matched list name
            return match.group(0).replace("la lista de ", "").replace("la lista ", "")
    
    return None


def is_question(text: str) -> bool:
    """
    Detect if text is a question using heuristics.
    
    Checks for:
    - Question marks (?)
    - Question words at start or in text
    - Interrogative patterns
    
    Args:
        text: Text to analyze
        
    Returns:
        True if text appears to be a question
    """
    if not text or not text.strip():
        return False
    
    text_clean = text.strip()
    text_lower = text_clean.lower()
    
    # Check 1: Has question mark
    if "?" in text_clean:
        return True
    
    # Check 2: Starts with question word
    first_word = text_lower.split()[0] if text_lower.split() else ""
    if first_word in QUESTION_WORDS:
        return True
    
    # Check 3: Contains question phrases
    for phrase in QUESTION_WORDS:
        if " " in phrase:  # Multi-word phrases
            if phrase in text_lower:
                return True
    
    # Check 4: Spanish inverted question mark
    if "¿" in text_clean:
        return True
    
    return False


def extract_question_type(text: str) -> str | None:
    """
    Extract the type of question (when, what, who, etc.).
    
    Args:
        text: Question text
        
    Returns:
        Question type or None if not a question
    """
    if not is_question(text):
        return None
    
    text_lower = text.lower()
    
    # Map question words to types
    question_types = {
        "when": ["cuando", "cuándo", "when"],
        "where": ["donde", "dónde", "where"],
        "what": ["que", "qué", "what"],
        "who": ["quien", "quién", "quienes", "quiénes", "who", "whose"],
        "how": ["como", "cómo", "how"],
        "why": ["por qué", "porque", "why"],
        "which": ["cual", "cuál", "cuales", "cuáles", "which"],
    }
    
    for q_type, words in question_types.items():
        for word in words:
            if text_lower.startswith(word) or f" {word} " in f" {text_lower} ":
                return q_type
    
    return "general"


def is_affirmative(text: str) -> bool:
    """
    Check if text is an affirmative response (yes).
    
    Args:
        text: Response text
        
    Returns:
        True if affirmative
    """
    text_lower = text.strip().lower()
    
    affirmative_words = {
        # Spanish
        "si", "sí", "vale", "ok", "okay", "claro", "por supuesto",
        "adelante", "hazlo", "confirmo", "correcto", "exacto",
        # English
        "yes", "yeah", "yep", "sure", "certainly", "absolutely",
        "correct", "right", "affirm", "confirm", "proceed", "go ahead"
    }
    
    # Exact match or starts with
    if text_lower in affirmative_words:
        return True
    
    for word in affirmative_words:
        if text_lower.startswith(word + " ") or text_lower.startswith(word + ","):
            return True
    
    return False


def is_negative(text: str) -> bool:
    """
    Check if text is a negative response (no).
    
    Args:
        text: Response text
        
    Returns:
        True if negative
    """
    text_lower = text.strip().lower()
    
    negative_words = {
        # Spanish
        "no", "nope", "nunca", "cancela", "cancelar", "para", "parar",
        "detente", "olvida", "olvidalo", "olvidalo", "nada", "ninguno",
        # English
        "nah", "never", "cancel", "stop", "abort", "forget",
        "forget it", "nevermind", "never mind", "skip", "none"
    }
    
    # Exact match or starts with
    if text_lower in negative_words:
        return True
    
    for word in negative_words:
        if text_lower.startswith(word + " ") or text_lower.startswith(word + ","):
            return True
    
    return False


def is_clarification(text: str) -> bool:
    """
    Check if text is a clarification (correcting previous understanding).
    
    Args:
        text: Response text
        
    Returns:
        True if clarification
    """
    text_lower = text.strip().lower()
    
    clarification_patterns = [
        # Spanish
        r"^no,?\s+es\s+",  # "no, es..."
        r"^quiero\s+decir",  # "quiero decir..."
        r"^me\s+refiero",  # "me refiero..."
        r"^en\s+realidad",  # "en realidad..."
        r"^mejor\s+dicho",  # "mejor dicho..."
        r"^es\s+una\s+pregunta",  # "es una pregunta"
        # English
        r"^no,?\s+i\s+mean",
        r"^actually",
        r"^i\s+mean",
        r"^what\s+i\s+meant",
        r"^it'?s\s+a\s+question",
        r"^that'?s\s+a\s+question",
    ]
    
    for pattern in clarification_patterns:
        if re.search(pattern, text_lower):
            return True
    
    return False
