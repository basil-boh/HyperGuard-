-- HyperGuard persistence schema (Supabase / Postgres).
-- Run once in the Supabase SQL editor. Ids are text to match existing fixed ids
-- ("acc_alex", "rcp_quick", "HG-…"). Money is numeric; blobs are jsonb. FKs cascade.

-- users (CustomerProfile + Account, merged 1:1)
create table if not exists users (
  id                  text primary key,            -- "acc_alex"
  name                text not null,
  phone               text not null,
  age                 int,
  vulnerability_flags jsonb not null default '[]',
  home_country        text not null default 'SG',
  known_payees        jsonb not null default '[]',
  known_payee_phones  jsonb not null default '[]',
  account_number      text not null,
  currency            text not null default 'SGD',
  balance             numeric not null default 0,
  is_app_user         boolean not null default false,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

-- recipients (saved payees; phone/country power PayNow-style signals)
create table if not exists recipients (
  id         text primary key,                     -- "rcp_quick"
  user_id    text not null references users(id) on delete cascade,
  name       text not null,
  account    text,
  bank       text,
  phone      text,
  country    text,
  saved      boolean not null default true,
  archetype  text,                                 -- hidden scam tag; never serialised to the client
  created_at timestamptz not null default now()
);
create index if not exists recipients_user_idx on recipients(user_id);

-- contacts (trusted_contacts / next of kin)
create table if not exists contacts (
  id           text primary key,
  user_id      text not null references users(id) on delete cascade,
  name         text not null,
  phone        text not null,
  relationship text not null,
  priority     int not null default 1,
  created_at   timestamptz not null default now()
);
create index if not exists contacts_user_idx on contacts(user_id);

-- transactions (the ledger)
create table if not exists transactions (
  id            text primary key,
  user_id       text not null references users(id) on delete cascade,
  ts            timestamptz not null,
  direction     text not null,                     -- "out" | "in"
  counterparty  text not null,
  amount        numeric not null,
  currency      text not null default 'SGD',
  status        text not null,                     -- approved | blocked | completed
  decision      text,
  risk_score    numeric,
  scam_type     text,
  memo          text,
  case_id       text,
  payee_account text,
  payee_phone   text,
  payee_country text,
  created_at    timestamptz not null default now()
);
create index if not exists transactions_user_ts_idx on transactions(user_id, ts desc);

-- cases (full CaseRecord; shared by the wallet + scenario paths)
create table if not exists cases (
  case_id         text primary key,
  user_id         text references users(id) on delete cascade,
  user_name       text,
  created_at      text not null,
  transaction     jsonb not null default '{}',
  decision        text not null,
  status          text not null,
  risk_score      numeric,
  band            text,
  risk_signals    jsonb not null default '[]',
  rationale       text,
  scam_type       text,
  classification  jsonb,
  guardian_alerts jsonb not null default '[]',
  transcript      jsonb not null default '[]',
  evidence        jsonb,
  narrative       text,
  -- Voice follow-up: the victim's spoken answers, the LLM's assessment, escalation
  -- record, and the generated incident report.
  context         jsonb,
  assessment      jsonb,
  escalation      jsonb,
  report          text
);
create index if not exists cases_user_created_idx on cases(user_id, created_at desc);

-- ── Migration for an EXISTING cases table (run once if you created it earlier) ──
alter table cases add column if not exists context    jsonb;
alter table cases add column if not exists assessment jsonb;
alter table cases add column if not exists escalation jsonb;
alter table cases add column if not exists report     text;
