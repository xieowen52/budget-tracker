-- ============================================================
-- Budget Tracker — Supabase Schema
-- Run this in the Supabase SQL Editor (project > SQL Editor > New query)
-- ============================================================

-- Enable UUID generation (already enabled on Supabase, but harmless to add)
create extension if not exists "pgcrypto";

-- ============================================================
-- USERS
-- Stores email + bcrypt-hashed password managed by our FastAPI
-- backend (NOT Supabase Auth). Supabase Auth is bypassed so we
-- have full control over the auth flow for interview demo purposes.
-- ============================================================
create table if not exists users (
    id            uuid primary key default gen_random_uuid(),
    email         text not null unique,
    password_hash text not null,
    created_at    timestamptz not null default now()
);

-- ============================================================
-- TRANSACTIONS
-- ============================================================
create type transaction_category as enum (
    'food', 'transport', 'entertainment',
    'shopping', 'health', 'subscriptions', 'housing', 'other'
);

-- MIGRATION (existing databases only): the enum above is only created on
-- fresh installs. If your database predates the 'housing' category, run
-- this single statement on its own (ADD VALUE cannot run inside a
-- transaction with other statements):
--
--   alter type transaction_category add value if not exists 'housing' before 'other';

create type transaction_type as enum ('income', 'expense');

create table if not exists transactions (
    id               uuid primary key default gen_random_uuid(),
    user_id          uuid not null references users(id) on delete cascade,
    amount           numeric(12, 2) not null check (amount > 0),
    category         transaction_category not null,
    description      text not null,
    date             date not null,
    transaction_type transaction_type not null,
    created_at       timestamptz not null default now()
);

-- Index for the common query: all transactions for a user in a date range
create index if not exists transactions_user_date
    on transactions(user_id, date desc);

-- ============================================================
-- BUDGETS
-- Monthly spending limits per category, per user.
-- (user_id, category) is unique — one limit per category.
-- ============================================================
create table if not exists budgets (
    id            uuid primary key default gen_random_uuid(),
    user_id       uuid not null references users(id) on delete cascade,
    category      transaction_category not null,
    monthly_limit numeric(12, 2) not null check (monthly_limit > 0),
    created_at    timestamptz not null default now(),
    constraint budgets_user_category_unique unique (user_id, category)
);

-- ============================================================
-- RECURRING TRANSACTIONS
-- Templates that auto-post a transaction monthly (rent, paycheck,
-- subscriptions). There is no scheduler on free-tier hosting, so
-- posting is catch-up-on-activity: the client calls
-- POST /recurring/post-due when the app loads, and the backend posts
-- everything with next_date <= today (looping if months were missed),
-- then advances next_date. day_of_month is capped at 28 so every
-- month has the date.
-- ============================================================
create table if not exists recurring_transactions (
    id               uuid primary key default gen_random_uuid(),
    user_id          uuid not null references users(id) on delete cascade,
    amount           numeric(12, 2) not null check (amount > 0),
    category         transaction_category not null,
    description      text not null,
    transaction_type transaction_type not null,
    day_of_month     int not null check (day_of_month between 1 and 28),
    next_date        date not null,
    created_at       timestamptz not null default now()
);

create index if not exists recurring_user on recurring_transactions(user_id);

-- ============================================================
-- PLANS
-- A multi-month budget plan generated from the onboarding wizard.
-- One plan per user for now (unique index); creating a new plan
-- replaces the old one. savings_goal is the total amount the user
-- wants saved (or, in pot mode, left over) by the end of the plan;
-- the monthly savings line is derived as savings_goal / horizon.
--
-- funding_mode: 'income' = regular monthly income; 'pot' = living
-- off a fixed pool of cash (total_funds) with no expected income —
-- monthly_income then stores the derived monthly draw
-- (total_funds / horizon_months) so the allocation math is shared.
-- ============================================================
create table if not exists plans (
    id             uuid primary key default gen_random_uuid(),
    user_id        uuid not null references users(id) on delete cascade,
    start_date     date not null,
    horizon_months int not null check (horizon_months between 1 and 24),
    monthly_income numeric(12, 2) not null check (monthly_income > 0),
    savings_goal   numeric(12, 2) not null default 0 check (savings_goal >= 0),
    funding_mode   text not null default 'income' check (funding_mode in ('income', 'pot')),
    total_funds    numeric(12, 2) check (total_funds > 0),
    created_at     timestamptz not null default now(),
    constraint plans_one_per_user unique (user_id)
);

