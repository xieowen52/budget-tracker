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
    'shopping', 'health', 'subscriptions', 'other'
);

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
-- ROW LEVEL SECURITY
-- We use the service-role key in FastAPI (bypasses RLS), so
-- these policies are defense-in-depth in case the anon key is
-- ever accidentally used or exposed.
-- ============================================================
alter table users        enable row level security;
alter table transactions enable row level security;
alter table budgets      enable row level security;

-- Block all access via the anon/authenticated roles (we manage auth ourselves)
create policy "deny_all_users"        on users        as restrictive for all using (false);
create policy "deny_all_transactions" on transactions as restrictive for all using (false);
create policy "deny_all_budgets"      on budgets      as restrictive for all using (false);
