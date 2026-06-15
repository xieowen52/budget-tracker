"""Deterministic budget allocation engine.

Generates a plan's per-category monthly amounts from the wizard inputs.
Intentionally NOT an LLM call: the math here must be transparent,
reproducible, and explainable to the user ("where did this number come
from?"). Claude is reserved for the analysis layer, where it summarizes
numbers this engine and the transaction history produce.

The model:

    discretionary = income - sum(fixed expenses) - monthly savings

where monthly savings = savings_goal / horizon_months. Discretionary is
then split across the variable spending categories, either from the
user's own estimates (scaled down proportionally if they overshoot) or
from sensible student-budget default weights.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.schemas.transaction import Category

CENT = Decimal("0.01")

# Categories treated as discretionary/variable spending. Fixed expenses
# (housing, subscriptions, ...) are whatever the user lists as fixed; a
# category may not appear on both sides of one plan.
VARIABLE_CATEGORIES = [
    Category.food,
    Category.transport,
    Category.entertainment,
    Category.shopping,
    Category.health,
    Category.other,
]

# Default split of discretionary money when the user gives no estimates.
# Loosely based on typical student spending: food dominates, then
# transport, with a small buffer in 'other'.
DEFAULT_WEIGHTS: dict[Category, Decimal] = {
    Category.food: Decimal("0.35"),
    Category.transport: Decimal("0.20"),
    Category.entertainment: Decimal("0.15"),
    Category.shopping: Decimal("0.15"),
    Category.health: Decimal("0.10"),
    Category.other: Decimal("0.05"),
}


class AllocationError(ValueError):
    """Raised when the inputs cannot produce a viable budget."""


class AllocationResult:
    """Computed plan: one allocation map plus the summary numbers.

    Allocations are identical for every month in v1 — the router
    materializes them per month_index so the storage stays month-aware
    for future irregular-event support.
    """

    def __init__(
        self,
        fixed: dict[Category, Decimal],
        variable: dict[Category, Decimal],
        monthly_income: Decimal,
        monthly_savings: Decimal,
        discretionary: Decimal,
        unallocated: Decimal,
    ):
        self.fixed = fixed
        self.variable = variable
        self.monthly_income = monthly_income
        self.monthly_savings = monthly_savings
        self.fixed_total = sum(fixed.values(), Decimal("0"))
        self.discretionary = discretionary
        self.unallocated = unallocated


def _to_cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _split_by_weights(
    total: Decimal, weights: dict[Category, Decimal]
) -> dict[Category, Decimal]:
    """Split `total` across categories proportionally to `weights`.

    Rounds each share to cents, then puts any rounding drift on the
    largest share so the parts always sum exactly to `total`.
    """
    weight_sum = sum(weights.values(), Decimal("0"))
    if weight_sum == 0:
        return {cat: Decimal("0.00") for cat in weights}

    shares = {
        cat: _to_cents(total * w / weight_sum) for cat, w in weights.items()
    }
    drift = total - sum(shares.values(), Decimal("0"))
    if drift:
        largest = max(shares, key=lambda c: shares[c])
        shares[largest] += drift
    return shares


def compute_allocation(
    monthly_income: Decimal,
    fixed_expenses: dict[Category, Decimal],
    variable_estimates: dict[Category, Decimal],
    savings_goal: Decimal,
    horizon_months: int,
) -> AllocationResult:
    """Compute one month's budget allocation from the wizard inputs.

    Raises AllocationError when fixed expenses + savings exceed income,
    or when a category appears as both fixed and variable.
    """
    overlap = set(fixed_expenses) & set(variable_estimates)
    if overlap:
        names = ", ".join(sorted(c.value for c in overlap))
        raise AllocationError(
            f"Categories cannot be both fixed and variable: {names}"
        )

    fixed = {cat: _to_cents(amt) for cat, amt in fixed_expenses.items() if amt > 0}
    fixed_total = sum(fixed.values(), Decimal("0"))
    monthly_savings = _to_cents(savings_goal / horizon_months)

    discretionary = monthly_income - fixed_total - monthly_savings
    if discretionary < 0:
        shortfall = _to_cents(-discretionary)
        raise AllocationError(
            f"Fixed expenses ({fixed_total}) plus monthly savings "
            f"({monthly_savings}) exceed income ({monthly_income}) by "
            f"{shortfall}. Reduce fixed expenses or the savings goal."
        )

    estimates = {
        cat: _to_cents(amt) for cat, amt in variable_estimates.items() if amt > 0
    }
    estimate_total = sum(estimates.values(), Decimal("0"))

    if not estimates:
        # No estimates given: split all discretionary money by default weights.
        variable = _split_by_weights(discretionary, DEFAULT_WEIGHTS)
        unallocated = Decimal("0.00")
    elif estimate_total > discretionary:
        # Estimates overshoot what's affordable: scale them down
        # proportionally so the plan fits inside income.
        variable = _split_by_weights(discretionary, estimates)
        unallocated = Decimal("0.00")
    else:
        # Estimates fit: keep them as-is and surface the surplus as an
        # unallocated buffer rather than inflating category budgets.
        variable = estimates
        unallocated = _to_cents(discretionary - estimate_total)

    return AllocationResult(
        fixed=fixed,
        variable=variable,
        monthly_income=_to_cents(monthly_income),
        monthly_savings=monthly_savings,
        discretionary=_to_cents(discretionary),
        unallocated=unallocated,
    )


def apply_income_changes(
    amounts: dict[int, dict[Category, Decimal]],
    fixed: dict[int, set[Category]],
    buffers: dict[int, Decimal],
    base_income: Decimal,
    monthly_savings: Decimal,
    changes: dict[int, Decimal],
) -> tuple[dict[int, dict[Category, Decimal]], dict[int, Decimal]]:
    """Rescale months whose income differs from the plan's base income.

    `changes` maps month_index -> new monthly amount, applying from that
    month until the next change or the plan's end. Fixed lines and the
    savings set-aside stay untouched; the flexible lines and buffer are
    scaled proportionally to the new discretionary amount, so the user's
    relative priorities (food vs. fun) survive the change.

    Applied BEFORE events, so an event's feasibility is judged against
    the income actually available in its months.

    Raises AllocationError when a month's new income can't cover its
    fixed costs plus savings.
    """
    amounts = {i: dict(cats) for i, cats in amounts.items()}
    buffers = dict(buffers)

    effective = base_income
    for i in sorted(amounts):
        effective = changes.get(i, effective)
        if effective == base_income:
            continue

        fixed_total = sum(
            (amt for cat, amt in amounts[i].items() if cat in fixed[i]),
            Decimal("0"),
        )
        flexible = {
            cat: amt for cat, amt in amounts[i].items()
            if cat not in fixed[i] and amt > 0
        }
        base_disc = base_income - fixed_total - monthly_savings
        new_disc = effective - fixed_total - monthly_savings
        if new_disc < 0:
            shortfall = _to_cents(-new_disc)
            raise AllocationError(
                f"From month {i + 1}, income of {effective} can't cover fixed "
                f"costs ({fixed_total}) plus savings ({monthly_savings}) — "
                f"short by {shortfall}. Lower the savings goal or adjust "
                f"fixed costs first."
            )

        flexible_total = sum(flexible.values(), Decimal("0"))
        if base_disc > 0 and flexible_total > 0:
            new_flexible_total = _to_cents(flexible_total * new_disc / base_disc)
            scaled = _split_by_weights(min(new_flexible_total, new_disc), flexible)
            amounts[i].update(scaled)
            buffers[i] = new_disc - sum(scaled.values(), Decimal("0"))
        else:
            # Nothing flexible to scale — the whole change lands on the buffer
            buffers[i] = _to_cents(new_disc)

    return amounts, buffers


@dataclass(frozen=True)
class IrregularEvent:
    """A one-time planned expense attached to one plan month."""

    name: str
    category: Category
    amount: Decimal
    month_index: int
    funding: str  # "spread" (save up across prior months) or "absorb" (event month only)


def apply_events(
    amounts: dict[int, dict[Category, Decimal]],
    fixed: dict[int, set[Category]],
    buffers: dict[int, Decimal],
    events: list[IrregularEvent],
) -> tuple[dict[int, dict[Category, Decimal]], dict[int, Decimal]]:
    """Overlay irregular events on the base per-month allocations.

    The base rows in plan_allocations are never modified — this derives
    the adjusted view on each read, so deleting an event is just a row
    delete with no rewrite-drift to clean up.

    For each event, the cost is charged to one or more months ('absorb'
    = all of it on the event month; 'spread' = split evenly over months
    0..event month, i.e. saving up for it). Within each charged month
    the money comes from the unallocated buffer first, then from the
    flexible (non-fixed) category budgets proportionally. The event
    amount is then added to its category in the event month so the
    spending is *planned* there — analysis won't flag it as a blowout.

    Raises AllocationError when a month's buffer plus flexible budget
    cannot cover its share.
    """
    amounts = {i: dict(cats) for i, cats in amounts.items()}
    buffers = dict(buffers)

    for event in events:
        m = event.month_index

        # How much each month contributes toward the event's cost
        if event.funding == "spread":
            n_months = m + 1
            share = _to_cents(event.amount / n_months)
            shares = {i: share for i in range(n_months)}
            shares[m] += event.amount - share * n_months  # rounding drift
        else:
            shares = {m: event.amount}

        for i, share in shares.items():
            from_buffer = min(buffers[i], share)
            buffers[i] -= from_buffer
            remainder = share - from_buffer
            if remainder <= 0:
                continue

            flexible = {
                cat: amt
                for cat, amt in amounts[i].items()
                if cat not in fixed[i] and amt > 0
            }
            available = sum(flexible.values(), Decimal("0"))
            if remainder > available:
                raise AllocationError(
                    f"'{event.name}' (${event.amount}) doesn't fit: month "
                    f"{i + 1} of the plan only has ${available + from_buffer} "
                    f"of flexible budget. Lower the amount or use a "
                    f"different funding option."
                )
            cuts = _split_by_weights(remainder, flexible)
            for cat, cut in cuts.items():
                amounts[i][cat] -= cut
            # Cent-level rounding drift can overdraw the largest line by
            # $0.01 — repair it from any line that still has money.
            for cat in cuts:
                if amounts[i][cat] < 0:
                    deficit = -amounts[i][cat]
                    amounts[i][cat] = Decimal("0.00")
                    donor = max(flexible, key=lambda c: amounts[i][c])
                    amounts[i][donor] -= deficit

        amounts[m][event.category] = (
            amounts[m].get(event.category, Decimal("0.00")) + event.amount
        )

    return amounts, buffers
