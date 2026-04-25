"""
ai_explainer.py  — Person 3: AI / GLM Engineer
------------------------------------------------
Owns all AI interactions with the ILMU GLM API:
  - get_ai_explanation()  : main purchase advice (structured JSON)
  - get_followup_answer() : multi-turn follow-up questions
  - scan_receipt_image()  : vision-based receipt scanning

Improvements:
  - Prompt trimmed to ~300 tokens (was ~460) to reduce timeout risk
  - Temperature lowered to 0.3 for consistent financial advice
  - LRU cache — identical inputs skip the API call entirely
  - Real error messages surface to UI instead of silent fallbacks
"""

import json
import os
import re
import time
import hashlib
import urllib.error
import urllib.request

# ── Simple in-memory cache ────────────────────────────────────────────────────
# Stores (result, timestamp) keyed by a hash of the inputs.
# Entries expire after CACHE_TTL seconds so stale data doesn't linger.

_CACHE: dict = {}
_CACHE_TTL   = 120  # 2 minutes — shorter TTL since responses are now reliable


def _cache_key(*args) -> str:
    """Hash any set of args into a short cache key."""
    raw = json.dumps(args, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_get(key: str):
    entry = _CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["val"]
    return None


def _cache_set(key: str, val):
    _CACHE[key] = {"val": val, "ts": time.time()}


# ── Internal API helper ───────────────────────────────────────────────────────

_MAX_RETRIES = 2


def _call_ilmu(
    messages:    list,
    max_tokens:  int   = 2048,
    system:      str   = "",
    temperature: float = 0.3,
) -> str:
    """
    Calls ILMU GLM. Returns text response or an error string starting
    with __NO_KEY__ or __ERROR__ for easy detection upstream.
    """
    api_key = os.environ.get("ILMU_API_KEY", "")
    if not api_key:
        return "__NO_KEY__"

    payload: dict = {
        "model":       "ilmu-glm-5.1",
        "max_tokens":  max_tokens,
        "messages":    messages,
        "temperature": temperature,
        "thinking":    {"type": "disabled"},
    }
    if system:
        payload["system"] = system

    body = json.dumps(payload).encode()
    req  = urllib.request.Request(
        "https://api.ilmu.ai/anthropic/v1/messages",
        data=body,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
        },
    )

    for attempt in range(_MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode())
                # Extract the first text block from content (skip thinking blocks)
                for block in data.get("content", []):
                    if block.get("type") == "text" and block.get("text", "").strip():
                        return block["text"]
                # If no text block found, return empty (thinking consumed all tokens)
                return ""
        except urllib.error.HTTPError as e:
            err_body = e.read().decode()
            # Retry on server-side transient errors
            if e.code in (429, 502, 503, 504) and attempt < _MAX_RETRIES:
                time.sleep(2 ** attempt)
                continue
            return f"__ERROR__ HTTP {e.code}: {err_body}"
        except urllib.error.URLError as e:
            if attempt < _MAX_RETRIES:
                time.sleep(2 ** attempt)
                continue
            return f"__ERROR__ Network: {e.reason}"
        except Exception as e:
            return f"__ERROR__ {e}"


def _parse_json_response(raw: str, required_keys: list) -> dict:
    """
    Robustly parses AI JSON.
    Handles: markdown fences, truncated JSON, missing closing brace.
    Falls back to regex extraction per-field if all else fails.
    """
    clean = raw.strip().replace("```json", "").replace("```", "").strip()

    # Attempt 1: clean parse
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    # Attempt 2: fix truncated JSON by closing open braces
    try:
        if not clean.endswith("}"):
            open_braces = clean.count("{") - clean.count("}")
            if open_braces > 0:
                clean = clean.rstrip(",\n\r ") + "}" * open_braces
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    # Attempt 3: regex per-field (handles escaped quotes and newlines)
    result = {}
    for key in required_keys:
        # Match value even if it contains escaped quotes or spans lines
        match = re.search(
            rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"\s*[,}}\]]',
            raw, re.DOTALL
        )
        if match:
            val = match.group(1)
            # Unescape common escape sequences
            val = val.replace('\\"', '"').replace('\\n', ' ').replace('\\t', ' ')
            result[key] = val.strip()
        else:
            result[key] = ""
    return result


# ── Shared system prompt ──────────────────────────────────────────────────────
# Kept short — system prompts consume tokens too.

_SYSTEM_PROMPT = (
    "You are a personal finance advisor for the Malaysian market. "
    "Give concise, data-driven advice using the user's actual financial numbers. "
    "Reference relevant Malaysian platforms (Shopee/Lazada sales, Maybank2u, EPF) "
    "and local budget alternatives only when suggesting cheaper options. "
    "Use clear, professional English. Be direct — state the trade-off, "
    "explain why with numbers, suggest practical alternatives, "
    "and recommend one concrete action."
)


