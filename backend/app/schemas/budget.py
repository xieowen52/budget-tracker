from uuid import UUID

from pydantic import BaseModel, condecimal

from app.schemas.transaction import Category


class BudgetUpsert(BaseModel):
    category: Category
    monthly_limit: condecimal(gt=0, decimal_places=2)  # type: ignore[valid-type]


class BudgetResponse(BaseModel):
    id: UUID
    user_id: UUID
    category: Category
    monthly_limit: float


class BudgetProgressItem(BaseModel):
    category: Category
    monthly_limit: float
    spent: float
    percentage: float
    over_limit: bool
