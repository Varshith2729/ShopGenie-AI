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
5. If the customer indicates an intent to buy or browse products (e.g., 'I want a mobile phone'), state what the shop offers from the context and politely ask what specific model or brand they are looking for.
6. If the customer asks about policies (e.g., exchange or return), answer strictly with the shop's actual policy from the context.
7. If the customer asks for shop address or location, answer ONLY if the address is explicitly stated in the context. Never guess or invent an address.
8. If the provided knowledge does not contain sufficient information to answer confidently, return can_answer = false and answer = null.
9. Keep answers short, friendly, accurate, and helpful."""

FALLBACK_MESSAGE = "Thank you! The shop owner will reply to you soon by email."

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

class AIService:
    @classmethod
    def get_provider(cls):
        return current_app.config.get("AI_PROVIDER", "gemini").lower()
        
    @classmethod
    def answer_question(cls, question: str, knowledge_entries: list, shop_name: str, conversation_history: list = None) -> dict:
        """
        Receives question and list of relevant knowledge entries.
        Optionally receives recent conversation history for follow-up context.
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

        if not knowledge_entries:
            return {
                "can_answer": False,
                "answer": FALLBACK_MESSAGE,
                "provider": "relevance_filter"
            }
            
        context_blocks = []
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
        
        try:
            if provider == "gemini" and gemini_key:
                res = cls._call_gemini(question, full_context, shop_name, gemini_key, conversation_history)
            elif provider == "claude" and claude_key:
                res = cls._call_claude(question, full_context, shop_name, claude_key, conversation_history)
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
    def _call_gemini(cls, question: str, context: str, shop_name: str, api_key: str, conversation_history: list = None) -> dict:
        """Call Gemini API via REST with structured output."""
        history_text = ""
        if conversation_history:
            history_lines = []
            for m in conversation_history[-4:]:
                sender = "Customer" if m.get("sender_type") == "customer" else "AI"
                history_lines.append(f"{sender}: {m.get('message_content', '')}")
            if history_lines:
                history_text = f"CONVERSATION HISTORY:\n" + "\n".join(history_lines) + "\n\n"

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
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
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
        
        try:
            res = requests.post(endpoint, headers=headers, json=payload, timeout=10)
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
            elif res.status_code == 429:
                logger.warning("Gemini API rate limit exceeded.")
            elif res.status_code in (400, 401, 403):
                logger.warning(f"Gemini API authentication/key error: HTTP {res.status_code}")
            else:
                logger.warning(f"Gemini API returned status {res.status_code}")
        except requests.exceptions.Timeout:
            logger.warning("Gemini API request timed out (10s).")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Gemini API network error: {type(e).__name__}")
        except Exception as e:
            logger.warning(f"Error parsing Gemini API response: {type(e).__name__}")
            
        return {
            "can_answer": False,
            "answer": FALLBACK_MESSAGE,
            "provider": "gemini"
        }

    @classmethod
    def _call_claude(cls, question: str, context: str, shop_name: str, api_key: str, conversation_history: list = None) -> dict:
        """Call Claude API via REST."""
        history_text = ""
        if conversation_history:
            history_lines = []
            for m in conversation_history[-4:]:
                sender = "Customer" if m.get("sender_type") == "customer" else "AI"
                history_lines.append(f"{sender}: {m.get('message_content', '')}")
            if history_lines:
                history_text = f"CONVERSATION HISTORY:\n" + "\n".join(history_lines) + "\n\n"

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
        endpoint = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": "claude-3-haiku-20240307",
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
        and never fabricates facts or returns empty content.
        """
        q_lower = question.lower()
        c_lower = context.lower()

        def clean_lines(lines_list):
            substantive = []
            for l in lines_list:
                line_str = l.strip()
                if line_str.startswith("[Entry"):
                    continue
                # If FAQ line, look for the Answer part
                if line_str.startswith("FAQ:") or line_str.startswith("Question:"):
                    continue
                if line_str.startswith("Category:") or line_str.startswith("Title:"):
                    continue
                if line_str.startswith("Answer:"):
                    ans_part = re.sub(r"^Answer:\s*", "", line_str, flags=re.IGNORECASE).strip()
                    if ans_part:
                        substantive.append(ans_part)
                    continue
                substantive.append(line_str)
            if substantive:
                return " ".join(substantive)
            return ""

        # 1. Address / Location intent
        addr_words = ["address", "location", "located", "where is", "where are", "street", "road", "pincode", "directions", "landmark", "situated"]
        if any(w in q_lower for w in addr_words):
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

        # 3. Product / Brand / Availability / Buy intent
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

        # 4. Delivery / Shipping intent
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

        # 5. Timings / Hours / Opening schedule intent (with follow-up support)
        time_words = ["time", "timing", "timings", "open", "opening", "close", "closing", "hours", "schedule", "sunday", "saturday", "weekend", "holiday"]
        is_time_q = any(w in q_lower for w in time_words)
        
        # Check if follow-up to a recent timing question
        if not is_time_q and conversation_history:
            recent_text = " ".join([m.get("message_content", "").lower() for m in conversation_history[-2:]])
            if any(w in recent_text for w in ["timing", "timings", "open", "close", "hours"]):
                if any(w in q_lower for w in ["sunday", "saturday", "monday", "weekend", "today", "tomorrow"]):
                    is_time_q = True

        if is_time_q:
            lines = context.split("\n")
            matching = [l.strip() for l in lines if any(k in l.lower() for k in ["open", "close", "am", "pm", "hours", "timing", "sunday", "monday", "holiday"]) and len(l.strip()) > 5 and not l.strip().startswith("[Entry")]
            sub = clean_lines(matching)
            if sub:
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

        # 6. General question check: Search for substantive matching lines
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
