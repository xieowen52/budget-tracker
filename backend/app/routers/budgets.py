from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user_id
from app.schemas.budget import BudgetProgressItem, BudgetResponse, BudgetUpsert
from app.schemas.transaction import Category

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.put("/{category}", response_model=BudgetResponse)
async def upsert_budget(
    category: Category,
    payload: BudgetUpsert,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_supabase),
):
    """Create or update the monthly spending limit for a category.

    Uses an upsert on the (user_id, category) unique constraint so the
    client doesn't need to track whether a limit already exists.
    """
    if payload.category != category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category in URL and body must match",
        )
    result = (
        db.table("budgets")
        .upsert(
            {
                "user_id": user_id,
                "category": category.value,
                "monthly_limit": float(payload.monthly_limit),
            },
            on_conflict="user_id,category",
        )
        .execute()
    )
    return result.data[0]


@router.get("/", response_model=list[BudgetResponse])
async def list_budgets(
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_supabase),
):
    """List all budget limits set by the authenticated user."""
    result = (
        db.table("budgets")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    return result.data


@router.get("/progress", response_model=list[BudgetProgressItem])
async def budget_progress(
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_supabase),
):
    """Return each budget limit alongside how much has been spent this month.

    Computes spending by joining against the transactions table filtered to
    the current calendar month. Only categories with a set limit are returned.
    """
    today = date.today()
    start = date(today.year, today.month, 1).isoformat()
    if today.month == 12:
        end = date(today.year + 1, 1, 1).isoformat()
    else:
        end = date(today.year, today.month + 1, 1).isoformat()

    budgets_result = (
        db.table("budgets").select("*").eq("user_id", user_id).execute()
    )
    budgets = budgets_result.data

    if not budgets:
        return []

    transactions_result = (
        db.table("transactions")
        .select("category, amount")
        .eq("user_id", user_id)
        .eq("transaction_type", "expense")
        .gte("date", start)
        .lt("date", end)
        .execute()
    )

    # Aggregate spending per category in Python — avoids a raw SQL RPC call
    spending: dict[str, float] = {}
    for tx in transactions_result.data:
        spending[tx["category"]] = spending.get(tx["category"], 0.0) + tx["amount"]

    progress = []
    for b in budgets:
        spent = spending.get(b["category"], 0.0)
        limit = b["monthly_limit"]
        progress.append(
            BudgetProgressItem(
                category=b["category"],
                monthly_limit=limit,
                spent=spent,
                percentage=round((spent / limit) * 100, 1) if limit else 0.0,
                over_limit=spent > limit,
            )
        )

    return progress


@router.delete("/{category}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    category: Category,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_supabase),
):
    """Remove the spending limit for a category."""
    existing = (
        db.table("budgets")
        .select("id")
        .eq("user_id", user_id)
        .eq("category", category.value)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget limit not found",
        )
    db.table("budgets").delete().eq("user_id", user_id).eq(
        "category", category.value
    ).execute()
