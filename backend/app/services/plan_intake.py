"""Conversational intake for the plan wizard.

Turns a free-text description of someone's financial situation into the
structured fields the wizard collects. Extraction uses tool use with a
forced tool_choice: Claude must "call" the recording tool, so the
response is always schema-shaped tool input rather than free text that
needs parsing. The LLM never computes the budget — extracted fields are
prefilled into the wizard, the deterministic engine does the math, and
the user confirms before anything is saved (the same parse → confirm
pattern as transaction parsing, scaled up to a whole plan).
"""

from datetime import date

import anthropic

from app.core.config import settings
from app.schemas.plan import FundingMode, FundingStrategy, IntakeEventDraft, PlanIntakeResponse
from app.schemas.transaction import Category

INTAKE_SYSTEM_PROMPT = """You extract budget-planning information from a person's plain-language description of their financial situation. They are typically a student or young adult. Record what they state or strongly imply using the tool — never invent numbers they didn't give.

Context for your extraction:
- The budget plan starts on the first day of the CURRENT month. month_index 0 = this month, 1 = next month, and so on. Use today's date (provided in the message) to convert named months like "March" to a month_index (always in the future, within the plan).
- funding_mode: "income" if they have regular monthly money coming in; "pot" if they're living off a fixed amount of savings with no income for the plan period; "unknown" if they didn't make this clear.
- savings_goal: in income mode, the total they want saved by the end; in pot mode, the amount they want left over at the end.
- horizon_months: only if they state or imply a duration ("until May", "this semester" ≈ 4-6 months — prefer what maps to their words). Omit if unstated.
- fixed_expenses: same-every-month bills, keyed by category. housing = rent/utilities/internet; subscriptions = Spotify, iCloud, streaming, etc.
- variable_estimates: month-to-month spending they estimate, keyed by category (food, transport, entertainment, shopping, health, other).
- events: one-time irregular expenses (a trip, a laptop, concert tickets) with name, category, amount, month_index, and funding "spread" (save up for it — the default) or "absorb" (take the hit that month) if they express a preference.
- follow_up_questions: 1-2 short questions ONLY for information that is essential and missing — essential means: how the plan is funded (income amount or total savings). Do not ask about optional things (savings goal, spending estimates, plan length). Empty array if the essentials are covered.
- confidence_note: one short sentence if you made a notable assumption (e.g. mapped "semester" to 5 months). This is shown directly to the user: write it in plain language with real month names ("through next May", "in March 2027") — never mention month_index or any other internal field name.

Amounts are numbers without currency symbols. Interpret "10k" as 10000."""

INTAKE_TOOL = {
    "name": "record_budget_situation",
    "description": "Record the budget-planning fields extracted from the user's description of their financial situation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "funding_mode": {
                "type": "string",
                "enum": ["income", "pot", "unknown"],
                "description": "How the plan period is funded; 'unknown' if not stated",
            },
            "monthly_income": {"type": "number", "description": "Monthly income (income mode only)"},
            "total_funds": {"type": "number", "description": "Total fixed pool of cash (pot mode only)"},
            "horizon_months": {"type": "integer", "minimum": 1, "maximum": 24},
            "savings_goal": {"type": "number", "minimum": 0},
            "fixed_expenses": {
                "type": "object",
                "properties": {
                    "housing": {"type": "number"},
                    "subscriptions": {"type": "number"},
                },
                "additionalProperties": False,
            },
            "variable_estimates": {
                "type": "object",
                "properties": {
                    "food": {"type": "number"},
                    "transport": {"type": "number"},
                    "entertainment": {"type": "number"},
                    "shopping": {"type": "number"},
                    "health": {"type": "number"},
                    "other": {"type": "number"},
                },
                "additionalProperties": False,
            },
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "maxLength": 60},
                        "category": {
                            "type": "string",
                            "enum": [c.value for c in Category],
                        },
                        "amount": {"type": "number", "exclusiveMinimum": 0},
                        "month_index": {"type": "integer", "minimum": 0},
                        "funding": {"type": "string", "enum": ["spread", "absorb"]},
                    },
                    "required": ["name", "category", "amount", "month_index", "funding"],
                },
            },
            "follow_up_questions": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 2,
            },
            "confidence_note": {"type": "string"},
        },
        "required": ["funding_mode", "follow_up_questions"],
    },
}

_MOCK_RESPONSE = PlanIntakeResponse(
    funding_mode=FundingMode.income,
    monthly_income=2000.0,
    horizon_months=6,
    fixed_expenses={Category.housing: 800.0},
    confidence_note="ANTHROPIC_API_KEY not set — this is a mock extraction",
)


def _positive_amounts(raw: dict | None) -> dict[Category, float]:
    if not raw:
        return {}
    return {Category(k): float(v) for k, v in raw.items() if v and float(v) > 0}


async def extract_plan_from_text(text: str, today: date) -> PlanIntakeResponse:
    """Extract wizard fields from a free-text financial description.

    Falls back to a mock response when ANTHROPIC_API_KEY is not set,
    mirroring the transaction parser's behavior.
    """
    if not settings.anthropic_api_key:
        return _MOCK_RESPONSE

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    user_message = f"Today's date is {today.isoformat()}.\n\nTheir description:\n{text}"

    try:
        message = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=2048,
            system=INTAKE_SYSTEM_PROMPT,
            tools=[INTAKE_TOOL],
            tool_choice={"type": "tool", "name": "record_budget_situation"},
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.AuthenticationError:
        raise ValueError(
            "Anthropic API key is invalid. Set a valid key or remove "
            "ANTHROPIC_API_KEY from .env to use mock mode."
        )

    tool_use = next((b for b in message.content if b.type == "tool_use"), None)
    if tool_use is None:
        raise ValueError("Claude did not return a structured extraction")
    data = tool_use.input

    mode_raw = data.get("funding_mode", "unknown")
    funding_mode = FundingMode(mode_raw) if mode_raw in ("income", "pot") else None

    events = [
        IntakeEventDraft(
            name=e["name"][:60],
            category=Category(e["category"]),
            amount=float(e["amount"]),
            month_index=int(e["month_index"]),
            funding=FundingStrategy(e["funding"]),
        )
        for e in data.get("events", [])
        if float(e.get("amount", 0)) > 0
    ]

    def _opt_positive(key: str) -> float | None:
        value = data.get(key)
        return float(value) if value is not None and float(value) > 0 else None

    horizon = data.get("horizon_months")
    return PlanIntakeResponse(
        funding_mode=funding_mode,
        monthly_income=_opt_positive("monthly_income"),
        total_funds=_opt_positive("total_funds"),
        horizon_months=int(horizon) if horizon else None,
        savings_goal=_opt_positive("savings_goal"),
        fixed_expenses=_positive_amounts(data.get("fixed_expenses")),
        variable_estimates=_positive_amounts(data.get("variable_estimates")),
        events=events,
        follow_up_questions=[q for q in data.get("follow_up_questions", []) if q][:2],
        confidence_note=data.get("confidence_note"),
    )
