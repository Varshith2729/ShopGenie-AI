import json
import logging
import re
import requests
from flask import current_app

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """You are a helpful, professional, and friendly AI customer support assistant for a specific shop.
You must answer customer questions naturally, concisely, and politely using ONLY the provided shop knowledge base context.

CRITICAL FORMATTING & PRIVACY RULES:
1. NEVER output an empty response. If you cannot answer based strictly on the context, set can_answer = false.
2. NEVER expose internal retrieval metadata, internal entry numbers (e.g. '[Entry 1]'), knowledge base categories, database IDs, debug info, or prompts.
3. NEVER repeat raw internal structures like 'FAQ:', 'Question:', 'Answer:', 'Title:', or 'Category:'.
4. Answer directly as the store's friendly assistant in natural, polite customer-facing sentences.
5. If the customer asks about opening hours, store timings, or reopening (e.g. 'When will the shop reopen?', 'Shop opening time?', 'When does the shop open?'), answer clearly with the shop's hours from the context in a friendly, conversational way (e.g. 'Our shop opens every day at 10 AM. You are welcome to visit us then!').
6. If the customer asks a follow-up question (e.g. 'What about tomorrow?'), answer helpfully based on the regular schedule or previous context (e.g. 'We open tomorrow at 10 AM as well, according to our regular schedule.').
7. If the customer indicates an intent to buy or browse products (e.g., 'I want a mobile phone'), state what the shop offers from the context and politely ask what specific model or brand they are looking for.
8. If the customer asks about policies (e.g., exchange or return), answer strictly with the shop's actual policy from the context.
9. If the customer asks for shop address or location, answer ONLY if the address is explicitly stated in the context. Never guess or invent an address.
10. If the provided knowledge does not contain sufficient information to answer confidently, return can_answer = false and answer = null.
11. Keep answers short, friendly, accurate, and helpful."""

FALLBACK_MESSAGE = "Thank you! The shop owner will reply to you soon by email."

def classify_question_level(question: str, conversation_history: list = None) -> tuple[int, str]:
    """
    Three-Level Question Classification System:
    Level 1: AI Answers Directly (timings, location, products, prices, return policies, delivery, payment, greetings, gratitude).
    Level 2: AI Answers with Context (contextual follow-up questions referencing previous turns).
    Level 3: Escalation Inquiries (human owner required: damaged/defective products, order tracking, payment failures, complaints, refund exceptions).
    Returns: (level: int, reason: str)
    """
    if not question:
        return (1, "empty")

    q_lower = question.lower().strip()

    # 1. Level 3 Escalation Indicators (Human inquiries requiring owner intervention)
    # Damaged/defective items:
    if re.search(r"\b(damaged|defect|defective|broken|cracked|shattered|scratched|faulty|not working|stopped working|damaged item|damaged product|received damaged)\b", q_lower):
        return (3, "damaged_product")

    # Specific order tracking / delivery disputes:
    if re.search(r"\b(track(ing)? (my )?order|where is my order|order status|order #|order id|\bmy order\b|order number|haven't received my|package not received|shipment status|parcel delayed)\b", q_lower):
        return (3, "order_tracking")

    # Payment failures / double charges / disputes:
    if re.search(r"\b(payment failed|money deducted|charged twice|double charged|unauthorized charge|billing issue|transaction failed|bank deducted|amount debited)\b", q_lower):
        return (3, "payment_dispute")

    # Customer complaints / request human / manager:
    if re.search(r"\b(complaint|complain|file a complaint|speak to (a )?human|speak to (a )?manager|talk to (a )?human|talk to (an )?agent|talk to human|speak to human|call me|cheated|scam|fraud)\b", q_lower):
        return (3, "complaint_escalation")

    # Special discount / individual refund exceptions:
    if re.search(r"\b(refund my money for order|special discount for me|give me extra discount|manager discount)\b", q_lower):
        return (3, "refund_exception")

    # 2. Level 2 Contextual Follow-Up Indicators
    follow_up_patterns = [
        r"^(what about|how about|and|also|what if)\b",
        r"\b(what about tomorrow|what about sunday|and tomorrow|and on weekends|can i visit then|is it available in|how much is it)\b"
    ]
    if any(re.search(p, q_lower) for p in follow_up_patterns):
        return (2, "follow_up")

    if conversation_history and len(q_lower.split()) <= 4:
        if any(w in q_lower for w in ["tomorrow", "today", "yesterday", "weekend", "sunday", "saturday", "monday", "price", "blue", "black"]):
            return (2, "follow_up")

    # 3. Level 1 Standard Knowledge or Conversational
    return (1, "standard")

