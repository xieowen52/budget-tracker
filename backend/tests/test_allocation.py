from decimal import Decimal

import pytest

from app.schemas.transaction import Category
from app.services.allocation import (
    AllocationError,
    DEFAULT_WEIGHTS,
    compute_allocation,
)


def D(value: str) -> Decimal:
    return Decimal(value)


def test_default_weights_split_all_discretionary():
    """With no estimates, discretionary money is split by default weights
    and the parts sum exactly to the discretionary total."""
    result = compute_allocation(
        monthly_income=D("2000"),
        fixed_expenses={Category.housing: D("800")},
        variable_estimates={},
        savings_goal=D("1200"),
        horizon_months=6,
    )
    # 2000 - 800 fixed - 200 savings = 1000 discretionary
    assert result.monthly_savings == D("200.00")
    assert result.discretionary == D("1000.00")
    assert sum(result.variable.values()) == D("1000.00")
    assert result.unallocated == D("0.00")
    # Largest default weight (food) gets the largest share
    assert max(result.variable, key=lambda c: result.variable[c]) == Category.food
    assert set(result.variable) == set(DEFAULT_WEIGHTS)


def test_user_estimates_kept_when_they_fit():
    """Estimates under the discretionary total are kept verbatim and the
    surplus is reported as an unallocated buffer."""
    result = compute_allocation(
        monthly_income=D("2000"),
        fixed_expenses={Category.housing: D("800"), Category.subscriptions: D("50")},
        variable_estimates={Category.food: D("400"), Category.transport: D("100")},
        savings_goal=D("0"),
        horizon_months=6,
    )
    # 2000 - 850 fixed = 1150 discretionary; 500 estimated -> 650 buffer
    assert result.variable == {
        Category.food: D("400.00"),
        Category.transport: D("100.00"),
    }
    assert result.unallocated == D("650.00")


def test_overshooting_estimates_scaled_down_proportionally():
    """Estimates above the discretionary total are scaled to fit while
    preserving their relative proportions."""
    result = compute_allocation(
        monthly_income=D("1000"),
        fixed_expenses={Category.housing: D("500")},
        variable_estimates={Category.food: D("600"), Category.transport: D("400")},
        savings_goal=D("0"),
        horizon_months=6,
    )
    # 500 discretionary, estimates total 1000 -> halved
    assert result.variable == {
        Category.food: D("300.00"),
        Category.transport: D("200.00"),
    }
    assert result.unallocated == D("0.00")


def test_rounding_drift_lands_on_largest_share():
    """Cent-level rounding never makes the parts disagree with the total."""
    # 100 discretionary split three equal ways -> 33.33 each leaves a
    # 0.01 remainder that must land on one share, not vanish.
    result = compute_allocation(
        monthly_income=D("100"),
        fixed_expenses={},
        variable_estimates={
            Category.food: D("200"),
            Category.transport: D("200"),
            Category.entertainment: D("200"),
        },
        savings_goal=D("0"),
        horizon_months=12,
    )
    assert result.discretionary == D("100.00")
    assert sum(result.variable.values()) == D("100.00")


def test_overcommitted_budget_rejected():
    """Fixed + savings beyond income is an input error, not a silent
    negative budget."""
    with pytest.raises(AllocationError, match="exceed income"):
        compute_allocation(
            monthly_income=D("1000"),
            fixed_expenses={Category.housing: D("900")},
            variable_estimates={},
            savings_goal=D("1200"),
            horizon_months=6,
        )


def test_category_cannot_be_fixed_and_variable():
    with pytest.raises(AllocationError, match="both fixed and variable"):
        compute_allocation(
            monthly_income=D("2000"),
            fixed_expenses={Category.transport: D("100")},
            variable_estimates={Category.transport: D("50")},
            savings_goal=D("0"),
            horizon_months=6,
        )


def test_zero_amount_entries_dropped():
    """Zero-dollar fixed lines don't clutter the plan."""
    result = compute_allocation(
        monthly_income=D("2000"),
        fixed_expenses={Category.housing: D("800"), Category.subscriptions: D("0")},
        variable_estimates={},
        savings_goal=D("0"),
        horizon_months=6,
    )
    assert Category.subscriptions not in result.fixed
    assert result.fixed_total == D("800.00")


# ---------- apply_events ----------

from app.services.allocation import IrregularEvent, apply_events


def base_months(horizon: int = 3):
    """3-month base: 800 housing (fixed), 400 food + 200 transport
    (flexible), 100/month unallocated buffer."""
    amounts = {
        i: {
            Category.housing: D("800.00"),
            Category.food: D("400.00"),
            Category.transport: D("200.00"),
        }
        for i in range(horizon)
    }
    fixed = {i: {Category.housing} for i in range(horizon)}
    buffers = {i: D("100.00") for i in range(horizon)}
    return amounts, fixed, buffers


def test_absorb_event_consumes_buffer_before_budgets():
    """A cost smaller than the buffer leaves category budgets untouched."""
    amounts, fixed, buffers = base_months()
    event = IrregularEvent("Concert", Category.entertainment, D("80"), 1, "absorb")
    adj, bufs = apply_events(amounts, fixed, buffers, [event])
    assert adj[1][Category.food] == D("400.00")
    assert adj[1][Category.entertainment] == D("80")
    assert bufs[1] == D("20.00")
    # Other months untouched
    assert adj[0] == amounts[0] and bufs[0] == D("100.00")


def test_absorb_overflow_cuts_flexible_proportionally():
    """Cost beyond the buffer reduces flexible lines 2:1 (food:transport)
    and never touches the fixed housing line."""
    amounts, fixed, buffers = base_months()
    event = IrregularEvent("Car repair", Category.transport, D("400"), 0, "absorb")
    adj, bufs = apply_events(amounts, fixed, buffers, [event])
    # 400 - 100 buffer = 300 cut: food -200, transport -100
    assert bufs[0] == D("0.00")
    assert adj[0][Category.food] == D("200.00")
    assert adj[0][Category.transport] == D("100.00") + D("400")  # cut, then event added
    assert adj[0][Category.housing] == D("800.00")


def test_spread_event_charges_every_month_up_to_event():
    """'Save up for it': each month from the start contributes equally."""
    amounts, fixed, buffers = base_months()
    event = IrregularEvent("Flight home", Category.transport, D("270"), 2, "spread")
    adj, bufs = apply_events(amounts, fixed, buffers, [event])
    # 270 / 3 = 90/month, fully covered by each month's 100 buffer
    assert all(bufs[i] == D("10.00") for i in range(3))
    assert adj[2][Category.transport] == D("200.00") + D("270")
    assert adj[0][Category.food] == D("400.00")


def test_event_too_large_raises_with_event_name():
    amounts, fixed, buffers = base_months()
    event = IrregularEvent("New laptop", Category.shopping, D("2000"), 0, "absorb")
    with pytest.raises(AllocationError, match="New laptop"):
        apply_events(amounts, fixed, buffers, [event])


def test_apply_events_does_not_mutate_base():
    amounts, fixed, buffers = base_months()
    event = IrregularEvent("Concert", Category.entertainment, D("150"), 0, "absorb")
    apply_events(amounts, fixed, buffers, [event])
    assert amounts[0][Category.food] == D("400.00")
    assert buffers[0] == D("100.00")