# ── Public API ────────────────────────────────────────────────────────────────

def get_ai_explanation(
    income:     float,
    expenses:   float,
    savings:    float,
    price:      float,
    item:       str,
    decision:   str,
    reason:     str,
    benchmarks: dict,
    persona:    str = "Young Professional",
    score:      int = 50,
    risk:       str = "MEDIUM",
    scenarios:  dict = None,
    category:   str = "Other",
    urgency:    int = 5,
) -> dict:
    """
    Returns structured AI advice dict:
      summary, tradeoff, explanation, alternatives, action, confidence, raw
    Cached for 5 minutes — identical inputs return instantly without API call.
    """
    # ── Cache check ───────────────────────────────────────────────────────────
    ck = _cache_key(income, expenses, savings, price, item, decision, persona,
                    score, risk, category, urgency)
    cached = _cache_get(ck)
    if cached:
        cached["from_cache"] = True
        return cached

    # ── Build concise prompt ─────────────────────────────────────────────────
    surplus     = income - expenses
    expense_pct = round(expenses / income * 100, 1) if income > 0 else 0

    # Peer summary — compact
    peer_line = ""
    if benchmarks:
        peer_line = (
            f"Peers(n={benchmarks.get('peer_count','?')}): "
            f"avg expenses RM{benchmarks.get('avg_expenses',0):,.0f}, "
            f"avg savings RM{benchmarks.get('avg_savings',0):,.0f}. "
        )

    # Scenario summary — compact
    scenario_line = ""
    if scenarios:
        buy_end  = scenarios.get("buy_now", [0])[-1]
        skip_end = scenarios.get("skip",    [0])[-1]
        scenario_line = (
            f"12mo projection: buy now=RM{buy_end:,.0f} saved, "
            f"skip=RM{skip_end:,.0f} saved. "
        )

    # Category-specific alternatives
    hints = {
        "Electronics": "budget brands, refurbished units, seasonal sales",
        "Transport":   "public transport passes, car-sharing, used vehicles",
        "Fashion":     "factory outlets, seasonal sales, mid-range brands",
        "Food":        "meal prep, bulk buying, promotional deals",
        "Essential":   "bulk purchases, warehouse clubs, government subsidies",
        "Other":       "secondhand marketplaces, seasonal sales events",
    }
    hint = hints.get(category, hints["Other"])

    user_prompt = (
        f"Profile: {persona}, Malaysia. "
        f"Purchase: {item} RM{price:,.0f} ({category}, urgency {urgency}/10). "
        f"Finances: Income RM{income:,.0f}/mo, Expenses RM{expenses:,.0f}/mo ({expense_pct}%), "
        f"Surplus RM{surplus:,.0f}/mo, Savings RM{savings:,.0f}. "
        f"Score: {score}/100 ({risk} risk). "
        f"{peer_line}{scenario_line}"
        f"Decision: {decision} — {reason}.\n"
        f"Reply as JSON only, no markdown:\n"
        f'{{"summary":"one clear sentence stating the recommendation",'
        f'"tradeoff":"specific RM amount gained or lost by buying vs skipping",'
        f'"explanation":"2-3 sentences explaining why, citing the user actual numbers",'
        f'"alternatives":"2-3 cheaper options ({hint})",'
        f'"action":"one specific step to take today",'
        f'"confidence":"HIGH or MEDIUM or LOW"}}'
    )

    raw = _call_ilmu(
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
    )

    # ── Error fallbacks ───────────────────────────────────────────────────────
    if raw.startswith("__NO_KEY__"):
        return {
            "summary":      "⚠️ AI Advisor offline — ILMU_API_KEY not set.",
            "tradeoff":     f"Buying costs RM{price:,.0f} from savings.",
            "explanation":  reason,
            "alternatives": f"Consider: {hint}",
            "action":       "Set ILMU_API_KEY in run.bat and restart.",
            "confidence":   "LOW", "raw": raw,
        }
    if raw.startswith("__ERROR__"):
        err = raw.replace("__ERROR__ ", "")
        is_server_error = any(code in err for code in ("504", "502", "503", "429"))
        return {
            "summary": (
                "⚠️ AI Advisor unavailable — the server is busy or timed out. "
                "This is not a bug, just a temporary server issue."
            ) if is_server_error else f"⚠️ {err}",
            "tradeoff":     "",
            "explanation":  reason,
            "alternatives": "",
            "action":       "Wait a moment and click Analyze Purchase again.",
            "confidence":   "LOW", "raw": raw,
        }

    # ── Parse + cache ─────────────────────────────────────────────────────────
    required = ["summary", "tradeoff", "explanation", "alternatives", "action", "confidence"]
    parsed   = _parse_json_response(raw, required)
    parsed["raw"]        = raw
    parsed["from_cache"] = False
    for key in required:
        if key not in parsed:
            parsed[key] = ""

    _cache_set(ck, parsed)
    return parsed


