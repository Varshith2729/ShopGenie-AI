import re
from typing import List, Dict, Any
from backend.app.models import KnowledgeBase

# Common conversational and generic stop words
STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "for", "to", "of", "and", "or",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "you", "your", "yours", "we", "our", "ours",
    "it", "its", "this", "that", "these", "those", "i", "me", "my", "myself",
    "us", "he", "him", "his", "she", "her", "they", "them", "what", "which",
    "who", "whom", "when", "where", "why", "how", "can", "could", "would",
    "should", "may", "might", "will", "shall", "want", "wanted", "wants",
    "need", "needs", "needed", "like", "tell", "show", "give", "know", "say",
    "please", "thanks", "thank", "hi", "hello", "hey", "yes", "no", "ok", "okay",
    "sir", "madam", "about", "any", "some", "shop", "store", "there", "here",
    "much", "many", "get", "got", "just", "also",
    "sell", "sells", "selling", "sold", "buy", "buying", "bought",
    "purchase", "purchased", "purchasing", "available", "availability", "stock"
}

# Semantic Intent Clusters
INTENT_CLUSTERS = {
    "address": {
        "address", "location", "located", "where", "place", "directions",
        "map", "landmark", "situated", "pincode", "zipcode", "city", "street", "road"
    },
    "timings": {
        "timing", "timings", "time", "hours", "open", "opening", "opens",
        "close", "closing", "closes", "closed", "schedule", "sunday", "saturday",
        "weekend", "holiday", "working"
    },
    "returns": {
        "return", "returns", "returned", "exchange", "exchanged", "exchanging",
        "refund", "refunds", "replacement", "warranty", "guarantee", "policy",
        "claim"
    },
    "delivery": {
        "delivery", "deliver", "delivering", "delivers", "shipping", "ship",
        "courier", "dispatch", "home delivery"
    },
    "payment": {
        "payment", "pay", "paying", "upi", "card", "cash", "credit", "debit",
        "gpay", "phonepe", "emi", "installments"
    },
    "products": {
        "product", "products", "item", "items", "brand", "brands", "model",
        "models", "stock", "available", "sell", "sells", "selling", "buy",
        "buying", "purchase", "price", "cost", "rate", "catalog", "mobile",
        "phone", "phones", "smartphone", "smartphones", "cloth", "clothes",
        "clothing", "dress", "dresses", "saree", "sarees", "shirt", "shirts",
        "pant", "pants", "apple", "samsung", "oneplus", "vivo", "oppo"
    }
}

# Synonyms for semantic domain matching
SYNONYM_GROUPS = [
    {"mobile", "phone", "phones", "smartphone", "smartphones", "cellphone", "cellphones", "handset", "device", "devices"},
    {"exchange", "exchanged", "exchanging", "return", "returns", "returned", "returning", "refund", "refunds", "replacement", "replace", "policy"},
    {"time", "timing", "timings", "hours", "open", "opening", "opens", "close", "closing", "closes", "schedule"},
    {"cloth", "clothes", "clothing", "dress", "dresses", "wear", "apparel", "garments", "fashion", "shirts", "shirt", "pant", "pants", "saree", "sarees", "ethnic"},
    {"deliver", "delivery", "shipping", "ship", "courier", "dispatch"},
    {"cost", "price", "pricing", "rate", "rates", "charge", "charges", "fee", "fees"},
    {"address", "location", "located", "place", "where", "landmark", "directions", "situated", "map"}
]

def tokenize(text: str, remove_stopwords: bool = True) -> set:
    """Normalize and tokenize text into lowercase word tokens."""
    if not text:
        return set()
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    tokens = {t for t in cleaned.split() if len(t) > 1}
    if remove_stopwords:
        tokens = {t for t in tokens if t not in STOP_WORDS}
    return tokens

def expand_synonyms(tokens: set) -> set:
    """Expand tokens with their domain synonyms."""
    expanded = set(tokens)
    for token in tokens:
        for group in SYNONYM_GROUPS:
            if token in group:
                expanded.update(group)
    return expanded

def detect_query_intents(query: str) -> set:
    """Detect high-level semantic intent clusters present in the query."""
    q_tokens = tokenize(query, remove_stopwords=False)
    q_lower = query.lower()
    intents = set()
    
    for intent_name, cluster_words in INTENT_CLUSTERS.items():
        if q_tokens.intersection(cluster_words):
            intents.add(intent_name)
        elif any(f" {w} " in f" {q_lower} " for w in cluster_words if " " in w):
            intents.add(intent_name)
            
    return intents

