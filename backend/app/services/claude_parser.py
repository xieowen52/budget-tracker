import json
from datetime import date

import anthropic

from app.core.config import settings
from app.schemas.transaction import Category, ParsedTransaction, TransactionType

# The exact prompt sent to Claude — kept as a module-level constant so it's
# easy to inspect, tune, and reference in code review.
PARSE_SYSTEM_PROMPT = """You are a financial transaction parser. The user will describe a purchase, payment, or income in natural language. Extract the transaction details and return ONLY a JSON object with these fields:

- amount: positive number (no currency symbol)
- category: one of "food", "transport", "entertainment", "shopping", "health", "subscriptions", "other"
- description: short, clean description (max 60 chars)
- date: ISO 8601 date string (YYYY-MM-DD); infer from relative phrases like "last night", "yesterday", "this morning" relative to today's date which is provided by the user
- transaction_type: "income" or "expense"
- confidence_note: optional short string if any field is ambiguous or assumed

Category guidelines:
- food: restaurants, groceries, coffee, drinks
- transport: gas, Uber, Lyft, subway, parking, flights
- entertainment: movies, concerts, games, streaming (Netflix, Hulu)
- shopping: clothing, electronics, Amazon, general retail
- health: gym, pharmacy, doctor, dental
- subscriptions: recurring software/services (Spotify, iCloud, SaaS)
- other: anything that doesn't fit

Return ONLY the JSON object, no markdown fences, no explanation."""

_MOCK_RESPONSE = ParsedTransaction(
    amount=12.99,
    category=Category.food,
    description="Sample transaction (AI parsing disabled)",
    date=date.today(),
    transaction_type=TransactionType.expense,
    confidence_note="ANTHROPIC_API_KEY not set — this is a mock response",
)


async def parse_transaction_text(text: str, today: date) -> ParsedTransaction:
    """Send natural language text to Claude and return a structured transaction.

    Uses claude-sonnet-4-6 with a strict JSON instruction so the
    response is always machine-parseable without a fallback parser.
    Falls back to a mock response when ANTHROPIC_API_KEY is not configured.
    """
    if not settings.anthropic_api_key:
        return _MOCK_RESPONSE

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    user_message = f"Today's date is {today.isoformat()}.\n\nTransaction: {text}"

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=PARSE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.AuthenticationError:
        raise ValueError("Anthropic API key is invalid. Set a valid key or remove ANTHROPIC_API_KEY from .env to use mock mode.")

    raw = message.content[0].text.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude returned non-JSON response: {raw[:200]}") from exc

    return ParsedTransaction(
        amount=float(data["amount"]),
        category=Category(data["category"]),
        description=data["description"],
        date=date.fromisoformat(data["date"]),
        transaction_type=TransactionType(data["transaction_type"]),
        confidence_note=data.get("confidence_note"),
    )