def get_followup_answer(
    question:     str,
    chat_history: list,
    context:      dict,
) -> str:
    """
    Multi-turn follow-up Q&A. Uses full chat history for context.
    Cached per (question + last assistant message) to avoid duplicate calls.
    Returns plain text.
    """
    # Cache key includes last reply so "ask again" still hits cache
    last_reply = chat_history[-1]["content"] if chat_history else ""
    ck = _cache_key(question, last_reply, context.get("item"), context.get("decision"))
    cached = _cache_get(ck)
    if cached:
        return cached

    income   = context.get("income",   0)
    expenses = context.get("expenses", 0)
    savings  = context.get("savings",  0)
    price    = context.get("price",    0)
    item     = context.get("item",     "the item")
    decision = context.get("decision", "DELAY")
    surplus  = income - expenses

    messages = [
        {
            "role": "user",
            "content": (
                f"[Context: {item} RM{price:,.0f}, "
                f"income RM{income:,.0f}/mo, expenses RM{expenses:,.0f}/mo, "
                f"surplus RM{surplus:,.0f}/mo, savings RM{savings:,.0f}. "
                f"Recommended: {decision}. Answer follow-ups in plain English, no JSON.]"
            )
        },
        {"role": "assistant", "content": "Understood, I have the financial context."},
    ]
    messages += chat_history
    messages.append({"role": "user", "content": question})

    raw = _call_ilmu(messages=messages, max_tokens=2048, system=_SYSTEM_PROMPT)

    if raw.startswith("__NO_KEY__") or raw.startswith("__ERROR__"):
        err = raw.replace("__NO_KEY__", "API key not set.").replace("__ERROR__ ", "")
        return f"⚠️ {err}"

    _cache_set(ck, raw)
    return raw


def scan_receipt_image(image_bytes: bytes, media_type: str) -> dict:
    """
    Extracts item + price from a receipt/price tag image.
    Returns: {"item": str, "price": float, "raw": str, "error": str|None}
    Returns error="VISION_NOT_SUPPORTED" if the model can't handle images.
    """
    import base64

    api_key = os.environ.get("ILMU_API_KEY", "")
    if not api_key:
        return {"item": "", "price": 0.0, "raw": "", "error": "ILMU_API_KEY not set."}

    img_b64 = base64.b64encode(image_bytes).decode()

    messages = [{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": img_b64}
            },
            {
                "type": "text",
                "text": (
                    "Find the TOTAL amount payable on this receipt/price tag.\n"
                    'Reply ONLY as JSON: {"item": "purchase type", "price": 123.45}\n'
                    'If no price found: {"item": "unknown", "price": 0}'
                )
            }
        ]
    }]

    body = json.dumps({
        "model": "ilmu-glm-5.1", "max_tokens": 2048, "messages": messages,
        "thinking": {"type": "disabled"},
    }).encode()

    req = urllib.request.Request(
        "https://api.ilmu.ai/anthropic/v1/messages",
        data=body,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode())
            # Extract first text block (skip thinking blocks)
            raw = ""
            for block in data.get("content", []):
                if block.get("type") == "text" and block.get("text", "").strip():
                    raw = block["text"].strip()
                    break

        parsed = _parse_json_response(raw, ["item", "price"])
        price  = 0.0
        try:
            price = float(str(parsed.get("price", 0)).replace(",", ""))
        except (ValueError, TypeError):
            pass

        if price > 0:
            return {"item": parsed.get("item", "Receipt total"), "price": price,
                    "raw": raw, "error": None}

        # Fallback: extract largest number from raw text
        candidates = []
        for m in re.findall(r"[\d,]+\.?\d*", raw):
            try:
                candidates.append(float(m.replace(",", "")))
            except ValueError:
                pass
        fallback = max(candidates) if candidates else 0.0
        return {
            "item":  parsed.get("item", "Receipt total"),
            "price": fallback,
            "raw":   raw,
            "error": "Number extraction fallback." if fallback > 0 else "No price found.",
        }

    except urllib.error.HTTPError as e:
        err = e.read().decode()
        if e.code in (400, 422):
            return {"item": "", "price": 0.0, "raw": err, "error": "VISION_NOT_SUPPORTED"}
        return {"item": "", "price": 0.0, "raw": err, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"item": "", "price": 0.0, "raw": "", "error": str(e)}
