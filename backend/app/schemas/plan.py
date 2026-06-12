from datetime import date
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, condecimal, model_validator

from app.schemas.transaction import Category


class FundingMode(str, Enum):
    """How the plan is funded: regular monthly income, or a fixed pool
    of cash (savings, a loan refund) that has to last the whole plan."""

    income = "income"
    pot = "pot"


class FundingStrategy(str, Enum):
    """Where an irregular event's money comes from: saved up evenly
    across the months before it, or taken out of the event month."""

    spread = "spread"
    absorb = "absorb"


class PlanEventCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    category: Category
    amount: condecimal(gt=0, decimal_places=2)  # type: ignore[valid-type]
    month_index: int = Field(ge=0)
    funding: FundingStrategy


class PlanEventResponse(BaseModel):
    id: UUID
    name: str
    category: Category
    amount: float
    month_index: int
    funding: FundingStrategy


class PlanCreate(BaseModel):
    """Wizard payload. fixed_expenses are off-the-top amounts (rent,
    subscriptions); variable_estimates are optional — when omitted the
    allocation engine splits discretionary money by default weights.

    funding_mode 'income' requires monthly_income; 'pot' requires
    total_funds instead, and savings_goal means "amount left at the
    end" rather than "amount saved up"."""

    funding_mode: FundingMode = FundingMode.income
    monthly_income: condecimal(gt=0, decimal_places=2) | None = None  # type: ignore[valid-type]
    total_funds: condecimal(gt=0, decimal_places=2) | None = None  # type: ignore[valid-type]
    start_date: date
    horizon_months: int = Field(default=6, ge=1, le=24)
    savings_goal: condecimal(ge=0, decimal_places=2) = 0  # type: ignore[valid-type]
    fixed_expenses: dict[Category, condecimal(ge=0, decimal_places=2)] = {}  # type: ignore[valid-type]
    variable_estimates: dict[Category, condecimal(ge=0, decimal_places=2)] = {}  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _funding_fields_match_mode(self):
        if self.funding_mode == FundingMode.income and self.monthly_income is None:
            raise ValueError("monthly_income is required when funding_mode is 'income'")
        if self.funding_mode == FundingMode.pot and self.total_funds is None:
            raise ValueError("total_funds is required when funding_mode is 'pot'")
        return self


class AllocationItem(BaseModel):
    category: Category
    amount: float
    is_fixed: bool


class PlanMonthView(BaseModel):
    month_index: int
    year: int
    month: int
    allocations: list[AllocationItem]
    unallocated: float = 0.0  # buffer left after events take their share


class PlanSummary(BaseModel):
    """The arithmetic behind the plan, surfaced so the UI can show the
    user exactly where each number came from."""

    monthly_income: float
    fixed_total: float
    monthly_savings: float
    discretionary: float
    unallocated: float


class PlanResponse(BaseModel):
    id: UUID
    user_id: UUID
    start_date: date
    horizon_months: int
    savings_goal: float
    funding_mode: FundingMode = FundingMode.income
    total_funds: float | None = None
    summary: PlanSummary
    months: list[PlanMonthView]  # event-adjusted view, not the stored base
    events: list[PlanEventResponse] = []


class PlanPreviewResponse(BaseModel):
    """Result of running the allocation engine without persisting —
    shown on the wizard's review step before the user commits."""

    summary: PlanSummary
    allocations: list[AllocationItem]


class MonthCategoryActual(BaseModel):
    category: Category
    planned: float
    actual: float
    difference: float  # positive = under budget, negative = over


class MonthAnalysis(BaseModel):
    month_index: int
    year: int
    month: int
    income_actual: float
    expenses_actual: float
    savings_actual: float  # income - expenses for the month
    savings_planned: float
    categories: list[MonthCategoryActual]
    # Pot mode only: burn-rate tracking at the end of this month
    remaining_funds: float | None = None
    expected_remaining: float | None = None


class AnalysisInsights(BaseModel):
    """Claude's narrative over the computed numbers. None when no API
    key is configured."""

    going_well: list[str]
    needs_attention: list[str]
    suggestions: list[str]


class PlanAnalysisResponse(BaseModel):
    funding_mode: FundingMode = FundingMode.income
    months_analyzed: int
    months: list[MonthAnalysis]
    consistently_over: list[Category]  # over budget in >= 2/3 of months
    consistently_under: list[Category]
    insights: AnalysisInsights | None = None
    insights_note: str | None = None
