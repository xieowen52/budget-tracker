import datetime
from datetime import date
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, condecimal


class Category(str, Enum):
    food = "food"
    transport = "transport"
    entertainment = "entertainment"
    shopping = "shopping"
    health = "health"
    subscriptions = "subscriptions"
    housing = "housing"
    other = "other"


class TransactionType(str, Enum):
    income = "income"
    expense = "expense"


class TransactionCreate(BaseModel):
    amount: condecimal(gt=0, decimal_places=2)  # type: ignore[valid-type]
    category: Category
    description: str = ''
    date: date
    transaction_type: TransactionType


class TransactionUpdate(BaseModel):
    # Use datetime.date to avoid the field name 'date' shadowing the type in Pydantic's class body
    amount: condecimal(gt=0, decimal_places=2) | None = None  # type: ignore[valid-type]
    category: Category | None = None
    description: str | None = None
    date: datetime.date | None = None
    transaction_type: TransactionType | None = None


class TransactionResponse(BaseModel):
    id: UUID
    user_id: UUID
    amount: float
    category: Category
    description: str
    date: date
    transaction_type: TransactionType


class ParseRequest(BaseModel):
    text: str


class ParsedTransaction(BaseModel):
    """Structured output returned by the Claude parsing endpoint."""

    amount: float
    category: Category
    description: str
    date: date
    transaction_type: TransactionType
    confidence_note: str | None = None
