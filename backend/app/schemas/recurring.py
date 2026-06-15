from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, condecimal

from app.schemas.transaction import Category, TransactionResponse, TransactionType


class RecurringCreate(BaseModel):
    """A monthly template: posts a transaction on day_of_month every
    month. Capped at 28 so the date exists in every month."""

    amount: condecimal(gt=0, decimal_places=2)  # type: ignore[valid-type]
    category: Category
    description: str = ""
    transaction_type: TransactionType
    day_of_month: int = Field(ge=1, le=28)


class RecurringResponse(BaseModel):
    id: UUID
    user_id: UUID
    amount: float
    category: Category
    description: str
    transaction_type: TransactionType
    day_of_month: int
    next_date: date


class PostDueResponse(BaseModel):
    """Transactions created by a catch-up run (may span several months
    if the user hasn't opened the app in a while)."""

    posted: list[TransactionResponse]
