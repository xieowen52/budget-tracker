"""Claude-powered narrative layer over the budget analysis.

All the numbers are computed deterministically in the plans router;
Claude only turns them into readable insights and suggestions. This
mirrors the claude_parser pattern: strict JSON output, module-level
prompt constant, graceful fallback when no API key is configured.
"""

import json

import anthropic

from app.core.config import settings
from app.schemas.plan import AnalysisInsights

ADVISOR_SYSTEM_PROMPT = """You are a budget coach for students and young adults reviewing someone's budget performance. You will receive a JSON object with their plan vs. actual spending per month and per category, including which categories were consistently over or under budget.

If funding_mode is "pot", the person is living off a fixed pool of money with little or no income (e.g. a student between jobs). Ignore monthly savings framing entirely; focus on burn rate — compare remaining_funds to expected_remaining each month, say plainly whether the money will last the plan at the current pace, and frame suggestions around stretching the pool.

Return ONLY a JSON object with these fields:

- going_well: array of 1-3 short strings highlighting genuine positives (under-budget categories, hitting savings targets). Empty array if nothing qualifies.
- needs_attention: array of 1-3 short strings naming the real problem areas, with concrete numbers from the data.
- suggestions: array of 2-3 short, specific, actionable suggestions tied to the data (e.g. reallocating between categories, adjusting an unrealistic limit). No generic advice like "spend less".

Rules:
- Every claim must be backed by the numbers provided. Do not invent data.
- Use a supportive, practical tone. Amounts in dollars, rounded to whole numbers.
- Keep each string under 140 characters.

Return ONLY the JSON object, no markdown fences, no explanation."""


async def generate_insights(analysis_data: dict) -> AnalysisInsights | None:
    """Ask Claude to narrate the computed analysis numbers.

    Returns None when no API key is configured so the endpoint can
    still serve the deterministic numbers without AI insights.
    """
    if not settings.anthropic_api_key:
        return None

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=ADVISOR_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(analysis_data)}],
    )

    raw = message.content[0].text.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude returned non-JSON response: {raw[:200]}") from exc

    return AnalysisInsights(
        going_well=data.get("going_well", []),
        needs_attention=data.get("needs_attention", []),
        suggestions=data.get("suggestions", []),
    )
