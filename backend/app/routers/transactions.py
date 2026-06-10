from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user_id
from app.schemas.transaction import TransactionCreate, TransactionResponse, TransactionUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post(
    "/",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction(
    payload: TransactionCreate,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_supabase),
):
    """Create a new transaction for the authenticated user."""
    result = (
        db.table("transactions")
        .insert(
            {
                "user_id": user_id,
                "amount": float(payload.amount),
                "category": payload.category.value,
                "description": payload.description,
                "date": payload.date.isoformat(),
                "transaction_type": payload.transaction_type.value,
            }
        )
        .execute()
    )
    return result.data[0]


@router.get("/", response_model=list[TransactionResponse])
async def list_transactions(
    year: int = Query(default=None),
    month: int = Query(default=None, ge=1, le=12),
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_supabase),
):
    """List all transactions for the authenticated user.

    Optionally filter by year and month (both must be provided together).
    Results are ordered newest-first.
    """
    query = (
        db.table("transactions")
        .select("*")
        .eq("user_id", user_id)
        .order("date", desc=True)
    )

    if year and month:
        start = date(year, month, 1).isoformat()
        # Last day of month: use the first of next month minus a day
        if month == 12:
            end = date(year + 1, 1, 1).isoformat()
        else:
            end = date(year, month + 1, 1).isoformat()
        query = query.gte("date", start).lt("date", end)

    result = query.execute()
    return result.data


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: UUID,
    payload: TransactionUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_supabase),
):
    """Partially update a transaction. Only fields present in the request body are changed.

    Verifies ownership before updating to prevent cross-user modification.
    """
    existing = (
        db.table("transactions")
        .select("id")
        .eq("id", str(transaction_id))
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    updates = payload.model_dump(exclude_none=True)
    if "amount" in updates:
        updates["amount"] = float(updates["amount"])
    if "category" in updates:
        updates["category"] = updates["category"].value
    if "transaction_type" in updates:
        updates["transaction_type"] = updates["transaction_type"].value
    if "date" in updates:
        updates["date"] = updates["date"].isoformat()

    result = (
        db.table("transactions")
        .update(updates)
        .eq("id", str(transaction_id))
        .execute()
    )
    return result.data[0]


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_supabase),
):
    """Delete a transaction by ID.

    Verifies ownership before deletion to prevent users from deleting
    each other's records (defense-in-depth on top of service-role key usage).
    """
    existing = (
        db.table("transactions")
        .select("id")
        .eq("id", str(transaction_id))
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    db.table("transactions").delete().eq("id", str(transaction_id)).execute()