def sanitize_customer_answer(raw_answer: str, question: str = "") -> str:
    """
    Sanitize AI answers to ensure no internal retrieval metadata,
    knowledge-base tags, or raw structures leak to the customer.
    Converts raw FAQs/Notes into clean conversational sentences.
    Never returns an empty string or single punctuation marks.
    """
    if not raw_answer or not isinstance(raw_answer, str):
        return FALLBACK_MESSAGE

    text = raw_answer.strip()
    if not text or text == FALLBACK_MESSAGE:
        return FALLBACK_MESSAGE

    # 1. Strip [Entry X - Category] or bracketed headers
    text = re.sub(r'\[Entry\s*\d+[^\]]*\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[.*?\]', '', text)

    # 2. Extract answer if formatted like 'Question: ... Answer: ...' or 'FAQ: ... Answer: ...'
    ans_match = re.search(
        r'(?:Correct\s+)?Answer:\s*(.*?)(?:\s*(?:Correction\s+Notes|Notes|FAQ|Question|Title|Category):|$)', 
        text, 
        flags=re.IGNORECASE | re.DOTALL
    )
    if ans_match and ans_match.group(1).strip():
        text = ans_match.group(1).strip()
    else:
        # Strip leading Question/FAQ/Category lines
        text = re.sub(r'^(?:FAQ|Question|Title|Category):\s*.*?(?:\n|$)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^(?:FAQ|Question|Title|Category):\s*', '', text, flags=re.IGNORECASE)

    # 3. Strip any remaining 'Answer:' or 'Correction Notes:' prefixes
    text = re.sub(r'^(?:Correct\s+)?Answer:\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Correction Notes:.*$', '', text, flags=re.IGNORECASE | re.DOTALL)

    # 4. Collapse whitespace
    text = re.sub(r'[ \t]+', ' ', text).strip()

    # 5. Check substantive alphanumeric content
    alnum_count = len(re.findall(r'[a-zA-Z0-9]', text))
    if alnum_count < 3:
        return FALLBACK_MESSAGE

    # Natural grammar touch-ups for shorthand notes
    text = re.sub(r'\bvalid id proof\b', 'a valid ID proof', text, flags=re.IGNORECASE)

    # 6. Natural sentence formatting: Capitalize first character
    if text and not text[0].isupper():
        text = text[0].upper() + text[1:]

    # Ensure sentence ending punctuation
    if text and text[-1] not in ('.', '!', '?'):
        text = text + '.'

    return text.strip()