def search_shop_knowledge(shop_id: int, query: str, min_score: float = 0.35, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search and rank knowledge entries ONLY for the given shop_id.
    Strict tenant isolation is enforced at query time.
    Uses semantic intent detection, synonym expansion, and strict relevance ranking.
    """
    if not shop_id or not query or not query.strip():
        return []

    entries = KnowledgeBase.query.filter_by(shop_id=shop_id).all()
    if not entries:
        return []

    # Substantive query tokens
    substantive_tokens = tokenize(query, remove_stopwords=True)
    all_query_tokens = tokenize(query, remove_stopwords=False)
    effective_tokens = substantive_tokens if substantive_tokens else all_query_tokens
    if not effective_tokens:
        return []

    expanded_query_tokens = expand_synonyms(effective_tokens)
    query_intents = detect_query_intents(query)
    q_lower = query.lower().strip()

    scored_entries = []

    for entry in entries:
        title_sub = tokenize(entry.title, remove_stopwords=True)
        content_sub = tokenize(entry.content, remove_stopwords=True)
        category_sub = tokenize(entry.category, remove_stopwords=True)
        
        entry_all_tokens = tokenize(f"{entry.title} {entry.category} {entry.content}", remove_stopwords=False)
        t_lower = entry.title.lower()
        c_lower = entry.content.lower()
        cat_lower = entry.category.lower()

        # 1. Intent alignment check
        entry_intents = set()
        for intent_name, cluster_words in INTENT_CLUSTERS.items():
            if entry_all_tokens.intersection(cluster_words):
                entry_intents.add(intent_name)

        # Disallow false matches across incompatible intents
        # e.g., asking for address should NEVER match timings or products unless entry explicitly contains address
        if "address" in query_intents and "address" not in entry_intents:
            continue
        if "timings" in query_intents and "timings" not in entry_intents and not any(t in expanded_query_tokens for t in content_sub):
            continue

        # 2. Token overlap score (direct and synonym-based)
        title_overlap = len(effective_tokens.intersection(title_sub))
        content_overlap = len(effective_tokens.intersection(content_sub))
        category_overlap = len(effective_tokens.intersection(category_sub))

        expanded_title_overlap = len(expanded_query_tokens.intersection(title_sub))
        expanded_content_overlap = len(expanded_query_tokens.intersection(content_sub))

        # Check if there is genuine domain overlap
        has_direct_match = (title_overlap > 0 or content_overlap > 0 or category_overlap > 0)
        has_expanded_match = (expanded_title_overlap > 0 or expanded_content_overlap > 0)

        # 3. Exact phrase match bonus
        exact_phrase_bonus = 0.0
        cleaned_q = " ".join([w for w in q_lower.split() if w not in STOP_WORDS])
        if cleaned_q and len(cleaned_q) > 4 and (cleaned_q in c_lower or cleaned_q in t_lower):
            exact_phrase_bonus = 1.5
        elif q_lower in c_lower or q_lower in t_lower:
            exact_phrase_bonus = 1.0

        if not has_direct_match and not has_expanded_match and exact_phrase_bonus == 0.0:
            continue

        # 4. Weighted scoring
        raw_score = (
            (title_overlap * 2.5) + 
            (expanded_title_overlap * 1.5) +
            (category_overlap * 2.0) + 
            (content_overlap * 1.2) + 
            (expanded_content_overlap * 0.8) + 
            exact_phrase_bonus
        )

        total_tokens = max(len(effective_tokens), 1)
        normalized_score = raw_score / total_tokens

        # Intent agreement bonus
        shared_intents = query_intents.intersection(entry_intents)
        if shared_intents:
            normalized_score += 0.35 * len(shared_intents)

        # Direct token bonuses
        for token in effective_tokens:
            if token in t_lower:
                normalized_score += 0.3
            elif token in c_lower:
                normalized_score += 0.15

        if normalized_score >= min_score:
            scored_entries.append({
                "entry": entry,
                "score": round(normalized_score, 3)
            })

    # Sort descending by relevance score
    scored_entries.sort(key=lambda x: x["score"], reverse=True)
    return scored_entries[:limit]
