from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user_id
from app.schemas.recurring import PostDueResponse, RecurringCreate, RecurringResponse

router = APIRouter(prefix="/recurring", tags=["recurring"])


def _next_month_same_day(d: date) -> date:
    """Same day_of_month, one month later (day <= 28, so always valid)."""
    total = d.year * 12 + d.month  # zero-based index of the NEXT month
    return date(total // 12, total % 12 + 1, d.day)


def _first_occurrence(day_of_month: int, today: date) -> date:
    """When a new template should first post.

    If the day hasn't passed yet this month (or is today), it's due this
    month — the user presumably hasn't logged it. If it already passed,
    they likely logged it manually, so start next month.
    """
    if day_of_month >= today.day:
        return date(today.year, today.month, day_of_month)
    return _next_month_same_day(date(today.year, today.month, day_of_month))


@router.post("/", response_model=RecurringResponse, status_code=status.HTTP_201_CREATED)
async def create_recurring(
    payload: RecurringCreate,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_supabase),
):
    """Create a monthly recurring transaction template."""
    result = (
        db.table("recurring_transactions")
        .insert(
            {
                "user_id": user_id,
                "amount": float(payload.amount),
                "category": payload.category.value,
                "description": payload.description,
                "transaction_type": payload.transaction_type.value,
                "day_of_month": payload.day_of_month,
                "next_date": _first_occurrence(payload.day_of_month, date.today()).isoformat(),
            }
        )
        .execute()
    )
    return result.data[0]


@router.get("/", response_model=list[RecurringResponse])
async def list_recurring(
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_supabase),
):
    """List the user's recurring transaction templates."""
    result = (
        db.table("recurring_transactions")
        .select("*")
        .eq("user_id", user_id)
        .order("day_of_month")
        .execute()
    )
    return result.data


@router.delete("/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring(
    recurring_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_supabase),
):
    """Remove a template. Already-posted transactions are kept."""
    existing = (
        db.table("recurring_transactions")
        .select("id")
        .eq("id", str(recurring_id))
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recurring transaction not found"
        )
    db.table("recurring_transactions").delete().eq("id", str(recurring_id)).execute()


@router.post("/post-due", response_model=PostDueResponse)
async def post_due(
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_supabase),
):
    """Post every recurring transaction that has come due.

    Free-tier hosting has no scheduler, so this runs as catch-up when
    the client opens the app: each template with next_date <= today
    posts one transaction per elapsed occurrence (covering missed
    months), then next_date advances past today. Idempotent for the
    rest of the day once caught up.
    """
    today = date.today()
    due = (
        db.table("recurring_transactions")
        .select("*")
        .eq("user_id", user_id)
        .lte("next_date", today.isoformat())
        .execute()
    ).data

    posted = []
    for template in due:
        next_date = date.fromisoformat(template["next_date"])
        while next_date <= today:
            result = (
                db.table("transactions")
                .insert(
                    {
                        "user_id": user_id,
                        "amount": template["amount"],
                        "category": template["category"],
                        "description": template["description"],
                        "date": next_date.isoformat(),
                        "transaction_type": template["transaction_type"],
                    }
                )
                .execute()
            )
            posted.append(result.data[0])
            next_date = _next_month_same_day(next_date)
        db.table("recurring_transactions").update(
            {"next_date": next_date.isoformat()}
        ).eq("id", template["id"]).execute()

    return PostDueResponse(posted=posted)
