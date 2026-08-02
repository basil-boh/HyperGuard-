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
  -- Sign-in credential: PBKDF2-HMAC-SHA256 of the customer's 6-digit PIN,
  -- "pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>". Never the PIN itself.
  pin_hash            text,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);
-- Phones are stored normalised to E.164, so login can match on equality.
create unique index if not exists users_phone_idx on users(phone);

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

-- ── Guardian network ───────────────────────────────────────────────────────────
-- Joins two real accounts, unlike `contacts` which is only a phone number the swarm
-- can reach. Consent belongs to the protected side: a link raised by a guardian
-- starts 'pending' until the protected account accepts.
create table if not exists guardian_links (
  id                 text primary key,               -- "lnk_…"
  guardian_user_id   text not null references users(id) on delete cascade,
  protected_user_id  text not null references users(id) on delete cascade,
  relationship       text not null default 'family', -- guardian's relation TO the protected
  status             text not null default 'pending',-- pending | active | declined | revoked
  invited_by         text not null default 'guardian',
  created_at         timestamptz not null default now(),
  responded_at       timestamptz,
  constraint guardian_links_not_self check (guardian_user_id <> protected_user_id)
);
create unique index if not exists guardian_links_pair_idx
  on guardian_links(guardian_user_id, protected_user_id);
create index if not exists guardian_links_protected_idx on guardian_links(protected_user_id, status);

-- One case report delivered to one guardian. The body is always read live from
-- `cases`; only delivery state and a headline snapshot live here.
create table if not exists incident_reports (
  id                text primary key,                -- "inc_…"
  case_id           text not null references cases(case_id) on delete cascade,
  protected_user_id text not null references users(id) on delete cascade,
  protected_name    text,
  guardian_user_id  text not null references users(id) on delete cascade,
  sent_at           timestamptz not null default now(),
  sent_by_user_id   text,                            -- null when the swarm delivered it
  read_at           timestamptz,
  note              text,
  amount            numeric not null default 0,
  currency          text not null default 'SGD',
  payee_name        text,
  scam_title        text,
  decision          text not null default 'block',
  risk_score        numeric not null default 0
);
create unique index if not exists incident_reports_case_guardian_idx
  on incident_reports(case_id, guardian_user_id);
create index if not exists incident_reports_guardian_idx on incident_reports(guardian_user_id, sent_at desc);

-- SIMULATED authority filings. HyperGuard is not connected to the police, the
-- National Anti-Scam Centre, or any other body: nothing here was ever transmitted.
-- `simulated` defaults true and every reference is prefixed 'SIM-' so a row read
-- straight out of the database still says so.
create table if not exists authority_filings (
  case_id          text primary key references cases(case_id) on delete cascade,
  reference        text not null,                    -- "SIM-NASC-2026-0F7C21"
  authority        text not null,
  filed_by_user_id text not null,
  filed_at         timestamptz not null default now(),
  status           text not null default 'received',
  timeline         jsonb not null default '[]',
  simulated        boolean not null default true
);

-- ── Migrations for an EXISTING database (safe to re-run) ───────────────────────
alter table cases add column if not exists context    jsonb;
alter table cases add column if not exists assessment jsonb;
alter table cases add column if not exists escalation jsonb;
alter table cases add column if not exists report     text;

-- Login (added with the PIN sign-in flow). The backend backfills PINs for the
-- seeded customers on the next boot, so this column is all that's needed by hand.
alter table users add column if not exists pin_hash text;
create unique index if not exists users_phone_idx on users(phone);

-- The guardian network tables above are `create table if not exists`, so running
-- this whole file again on an existing database adds them and changes nothing else.