-- MIGRATION (existing databases only):
--
--   alter table plans add column if not exists funding_mode text not null default 'income'
--       check (funding_mode in ('income', 'pot'));
--   alter table plans add column if not exists total_funds numeric(12, 2) check (total_funds > 0);

-- ============================================================
-- PLAN ALLOCATIONS
-- Per-month, per-category amounts. month_index is 0-based from the
-- plan's start_date. Allocations are materialized per month (rather
-- than one flat number) so future features — one-time expenses,
-- income changes mid-plan — can adjust individual months without a
-- schema change. is_fixed marks off-the-top lines (rent,
-- subscriptions) vs. allocated discretionary spending.
-- ============================================================
create table if not exists plan_allocations (
    id          uuid primary key default gen_random_uuid(),
    plan_id     uuid not null references plans(id) on delete cascade,
    month_index int not null check (month_index >= 0),
    category    transaction_category not null,
    amount      numeric(12, 2) not null check (amount >= 0),
    is_fixed    boolean not null,
    constraint plan_allocations_unique unique (plan_id, month_index, category)
);

create index if not exists plan_allocations_plan
    on plan_allocations(plan_id, month_index);

-- ============================================================
-- PLAN EVENTS
-- One-time irregular expenses (a trip, a laptop) attached to a
-- specific plan month. Events never modify plan_allocations: the
-- stored allocations are the untouched base, and the API derives
-- event-adjusted months on every read. funding says where the money
-- comes from: 'spread' = saved up evenly across all months up to the
-- event, 'absorb' = taken out of the event month alone. Either way
-- the month's unallocated buffer is consumed before flexible
-- category budgets are reduced.
-- ============================================================
create table if not exists plan_events (
    id          uuid primary key default gen_random_uuid(),
    plan_id     uuid not null references plans(id) on delete cascade,
    name        text not null,
    category    transaction_category not null,
    amount      numeric(12, 2) not null check (amount > 0),
    month_index int not null check (month_index >= 0),
    funding     text not null check (funding in ('spread', 'absorb')),
    created_at  timestamptz not null default now()
);

create index if not exists plan_events_plan on plan_events(plan_id);

-- ============================================================
-- PLAN INCOME CHANGES
-- "From month N onward, the monthly income/draw is X." Like events,
-- these never modify plan_allocations — the API rescales each
-- affected month's flexible lines and buffer on read, proportionally
-- to the new discretionary amount. One change per month; a later
-- change supersedes an earlier one from its month onward.
-- ============================================================
create table if not exists plan_income_changes (
    id             uuid primary key default gen_random_uuid(),
    plan_id        uuid not null references plans(id) on delete cascade,
    month_index    int not null check (month_index >= 0),
    monthly_amount numeric(12, 2) not null check (monthly_amount > 0),
    created_at     timestamptz not null default now(),
    constraint plan_income_changes_unique unique (plan_id, month_index)
);

-- ============================================================
-- ROW LEVEL SECURITY
-- We use the service-role key in FastAPI (bypasses RLS), so
-- these policies are defense-in-depth in case the anon key is
-- ever accidentally used or exposed.
-- ============================================================
alter table users                  enable row level security;
alter table transactions           enable row level security;
alter table budgets                enable row level security;
alter table plans                  enable row level security;
alter table plan_allocations       enable row level security;
alter table plan_events            enable row level security;
alter table recurring_transactions enable row level security;
alter table plan_income_changes    enable row level security;

-- Block all access via the anon/authenticated roles (we manage auth ourselves)
create policy "deny_all_users"            on users            as restrictive for all using (false);
create policy "deny_all_transactions"     on transactions     as restrictive for all using (false);
create policy "deny_all_budgets"          on budgets          as restrictive for all using (false);
create policy "deny_all_plans"            on plans            as restrictive for all using (false);
create policy "deny_all_plan_allocations" on plan_allocations as restrictive for all using (false);
create policy "deny_all_plan_events"      on plan_events      as restrictive for all using (false);
create policy "deny_all_recurring"        on recurring_transactions as restrictive for all using (false);
create policy "deny_all_income_changes"   on plan_income_changes    as restrictive for all using (false);