def classify_conversational_intent(text: str) -> str:
    """
    Classify general customer conversation into:
    'greeting', 'how_are_you', 'help', 'catalog', 'gratitude', 'farewell', or None.
    """
    if not text:
        return None
    cleaned = re.sub(r"[^\w\s]", "", text.strip().lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return None

    # 1. Greetings
    greeting_exact = {"hi", "hello", "hey", "good morning", "good evening", "good afternoon", "greetings", "hey there", "hello there"}
    if cleaned in greeting_exact:
        return "greeting"
    if any(cleaned.startswith(g + " ") for g in ["hi", "hello", "hey", "good morning", "good evening", "good afternoon"]):
        rest = re.sub(r"^(hi|hello|hey|good morning|good evening|good afternoon)\s*", "", cleaned).strip()
        if not rest or rest in {"there", "bot", "assistant", "team", "shop", "sir", "madam", "friend", "good morning", "good evening", "good afternoon"}:
            return "greeting"

    # 2. How are you
    if cleaned in {"how are you", "how are you doing", "how do you do", "how is it going", "how r u", "how are u"}:
        return "how_are_you"
    if any(cleaned.startswith(p) for p in ["how are you", "how are you doing", "how do you do", "how is it going"]):
        return "how_are_you"

    # 3. Help / Capabilities
    help_phrases = {
        "what can you help me with", "what can you help with", "what can you do",
        "how can you help", "how can you help me", "who are you", "what are you",
        "can you help me", "help me", "what do you do"
    }
    if cleaned in help_phrases:
        return "help"
    if any(cleaned.startswith(p) for p in ["what can you help", "how can you help", "who are you"]):
        return "help"

    # 4. Gratitude
    gratitude_phrases = {"thank you", "thanks", "thank u", "thanks a lot", "thank you so much", "many thanks", "appreciate it"}
    if cleaned in gratitude_phrases or any(cleaned.startswith(p) for p in ["thank you", "thanks"]):
        return "gratitude"

    # 5. Farewells
    farewell_phrases = {"bye", "goodbye", "good bye", "bye bye", "see you", "see ya", "have a nice day", "have a good day", "take care"}
    if cleaned in farewell_phrases or any(cleaned.startswith(p) for p in ["bye", "goodbye", "good bye", "see you"]):
        return "farewell"

    # 6. General Store Catalog Inquiry (must not match specific products like iPhone or saree)
    catalog_patterns = [
        r"^what (does|do) (your shop|this shop|the shop|you) sell$",
        r"^what (products|items|brands) do you (sell|have|offer)$",
        r"^what products are available$",
        r"^what do you (have|offer)$",
        r"^tell me about (your|this) (shop|store)$",
        r"^what is (this|your) (shop|store)$"
    ]
    for pattern in catalog_patterns:
        if re.match(pattern, cleaned):
            return "catalog"

    return None

def get_conversational_response(intent: str, shop_name: str, shop_description: str = None, context: str = None) -> str:
    """Generate friendly, polite, non-hallucinating responses for general conversational intents."""
    if intent == "greeting":
        return f"Hello! Welcome to {shop_name}. How can I assist you today?"
    elif intent == "how_are_you":
        return f"I'm doing well, thank you for asking! How can I assist you today at {shop_name}?"
    elif intent == "help":
        return f"I am the customer support assistant for {shop_name}. I can assist you with store hours, products, return and exchange policies, pricing, and our location. How can I help you?"
    elif intent == "gratitude":
        return f"You're very welcome! Please let me know if you need any further assistance with {shop_name}."
    elif intent == "farewell":
        return f"Goodbye! Thank you for visiting {shop_name}. Have a wonderful day!"
    elif intent == "catalog":
        if shop_description:
            desc_clean = shop_description.strip().rstrip('.')
            return f"At {shop_name}, {desc_clean}. What specific product or brand are you looking for?"
        if context:
            lines = [l.strip() for l in context.split("\n") if any(k in l.lower() for k in ["sell", "product", "phone", "cloth", "brand", "item", "available", "store", "shop"]) and not l.strip().startswith("[Entry")]
            if lines:
                return f"At {shop_name}, {lines[0]}. Let me know if you are looking for a specific model or item!"
        return f"Welcome to {shop_name}! We offer a variety of high quality products. Please let me know what specific product or brand you are looking for!"
    return f"Hello! Welcome to {shop_name}. How can I assist you today?"

class AIService:
    @classmethod
    def get_provider(cls):
        return current_app.config.get("AI_PROVIDER", "gemini").lower()
        
    @classmethod
    def answer_question(cls, question: str, knowledge_entries: list, shop_name: str, conversation_history: list = None, shop_description: str = None) -> dict:
        """
        Receives question and list of relevant knowledge entries.
        Optionally receives recent conversation history for follow-up context and shop description.
        Returns dict:
        {
            "can_answer": bool,
            "answer": str,
            "provider": str
        }
        Guarantees that can_answer=True ONLY if answer is a valid, substantive, non-empty answer.
        """
        if not question or not question.strip():
            return {
                "can_answer": False,
                "answer": FALLBACK_MESSAGE,
                "provider": "validator"
            }

        # 1. Three-Level Classification check: Level 3 Escalations require human owner intervention
        level, reason = classify_question_level(question, conversation_history)
        if level == 3:
            return {
                "can_answer": False,
                "answer": FALLBACK_MESSAGE,
                "provider": "escalation_classifier",
                "level": 3
            }

        intent = classify_conversational_intent(question)
            
        context_blocks = []
        if knowledge_entries:
            for idx, item in enumerate(knowledge_entries, 1):
                entry = item["entry"] if isinstance(item, dict) and "entry" in item else item
                title = getattr(entry, "title", "")
                content = getattr(entry, "content", "")
                category = getattr(entry, "category", "")
                context_blocks.append(f"[Entry {idx} - {category}] {title}\n{content}")
            
        full_context = "\n\n".join(context_blocks)
        provider = cls.get_provider()
        
        gemini_key = current_app.config.get("GEMINI_API_KEY")
        claude_key = current_app.config.get("ANTHROPIC_API_KEY")

        # 1. Handle general conversational queries immediately without pending queue
        if intent:
            try:
                if provider == "gemini" and gemini_key:
                    res = cls._call_gemini(question, full_context, shop_name, gemini_key, conversation_history, is_conversational=True, shop_description=shop_description)
                    if res.get("can_answer") and res.get("answer"):
                        return res
                elif provider == "claude" and claude_key:
                    res = cls._call_claude(question, full_context, shop_name, claude_key, conversation_history, is_conversational=True, shop_description=shop_description)
                    if res.get("can_answer") and res.get("answer"):
                        return res
            except Exception as e:
                logger.warning(f"Error in conversational AI provider: {e}")

            return {
                "can_answer": True,
                "answer": get_conversational_response(intent, shop_name, shop_description, full_context),
                "provider": "conversational_engine"
            }

        # 2. For shop-specific queries, require relevant knowledge entries
        if not knowledge_entries:
            return {
                "can_answer": False,
                "answer": FALLBACK_MESSAGE,
                "provider": "relevance_filter"
            }
        
        try:
            if provider == "gemini" and gemini_key:
                res = cls._call_gemini(question, full_context, shop_name, gemini_key, conversation_history, is_conversational=False, shop_description=shop_description)
            elif provider == "claude" and claude_key:
                res = cls._call_claude(question, full_context, shop_name, claude_key, conversation_history, is_conversational=False, shop_description=shop_description)
            else:
                res = cls._fallback_local_evaluator(question, full_context, shop_name, conversation_history)
        except Exception as e:
            logger.error(f"Unexpected error in AI service dispatcher: {e}")
            res = {
                "can_answer": False,
                "answer": FALLBACK_MESSAGE,
                "provider": provider
            }

        # Strict answer validation & sanitization
        can_answer = bool(res.get("can_answer", False))
        raw_answer = res.get("answer")

        if can_answer and raw_answer and isinstance(raw_answer, str) and raw_answer.strip():
            sanitized = sanitize_customer_answer(raw_answer, question)
            if sanitized and sanitized != FALLBACK_MESSAGE and len(sanitized.strip()) >= 3:
                res["can_answer"] = True
                res["answer"] = sanitized
            else:
                res["can_answer"] = False
                res["answer"] = FALLBACK_MESSAGE
        else:
            res["can_answer"] = False
            res["answer"] = FALLBACK_MESSAGE

        return res

    @classmethod
    def stream_answer_question(cls, question: str, knowledge_entries: list, shop_name: str, conversation_history: list = None, shop_description: str = None):
        """
        Public generator for streaming AI responses.
        Yields dicts with {"type": "chunk", "text": "..."}
        and terminates with {"type": "done", "can_answer": bool, "answer": str, "provider": str}.
        """
        if not question or not question.strip():
            yield {"type": "chunk", "text": FALLBACK_MESSAGE}
            yield {"type": "done", "can_answer": False, "answer": FALLBACK_MESSAGE, "provider": "validator"}
            return

        # 1. Three-Level Classification check: Level 3 Escalations require human owner intervention
        level, reason = classify_question_level(question, conversation_history)
        if level == 3:
            yield {"type": "chunk", "text": FALLBACK_MESSAGE}
            yield {
                "type": "done",
                "can_answer": False,
                "answer": FALLBACK_MESSAGE,
                "provider": "escalation_classifier",
                "level": 3
            }
            return

        intent = classify_conversational_intent(question)
        context_blocks = []
        if knowledge_entries:
            for idx, item in enumerate(knowledge_entries, 1):
                entry = item["entry"] if isinstance(item, dict) and "entry" in item else item
                title = getattr(entry, "title", "")
                content = getattr(entry, "content", "")
                category = getattr(entry, "category", "")
                context_blocks.append(f"[Entry {idx} - {category}] {title}\n{content}")
        full_context = "\n\n".join(context_blocks)

        provider = cls.get_provider()
        gemini_key = current_app.config.get("GEMINI_API_KEY")

        # 1. Handle general conversational queries immediately
        if intent:
            if provider == "gemini" and gemini_key:
                try:
                    for ev in cls._stream_gemini(question, full_context, shop_name, gemini_key, conversation_history, is_conversational=True, shop_description=shop_description):
                        yield ev
                    return
                except Exception as e:
                    logger.warning(f"Error in conversational Gemini stream: {e}")

            conv_text = get_conversational_response(intent, shop_name, shop_description, full_context)
            yield {"type": "chunk", "text": conv_text}
            yield {"type": "done", "can_answer": True, "answer": conv_text, "provider": "conversational_engine"}
            return

        # 2. For shop-specific queries, require relevant knowledge entries
        if not knowledge_entries:
            yield {"type": "chunk", "text": FALLBACK_MESSAGE}
            yield {"type": "done", "can_answer": False, "answer": FALLBACK_MESSAGE, "provider": "relevance_filter"}
            return

        # 3. Stream from Gemini API
        if provider == "gemini" and gemini_key:
            try:
                for ev in cls._stream_gemini(question, full_context, shop_name, gemini_key, conversation_history, is_conversational=False, shop_description=shop_description):
                    yield ev
                return
            except Exception as e:
                logger.error(f"Error in Gemini streaming dispatcher: {e}")

        # 4. Fallback local evaluator (for offline / development / test environments)
        res = cls._fallback_local_evaluator(question, full_context, shop_name, conversation_history)
        can_answer = bool(res.get("can_answer", False))
        answer = res.get("answer", FALLBACK_MESSAGE)
        if can_answer and answer and answer != FALLBACK_MESSAGE:
            words = answer.split(" ")
            mid = max(1, len(words) // 2)
            c1 = " ".join(words[:mid]) + " "
            c2 = " ".join(words[mid:])
            yield {"type": "chunk", "text": c1}
            yield {"type": "chunk", "text": c2}
            yield {"type": "done", "can_answer": True, "answer": answer, "provider": "local_fallback"}
        else:
            yield {"type": "chunk", "text": FALLBACK_MESSAGE}
            yield {"type": "done", "can_answer": False, "answer": FALLBACK_MESSAGE, "provider": "local_fallback"}

    @classmethod
    def _stream_gemini(cls, question: str, context: str, shop_name: str, api_key: str, conversation_history: list = None, is_conversational: bool = False, shop_description: str = None):
        """
        Stream response chunks directly from Gemini's streamGenerateContent API using SSE transport.
        Yields dicts:
          {"type": "chunk", "text": "..."}
          and finally:
          {"type": "done", "can_answer": bool, "answer": str, "provider": "gemini"}
        """
        history_text = ""
        if conversation_history:
            history_lines = []
            for m in conversation_history[-4:]:
                sender = "Customer" if m.get("sender_type") == "customer" else "AI"
                history_lines.append(f"{sender}: {m.get('message_content', '')}")
            if history_lines:
                history_text = f"CONVERSATION HISTORY:\n" + "\n".join(history_lines) + "\n\n"

        if is_conversational:
            shop_desc_line = f"Shop Description: {shop_description}\n" if shop_description else ""
            kb_line = f"KNOWLEDGE BASE CONTEXT:\n{context}\n\n" if context else ""
            prompt = f"""You are a helpful, professional, and friendly AI customer support assistant for {shop_name}.
{shop_desc_line}{kb_line}{history_text}CUSTOMER MESSAGE:
{question}

You must respond warmly, politely, concisely, and helpfully as the store's assistant in natural sentences.
If this is a greeting or pleasantry, welcome the customer to {shop_name}.
If they ask what you can do or who you are, explain you are the AI assistant for {shop_name} and can help with store hours, products, return/exchange policies, and location.
If they ask what the shop sells, summarize the shop's general products based on the shop description or context, and ask what they are looking for. Never invent specific unmentioned brands.
If they say thank you or goodbye, reply with a warm closing.
Do not output JSON, quotes, prefixes, or markdown headers. Output plain conversational text directly."""
        else:
            prompt = f"""You are a helpful, professional, and friendly AI customer support assistant for {shop_name}.
You must answer customer questions naturally, concisely, and politely using ONLY the provided shop knowledge base context.

CRITICAL RULES:
1. Answer directly as the store's friendly assistant in natural, polite customer-facing sentences.
2. NEVER repeat raw internal structures like 'FAQ:', 'Question:', 'Answer:', 'Title:', or 'Category:'.
3. NEVER expose entry numbers like '[Entry 1]' or category labels.
4. If the customer asks about opening hours, store timings, or reopening (e.g. 'When will the shop reopen?', 'Shop opening time?', 'When does the shop open?'), answer clearly with the shop's hours from the context in a friendly, conversational way (e.g. 'Our shop opens every day at 10 AM. You are welcome to visit us then!').
5. If the customer asks a follow-up question (e.g. 'What about tomorrow?'), answer helpfully based on the regular schedule or previous context.
6. If the provided context does not contain sufficient information to answer the question confidently, reply with EXACTLY: CANNOT_ANSWER
7. Never invent or assume products, prices, or policies not in the context.
8. Do NOT output JSON, quotes, prefixes, or markdown headers. Answer directly.

KNOWLEDGE BASE CONTEXT:
{context}

{history_text}CUSTOMER QUESTION:
{question}"""

        primary_model = current_app.config.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"
        timeout_seconds = int(current_app.config.get("AI_TIMEOUT", 20))
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.1,
            }
        }

        candidate_models = [primary_model]
        for fallback in ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        for model_name in candidate_models:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:streamGenerateContent?alt=sse&key={api_key}"
            try:
                res = requests.post(endpoint, headers=headers, json=payload, stream=True, timeout=timeout_seconds)
                if res.status_code == 200:
                    buffer = ""
                    is_evaluated = False
                    streamed_chunks = []

                    for line in res.iter_lines():
                        if not line:
                            continue
                        decoded = line.decode("utf-8").strip()
                        if not decoded.startswith("data: "):
                            continue
                        json_str = decoded[6:].strip()
                        if not json_str:
                            continue
                        try:
                            data = json.loads(json_str)
                        except Exception:
                            continue

                        candidates = data.get("candidates") or []
                        if not candidates:
                            continue
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if not parts or "text" not in parts[0]:
                            continue
                        raw_chunk = parts[0]["text"]
                        if not raw_chunk:
                            continue

                        if not is_evaluated:
                            buffer += raw_chunk
                            if "CANNOT" in buffer.upper() or "NOT_FOUND" in buffer.upper():
                                is_evaluated = True
                                yield {"type": "chunk", "text": FALLBACK_MESSAGE}
                                yield {"type": "done", "can_answer": False, "answer": FALLBACK_MESSAGE, "provider": "gemini"}
                                return
                            elif len(buffer) >= 15 or not ("CANNOT"[:min(len(buffer), 6)].upper() in buffer.upper()):
                                is_evaluated = True
                                clean_buf = re.sub(r'^(?:Answer|FAQ|Question):\s*', '', buffer, flags=re.IGNORECASE)
                                clean_buf = re.sub(r'\[Entry\s*\d+[^\]]*\]', '', clean_buf, flags=re.IGNORECASE)
                                if clean_buf:
                                    streamed_chunks.append(clean_buf)
                                    yield {"type": "chunk", "text": clean_buf}
                        else:
                            clean_chunk = re.sub(r'\[Entry\s*\d+[^\]]*\]', '', raw_chunk, flags=re.IGNORECASE)
                            if clean_chunk:
                                streamed_chunks.append(clean_chunk)
                                yield {"type": "chunk", "text": clean_chunk}

                    if not is_evaluated:
                        if "CANNOT" in buffer.upper() or "NOT_FOUND" in buffer.upper() or not buffer.strip():
                            yield {"type": "chunk", "text": FALLBACK_MESSAGE}
                            yield {"type": "done", "can_answer": False, "answer": FALLBACK_MESSAGE, "provider": "gemini"}
                            return
                        else:
                            clean_buf = sanitize_customer_answer(buffer, question)
                            if clean_buf and clean_buf != FALLBACK_MESSAGE:
                                yield {"type": "chunk", "text": clean_buf}
                                yield {"type": "done", "can_answer": True, "answer": clean_buf, "provider": "gemini"}
                            else:
                                yield {"type": "chunk", "text": FALLBACK_MESSAGE}
                                yield {"type": "done", "can_answer": False, "answer": FALLBACK_MESSAGE, "provider": "gemini"}
                            return

                    full_answer = "".join(streamed_chunks).strip()
                    sanitized_answer = sanitize_customer_answer(full_answer, question)
                    if not sanitized_answer or sanitized_answer == FALLBACK_MESSAGE or len(sanitized_answer) < 3:
                        yield {"type": "done", "can_answer": False, "answer": FALLBACK_MESSAGE, "provider": "gemini"}
                    else:
                        yield {"type": "done", "can_answer": True, "answer": sanitized_answer, "provider": "gemini"}
                    return
                elif res.status_code in (404, 503):
                    logger.warning(f"Gemini streaming status {res.status_code} for model {model_name}, trying next fallback.")
                    continue
                else:
                    logger.warning(f"Gemini streaming returned error {res.status_code} for model {model_name}")
                    break
            except Exception as e:
                logger.warning(f"Error during Gemini streaming with model {model_name}: {e}")
                continue

        # If all candidates fail or error:
        yield {"type": "chunk", "text": FALLBACK_MESSAGE}
        yield {"type": "done", "can_answer": False, "answer": FALLBACK_MESSAGE, "provider": "gemini"}

    @classmethod
    def _call_gemini(cls, question: str, context: str, shop_name: str, api_key: str, conversation_history: list = None, is_conversational: bool = False, shop_description: str = None) -> dict:
        """Call Gemini API via REST with structured output."""
        history_text = ""
        if conversation_history:
            history_lines = []
            for m in conversation_history[-4:]:
                sender = "Customer" if m.get("sender_type") == "customer" else "AI"
                history_lines.append(f"{sender}: {m.get('message_content', '')}")
            if history_lines:
                history_text = f"CONVERSATION HISTORY:\n" + "\n".join(history_lines) + "\n\n"

        if is_conversational:
            shop_desc_line = f"Shop Description: {shop_description}\n" if shop_description else ""
            kb_line = f"KNOWLEDGE BASE CONTEXT:\n{context}\n\n" if context else ""
            prompt = f"""You are a helpful, professional, and friendly AI customer support assistant for {shop_name}.
{shop_desc_line}{kb_line}{history_text}CUSTOMER MESSAGE:
{question}

You must respond warmly, politely, concisely, and helpfully as the store's assistant.
If this is a greeting or pleasantry, welcome the customer to {shop_name}.
If they ask what you can do or who you are, explain you are the AI assistant for {shop_name} and can help with store hours, products, return/exchange policies, and location.
If they ask what the shop sells, summarize the shop's general products based on the shop description or context, and ask what they are looking for. Never invent specific unmentioned brands.
If they say thank you or goodbye, reply with a warm closing.
Always return can_answer: true.

Respond ONLY with a valid JSON object:
{{
  "can_answer": true,
  "answer": "your concise, polite customer-facing response"
}}
"""
        else:
            prompt = f"""
{SYSTEM_INSTRUCTION}

Shop Name: {shop_name}

KNOWLEDGE BASE CONTEXT:
{context}

{history_text}CUSTOMER QUESTION:
{question}

You must respond ONLY with a valid JSON object in this exact schema:
{{
  "can_answer": true/false,
  "answer": "your concise, friendly answer based strictly on the context, or null if cannot answer"
}}
"""
        primary_model = current_app.config.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"
        timeout_seconds = int(current_app.config.get("AI_TIMEOUT", 20))
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }

        # Build resilient model sequence (configured model first, then high-availability fallbacks)
        candidate_models = [primary_model]
        for fallback in ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        for model_name in candidate_models:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            try:
                res = requests.post(endpoint, headers=headers, json=payload, timeout=timeout_seconds)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates") or []
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            raw_text = parts[0]["text"].strip()
                            json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                            if json_match:
                                raw_text = json_match.group(0)
                            parsed = json.loads(raw_text)
                            can_answer = bool(parsed.get("can_answer", False))
                            answer = parsed.get("answer")
                            if can_answer and answer and isinstance(answer, str) and answer.strip():
                                return {
                                    "can_answer": True,
                                    "answer": answer.strip(),
                                    "provider": "gemini"
                                }
                            else:
                                # Context does not support answering; valid non-answer
                                return {
                                    "can_answer": False,
                                    "answer": FALLBACK_MESSAGE,
                                    "provider": "gemini"
                                }
                elif res.status_code == 429:
                    logger.warning(f"Gemini API rate limit exceeded for model '{model_name}'.")
                elif res.status_code == 503:
                    logger.warning(f"Gemini API model '{model_name}' unavailable (HTTP 503 high demand). Trying next candidate.")
                    continue
                elif res.status_code == 404:
                    logger.warning(f"Gemini API model identifier '{model_name}' not found (HTTP 404). Trying next candidate.")
                    continue
                elif res.status_code in (400, 401, 403):
                    logger.warning(f"Gemini API auth or configuration error with model '{model_name}': HTTP {res.status_code}")
                    break
                else:
                    logger.warning(f"Gemini API returned status {res.status_code} for model '{model_name}'")
            except requests.exceptions.Timeout:
                logger.warning(f"Gemini API request timed out ({timeout_seconds}s) for model '{model_name}'.")
                continue
            except requests.exceptions.RequestException as e:
                logger.warning(f"Gemini API network error for model '{model_name}': {type(e).__name__}")
                continue
            except Exception as e:
                logger.warning(f"Error parsing Gemini API response for model '{model_name}': {type(e).__name__}")
                continue
            
        return {
            "can_answer": False,
            "answer": FALLBACK_MESSAGE,
            "provider": "gemini"
        }

    @classmethod
    def _call_claude(cls, question: str, context: str, shop_name: str, api_key: str, conversation_history: list = None, is_conversational: bool = False, shop_description: str = None) -> dict:
        """Call Claude API via REST."""
        history_text = ""
        if conversation_history:
            history_lines = []
            for m in conversation_history[-4:]:
                sender = "Customer" if m.get("sender_type") == "customer" else "AI"
                history_lines.append(f"{sender}: {m.get('message_content', '')}")
            if history_lines:
                history_text = f"CONVERSATION HISTORY:\n" + "\n".join(history_lines) + "\n\n"

        if is_conversational:
            shop_desc_line = f"Shop Description: {shop_description}\n" if shop_description else ""
            kb_line = f"KNOWLEDGE BASE CONTEXT:\n{context}\n\n" if context else ""
            prompt = f"""You are a helpful, professional, and friendly AI customer support assistant for {shop_name}.
{shop_desc_line}{kb_line}{history_text}CUSTOMER MESSAGE:
{question}

You must respond warmly, politely, concisely, and helpfully as the store's assistant.
If this is a greeting or pleasantry, welcome the customer to {shop_name}.
If they ask what you can do or who you are, explain you are the AI assistant for {shop_name} and can help with store hours, products, return/exchange policies, and location.
If they ask what the shop sells, summarize the shop's general products based on the shop description or context, and ask what they are looking for. Never invent specific unmentioned brands.
If they say thank you or goodbye, reply with a warm closing.
Always return can_answer: true.

Respond ONLY with a valid JSON object:
{{
  "can_answer": true,
  "answer": "your concise, polite customer-facing response"
}}
"""
        else:
            prompt = f"""
{SYSTEM_INSTRUCTION}

Shop Name: {shop_name}

KNOWLEDGE BASE CONTEXT:
{context}

{history_text}CUSTOMER QUESTION:
{question}

Respond ONLY with valid JSON:
{{
  "can_answer": true/false,
  "answer": "your answer based strictly on context, or null if cannot answer"
}}
"""
        model_name = current_app.config.get("CLAUDE_MODEL", "claude-haiku-5-5").strip() or "claude-haiku-5-5"
        endpoint = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": model_name,
            "max_tokens": 500,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            res = requests.post(endpoint, headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                content = data.get("content") or []
                if content and "text" in content[0]:
                    text = content[0]["text"].strip()
                    json_match = re.search(r"\{.*\}", text, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(0))
                        can_answer = bool(parsed.get("can_answer", False))
                        answer = parsed.get("answer")
                        if can_answer and answer and isinstance(answer, str) and answer.strip():
                            return {
                                "can_answer": True,
                                "answer": answer.strip(),
                                "provider": "claude"
                            }
            elif res.status_code == 429:
                logger.warning("Claude API rate limit exceeded.")
            elif res.status_code in (400, 401, 403):
                logger.warning(f"Claude API authentication/key error: HTTP {res.status_code}")
            else:
                logger.warning(f"Claude API returned status {res.status_code}")
        except requests.exceptions.Timeout:
            logger.warning("Claude API request timed out (10s).")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Claude API network error: {type(e).__name__}")
        except Exception as e:
            logger.warning(f"Error parsing Claude API response: {type(e).__name__}")
            
        return {
            "can_answer": False,
            "answer": FALLBACK_MESSAGE,
            "provider": "claude"
        }

    @classmethod
    def _fallback_local_evaluator(cls, question: str, context: str, shop_name: str, conversation_history: list = None) -> dict:
        """
        Intelligent local context evaluation for testing & development.
        Answers strictly from the context, understands intent, supports follow-up questions,
        prioritizes owner-verified corrections and approved answers,
        and never fabricates facts or returns empty content.
        """
        q_lower = question.lower()
        c_lower = context.lower()

        # 0. Escalation Check: Level 3 inquiries MUST route to Pending
        level, reason = classify_question_level(question, conversation_history)
        if level == 3:
            return {
                "can_answer": False,
                "answer": FALLBACK_MESSAGE,
                "provider": "escalation_classifier"
            }

        # Priority: Check for verified direct Q&A entries (pending_answered & feedback_correction)
        # This guarantees that owner-approved answers and corrections strictly take precedence
        # over any older or conflicting general entries.
        from backend.app.services.search_service import tokenize
        user_q_tokens = tokenize(question, remove_stopwords=True)
        blocks = context.split("\n\n")
        for block in blocks:
            # Extract Answer or Correct Answer
            ans_match = re.search(
                r'(?:Correct\s+)?Answer:\s*([^\n]+(?:\n(?!(?:Correction Notes|Notes|FAQ|Question|Title|Category):)[^\n]+)*)',
                block,
                flags=re.IGNORECASE
            )
            if ans_match:
                # Extract Question
                q_match = re.search(r'(?:Question|FAQ):\s*([^\n]+)', block, flags=re.IGNORECASE)
                if q_match:
                    entry_q = q_match.group(1).lower().strip()
                    entry_q_tokens = tokenize(entry_q, remove_stopwords=True)
                    if user_q_tokens and (
                        user_q_tokens.issubset(entry_q_tokens) or
                        len(user_q_tokens.intersection(entry_q_tokens)) / max(len(user_q_tokens), 1) >= 0.5 or
                        q_lower in entry_q or entry_q in q_lower
                    ):
                        direct_ans = ans_match.group(1).strip()
                        if direct_ans and len(direct_ans) > 5:
                            return {
                                "can_answer": True,
                                "answer": direct_ans,
                                "provider": "local_engine"
                            }

        def clean_lines(lines_list):
            substantive = []
            for l in lines_list:
                line_str = l.strip()
                if line_str.startswith("[Entry"):
                    continue
                # If FAQ line, look for the Answer part
                if line_str.startswith("FAQ:") or line_str.startswith("Question:"):
                    continue
                if line_str.startswith("Category:") or line_str.startswith("Title:") or line_str.lower().startswith("correction notes:"):
                    continue
                if line_str.lower().startswith(("answer:", "correct answer:")):
                    ans_part = re.sub(r"^(?:correct\s+)?answer:\s*", "", line_str, flags=re.IGNORECASE).strip()
                    if ans_part:
                        substantive.append(ans_part)
                    continue
                substantive.append(line_str)
            if substantive:
                return " ".join(substantive)
            return ""

        # 1. Address / Location intent
        addr_words = ["address", "location", "located", "where is", "where are", "street", "road", "pincode", "directions", "landmark", "situated", "where"]
        if any(w in q_lower for w in addr_words) and not any(w in q_lower for w in ["open", "close", "reopen", "time", "hours"]):
            lines = context.split("\n")
            matching = [l.strip() for l in lines if any(k in l.lower() for k in ["address", "location", "street", "road", "near", "opposite", "behind", "pincode", "situated", "floor"]) and len(l.strip()) > 5 and not l.strip().startswith("[Entry")]
            sub = clean_lines(matching)
            if sub:
                return {
                    "can_answer": True,
                    "answer": sub,
                    "provider": "local_engine"
                }
            # Context does NOT contain an address!
            return {
                "can_answer": False,
                "answer": FALLBACK_MESSAGE,
                "provider": "local_engine"
            }

        # 2. Return / Exchange / Refund policy intent
        ret_words = ["return", "returns", "exchange", "refund", "replacement", "warranty", "policy", "guarantee", "claim"]
        if any(w in q_lower for w in ret_words):
            lines = context.split("\n")
            matching = [l.strip() for l in lines if any(k in l.lower() for k in ["return", "exchange", "refund", "days", "bill", "box", "tags", "warranty", "unused", "replacement", "proof"]) and len(l.strip()) > 5 and not l.strip().startswith("[Entry")]
            sub = clean_lines(matching)
            if sub:
                # Add natural conversational prefix if needed
                if not sub.lower().startswith(("yes", "customers", "you", "our", "in order", "please")):
                    sub = f"Yes, you can exchange or return products. {sub}"
                return {
                    "can_answer": True,
                    "answer": sub,
                    "provider": "local_engine"
                }
            return {
                "can_answer": False,
                "answer": FALLBACK_MESSAGE,
                "provider": "local_engine"
            }

        # 3. Pricing / Cost intent
        price_words = ["price", "cost", "how much", "rate", "rates", "charge", "pricing"]
        if any(w in q_lower for w in price_words):
            lines = context.split("\n")
            matching = [l.strip() for l in lines if any(k in l.lower() for k in ["rs", "$", "price", "cost", "inr", "usd", "starts at", "starting", "worth"]) and len(l.strip()) > 5 and not l.strip().startswith("[Entry")]
            sub = clean_lines(matching)
            if sub:
                return {
                    "can_answer": True,
                    "answer": sub,
                    "provider": "local_engine"
                }

        # 4. Product / Brand / Availability / Buy intent
        from backend.app.services.search_service import STOP_WORDS, expand_synonyms
        prod_words = ["mobile", "phone", "smartphone", "product", "sell", "brand", "item", "available", "cloth", "clothes", "dress", "saree", "buy", "purchase", "laptop", "accessory", "accessories"]
        if any(w in q_lower for w in prod_words):
            # Extract substantive query product nouns (ignoring intent verbs like sell/buy/available)
            q_product_nouns = [w for w in re.sub(r"[^\w\s]", "", q_lower).split() if len(w) > 2 and w not in STOP_WORDS]
            expanded_nouns = expand_synonyms(set(q_product_nouns))

            # If customer asked about specific product nouns, verify at least one is supported in context
            if q_product_nouns and not any(noun in c_lower for noun in expanded_nouns):
                return {
                    "can_answer": False,
                    "answer": FALLBACK_MESSAGE,
                    "provider": "local_engine"
                }

            lines = context.split("\n")
            matching = [l.strip() for l in lines if any(k in l.lower() for k in ["sell", "product", "brand", "phone", "smartphone", "cloth", "dress", "saree", "kurta", "samsung", "apple", "vivo", "oneplus", "men", "women", "available", "accessories"]) and len(l.strip()) > 5 and not l.strip().startswith("[Entry")]
            sub = clean_lines(matching)
            if sub:
                if any(w in q_lower for w in ["want", "buy", "looking", "interested"]) and not sub.endswith("?"):
                    sub = f"{sub.rstrip('. ')}. Which brand or model are you looking for?"
                return {
                    "can_answer": True,
                    "answer": sub,
                    "provider": "local_engine"
                }
            return {
                "can_answer": False,
                "answer": FALLBACK_MESSAGE,
                "provider": "local_engine"
            }

        # 5. Delivery / Shipping intent
        if any(w in q_lower for w in ["delivery", "deliver", "shipping", "ship", "courier"]):
            lines = context.split("\n")
            matching = [l.strip() for l in lines if any(k in l.lower() for k in ["deliver", "delivery", "shipping", "courier", "dispatch"]) and len(l.strip()) > 5 and not l.strip().startswith("[Entry")]
            sub = clean_lines(matching)
            if sub:
                return {
                    "can_answer": True,
                    "answer": sub,
                    "provider": "local_engine"
                }
            return {
                "can_answer": False,
                "answer": FALLBACK_MESSAGE,
                "provider": "local_engine"
            }

        # 6. Timings / Hours / Opening schedule / Reopening intent (with follow-up support)
        time_words = [
            "time", "timing", "timings", "timmings", "open", "opening", "opens", "opened",
            "reopen", "reopening", "reopens", "re-open", "opn", "close", "closing", "closes",
            "hours", "schedule", "sunday", "saturday", "weekend", "holiday", "visit", "operating"
        ]
        is_time_q = any(w in q_lower for w in time_words)
        
        # Check if follow-up to a recent timing question
        if not is_time_q and conversation_history:
            recent_text = " ".join([m.get("message_content", "").lower() for m in conversation_history[-2:]])
            if any(w in recent_text for w in ["timing", "timings", "open", "reopen", "close", "hours"]):
                if any(w in q_lower for w in ["sunday", "saturday", "monday", "weekend", "today", "tomorrow"]):
                    is_time_q = True

        if is_time_q:
            lines = context.split("\n")
            matching = [l.strip() for l in lines if any(k in l.lower() for k in ["open", "reopen", "close", "am", "pm", "hours", "timing", "sunday", "monday", "holiday", "schedule", "day"]) and len(l.strip()) > 5 and not l.strip().startswith("[Entry")]
            sub = clean_lines(matching)
            if sub:
                # Follow-up check: "What about tomorrow?"
                if any(w in q_lower for w in ["tomorrow", "tmrw"]):
                    if "every day" in sub.lower() or "daily" in sub.lower() or "10 am" in sub.lower():
                        return {
                            "can_answer": True,
                            "answer": "We open tomorrow at 10 AM as well, according to our regular opening schedule." if "10 am" in sub.lower() else f"We are open tomorrow as well: {sub}",
                            "provider": "local_engine"
                        }
                if any(w in q_lower for w in ["reopen", "reopening", "reopens"]):
                    return {
                        "can_answer": True,
                        "answer": "Our shop opens every day at 10 AM. You're welcome to visit us then!" if ("10 am" in sub.lower() and "every day" in sub.lower()) else sub,
                        "provider": "local_engine"
                    }
                if "sunday" in q_lower and "sunday" in sub.lower():
                    # Return Sunday specific sentence if available
                    for sent in sub.split("."):
                        if "sunday" in sent.lower() and len(sent.strip()) > 5:
                            return {
                                "can_answer": True,
                                "answer": sent.strip() + ".",
                                "provider": "local_engine"
                            }
                return {
                    "can_answer": True,
                    "answer": sub,
                    "provider": "local_engine"
                }
            return {
                "can_answer": False,
                "answer": FALLBACK_MESSAGE,
                "provider": "local_engine"
            }

        # 7. General question check: Search for substantive matching lines
        words = [w for w in re.sub(r"[^\w\s]", "", q_lower).split() if len(w) > 3]
        matches = [line.strip() for line in context.split("\n") if any(w in line.lower() for w in words) and len(line.strip()) > 5 and not line.strip().startswith("[Entry")]
        sub = clean_lines(matches)
        if sub and len(sub) > 5:
            return {
                "can_answer": True,
                "answer": sub,
                "provider": "local_engine"
            }

        return {
            "can_answer": False,
            "answer": FALLBACK_MESSAGE,
            "provider": "local_engine"
        }
