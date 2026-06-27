-- HyperGuard — Supabase / Postgres schema
-- Optional: the swarm runs without persistence. Apply this to durably store
-- customers, transactions, and closed cases. Run in the Supabase SQL editor.

create extension if not exists "pgcrypto";

-- ── Customers & their behavioural baseline ───────────────────────────────────
create table if not exists customers (
    id                      text primary key,
    name                    text not null,
    phone                   text not null,
    age                     int,
    vulnerability_flags     text[] default '{}',
    baseline_avg_amount     numeric not null,
    baseline_std_amount     numeric not null,
    typical_hour_start      int default 8,
    typical_hour_end        int default 22,
    typical_velocity_per_day numeric default 1.5,
    known_payees            text[] default '{}',
    created_at              timestamptz default now()
);

create table if not exists trusted_contacts (
    id            text primary key,
    customer_id   text references customers(id) on delete cascade,
    name          text not null,
    phone         text not null,
    relationship  text,
    priority      int default 1
);

-- ── Transactions ─────────────────────────────────────────────────────────────
create table if not exists transactions (
    id                       text primary key,
    customer_id              text references customers(id) on delete cascade,
    amount                   numeric not null,
    currency                 text default 'SGD',
    payee_name               text not null,
    payee_account            text,
    channel                  text,
    memo                     text,
    requested_at             timestamptz not null,
    recent_transfer_count_24h int default 0,
    status                   text default 'pending'
);

-- ── Closed cases (denormalised: full outcome travels in `outcome` jsonb) ──────
create table if not exists cases (
    case_id        text primary key,
    customer_id    text,
    customer_name  text,
    decision       text,
    risk_score     numeric,
    scam_type      text,
    outcome        jsonb not null,
    created_at     timestamptz default now()
);

create index if not exists cases_customer_idx on cases(customer_id);
create index if not exists cases_created_idx  on cases(created_at desc);

-- ── Per-case detail tables (populate from the outcome jsonb if you want SQL
--    reporting over individual signals, turns, alerts, and evidence) ──────────
create table if not exists risk_assessments (
    id              uuid primary key default gen_random_uuid(),
    case_id         text references cases(case_id) on delete cascade,
    transaction_id  text,
    score           numeric,
    band            text,
    signals         jsonb,
    rationale       text,
    created_at      timestamptz default now()
);

create table if not exists guardian_alerts (
    id           uuid primary key default gen_random_uuid(),
    case_id      text references cases(case_id) on delete cascade,
    contact_name text,
    channel      text,
    status       text,
    acknowledged boolean default false,
    created_at   timestamptz default now()
);

create table if not exists evidence_packages (
    id           uuid primary key default gen_random_uuid(),
    case_id      text references cases(case_id) on delete cascade,
    package      jsonb not null,
    created_at   timestamptz default now()
);
