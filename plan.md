# HyperGuard, Autonomous Fraud Intervention Swarm

> Build plan for a hackathon-grade, demo-able multi-agent system that detects social-engineering fraud and **intervenes in real time** before money leaves the account.

---

## 1. The One-Liner

**HyperGuard is an AI agent swarm that catches a victim mid-scam, calls them, talks them out of it, loops in their family, and, if it's too late, builds the evidence package to get their money back.**

The differentiator vs. existing tools (e.g. SG ScamShield): those stop at **detection + reporting**. HyperGuard owns the **real-time intervention → education → family escalation → recovery** loop.

---

## 2. Problem & Insight

- Fraud detection systems flag *suspicious transactions*. They cannot tell whether a customer is being **actively socially engineered** while the transaction happens.
- The money is often transferred *willingly* by the victim, so blocking the transaction alone fails and frustrates legitimate users.
- The gap is the **human moment**: the 60 seconds between "I'll send the money" and "money sent." HyperGuard inserts an agent into that moment.

**Bet:** A timely, contextual voice conversation + a trusted-contact alert changes the outcome more than a frozen transaction ever could.

---

## 3. The Swarm, 5 Agents

| # | Agent | Role | Core Output |
|---|-------|------|-------------|
| 1 | **Digital Twin** | Behavioural profiling + anomaly scoring | `risk_score` (0–1) + reasons |
| 2 | **Voice Negotiator** | Automated outbound call, contextual verification | call transcript + extracted intent |
| 3 | **Educator** | Classify scam narrative, deliver targeted warnings | `scam_type` + guidance script |
| 4 | **Guardian** | Escalate to pre-authorized trusted contacts | alert delivered + ack status |
| 5 | **Recovery Coordinator** | Post-incident evidence + report generation | evidence package (PDF/JSON) |

### Agent responsibilities (detailed)

**1. Digital Twin (Risk Scoring)**
- Builds a behavioural profile per customer from historical transactions: typical amounts, recipients, times, channels.
- Detects anomalies (new payee, off-hours, amount > Nσ from norm, velocity spikes).
- Emits a real-time `risk_score` + human-readable reasons; triggers the workflow when score crosses threshold.
- Hackathon impl: feature-based scoring (z-scores + rules) with an LLM "explainer", *not* a trained deep model.

**2. Voice Negotiator**
- Places an outbound call the instant a high-risk transfer is initiated.
- Runs a natural, scripted-but-adaptive conversation: "We noticed a transfer of $X to a new payee, can you confirm what it's for?"
- Streams answers to the Educator for live analysis; relays warnings back into the call.
- Primary human interaction layer. Twilio (telephony) + ElevenLabs (voice) + LLM (dialogue).

**3. Educator (Response Analysis)**
- Analyzes transcript for scam indicators & social-engineering tactics (urgency, secrecy, authority impersonation, "don't tell the bank").
- Classifies into known narratives: bank impersonation, govt/police impersonation, investment/crypto, romance, job scam, tech support.
- Returns the matching real-time guidance script the Negotiator should read aloud.

**4. Guardian (Family Network)**
- On high risk + ambiguous/failed verification, alerts pre-authorized trusted contacts (SMS/WhatsApp/call).
- Shares transaction context + risk assessment; requests human confirmation.
- Adds a human verification layer for vulnerable users (elderly, prior victims).

**5. Recovery Coordinator**
- Activates when a fraudulent transfer already completed.
- Generates an evidence package: transaction details, timeline, full conversation logs, risk rationale.
- Produces incident reports formatted for banks + law enforcement; streamlines recovery workflow.

---

## 4. System Architecture

```
Transaction Request
        │
        ▼
┌──────────────────────┐
│ Fraud Digital Twin   │  risk_score < threshold ──► APPROVE (fast path)
│ (Risk Scoring)       │
└──────────┬───────────┘
           │ risk_score ≥ threshold
           ▼
┌──────────────────────┐
│ AI Voice Negotiator  │◄────────────┐
└──────────┬───────────┘             │ guidance script
           │ transcript chunks       │
           ▼                         │
┌──────────────────────┐             │
│ Scam Education Agent  │─────────────┘
│ + Response Analysis   │
└──────────┬───────────┘
           │ verified? / scam detected?
           ▼
┌──────────────────────┐
│ Family Guardian       │  (on ambiguous / high risk)
│ Network               │
└──────────┬───────────┘
           ▼
   ┌───────────────┐
   │  DECISION     │──► Transfer APPROVED
   └───────┬───────┘──► Transfer BLOCKED
           │
           ▼ (if fraud already processed)
┌──────────────────────┐
│ Recovery Coordinator  │
└──────────────────────┘
```

**Orchestration model (LangGraph):** a stateful graph where nodes = agents and edges = conditional transitions on `risk_score`, `verification_status`, and `scam_detected`. Shared state object carries `transaction`, `customer_profile`, `risk`, `transcript`, `scam_type`, `decision`, `evidence`.

---

## 5. Tech Stack

| Layer | Choice | Hackathon note |
|-------|--------|----------------|
| Frontend | Next.js + TypeScript + Tailwind + shadcn/ui | Live "Mission Control" dashboard |
| Backend | FastAPI | REST + WebSocket for live updates |
| AI Orchestration | LangGraph | The swarm state machine |
| LLM | GPT-5.5 (or latest available) | Risk explain, dialogue, classification |
| Voice | Twilio + ElevenLabs | Outbound call + lifelike TTS |
| Database | Supabase (Postgres + pgvector) | Customers, txns, transcripts |
| Cache / Queue | Redis + Redis Streams | Event bus between agents |
| Workflow | Temporal *(optional)* | Durable long-running flows, **stretch** |
| Deploy | Vercel (FE) + Railway (BE) | |

> **Reality check:** Temporal + Kafka are production-grade and *time sinks* for a hackathon. Default to **Redis Streams** for the event bus and run LangGraph in-process. Add Temporal only if recovery flows need durability and time allows.

---

## 6. Scope Strategy, MVP vs. Stretch

The single most important hackathon decision. **Demo > completeness.**

### 🎯 MVP (must demo, the "golden path")
1. **Digital Twin** scores a seeded transaction as high-risk with readable reasons.
2. **Voice Negotiator** places a *real* outbound call (to a judge's phone) and has a coherent conversation.
3. **Educator** classifies the scam narrative live and feeds a warning back into the call.
4. **Dashboard** shows the swarm acting in real time (risk gauge, live transcript, decision).
5. **Decision**: transfer BLOCKED with a clear, explainable rationale.

### ➕ Stretch (do if ahead)
- **Guardian**: real SMS/WhatsApp alert to a "family member" phone with ack.
- **Recovery Coordinator**: one-click evidence-package PDF.
- Behavioural profile learned from a richer seeded history + pgvector similarity.
- Temporal-backed durable recovery workflow.

### ⛔ Explicitly out of scope
- Real bank/payment-rail integration (mock the transaction source).
- Training a real ML fraud model (use rules + z-scores + LLM explainer).
- Auth/multi-tenant/production security hardening.
- Mobile app.

---

## 7. Build Phases & Timeline (≈ 24–36h hackathon)

> Adjust hour markers to your actual clock. Order matters more than exact times.

**Phase 0, Foundations (0–3h)**
- Repo scaffold: `/frontend` (Next.js), `/backend` (FastAPI), `/agents` (LangGraph).
- Supabase project + schema (Section 8). Seed 1 customer + transaction history.
- Env/secrets wired: OpenAI, Twilio, ElevenLabs, Supabase, Redis.
- Health-check endpoint + a "hello swarm" LangGraph that returns canned state.

**Phase 1, Digital Twin + Backend Spine (3–8h)**
- Implement risk scoring (z-score on amount/time + new-payee rule + velocity).
- LLM explainer turns raw signals → human reasons.
- `POST /transaction` → runs Twin → returns `risk_score` + triggers graph.
- WebSocket channel pushing state updates to the dashboard.

**Phase 2, Voice Negotiator (8–16h), highest risk, start early in parallel**
- Twilio outbound call → media stream.
- ElevenLabs TTS for agent turns; STT for customer turns (Twilio/Whisper).
- LLM dialogue loop with the conversation script; stream transcript to backend.
- *De-risk first* with a non-voice text-chat fallback that exercises the same graph.

**Phase 3, Educator (12–18h, overlaps Phase 2)**
- Scam-narrative classifier (LLM few-shot over indicator taxonomy).
- Guidance scripts per scam type; injected back into the Negotiator turn.

**Phase 4, Dashboard "Mission Control" (overlaps everything, 6–20h)**
- Live risk gauge, agent timeline, streaming transcript, final decision card.
- This is what the judges *watch*, invest in it.

**Phase 5, Stretch: Guardian + Recovery (20–28h)**
- Guardian SMS via Twilio to a second phone.
- Recovery evidence-package generator (HTML→PDF).

**Phase 6, Demo hardening (last 4–6h)**
- Scripted demo scenario, seeded data, fallbacks for every live dependency.
- Record a backup video of the working flow (insurance against live failure).
- Rehearse the 3-minute pitch + live demo at least twice.

---

## 8. Data Model (Supabase / Postgres)

```sql
customers(
  id uuid pk, name, phone, risk_tolerance,
  baseline_avg_amount numeric, baseline_std_amount numeric,
  typical_hours int4range, created_at
)

trusted_contacts(
  id uuid pk, customer_id fk, name, phone, relationship, priority
)

transactions(
  id uuid pk, customer_id fk, amount numeric, currency,
  payee_name, payee_account, is_new_payee bool,
  channel, requested_at, status  -- pending|approved|blocked|completed
)

risk_assessments(
  id uuid pk, transaction_id fk, risk_score numeric,
  signals jsonb, reasons text, model_version, created_at
)

interventions(
  id uuid pk, transaction_id fk, call_sid, transcript jsonb,
  scam_type, scam_confidence numeric, decision, created_at
)

guardian_alerts(
  id uuid pk, transaction_id fk, contact_id fk,
  channel, status, acknowledged_at
)

evidence_packages(
  id uuid pk, transaction_id fk, package jsonb, pdf_url, created_at
)
```

---

## 9. Agent Orchestration (LangGraph sketch)

```python
# Shared state threaded through the graph
class SwarmState(TypedDict):
    transaction: dict
    customer: dict
    risk: dict            # {score, signals, reasons}
    transcript: list      # [{role, text, ts}]
    scam: dict            # {type, confidence, guidance}
    verification: str     # unknown|verified|failed
    decision: str         # approve|block
    evidence: dict | None

# Nodes: twin → (conditional) → negotiator ⇄ educator → guardian → decide → recover
# Edges:
#   twin:        score < T          -> approve (END)
#                score >= T         -> negotiator
#   negotiator:  each turn          -> educator
#   educator:    scam_detected      -> guardian
#                verified           -> decide(approve)
#                ambiguous          -> guardian
#   guardian:    contact_confirms   -> decide(approve)
#                no_ack / confirms_fraud -> decide(block)
#   decide:      block              -> recover (if already processed) else END
```

Keep the loop **bounded** (max N negotiator↔educator turns) so a demo can't hang.

---

## 10. Demo Script (the 3-minute story)

1. **Setup (15s):** "Meet Auntie May. A scammer posing as the police told her to transfer $8,000 to a 'safe account.'"
2. **Trigger (20s):** Initiate the transfer in the UI. Digital Twin lights up → risk 0.93, reasons: *new payee, 4× normal amount, 2am, urgency keywords*.
3. **Intervention (60s):** HyperGuard calls a judge's phone live. Negotiator asks what it's for; judge plays the victim ("the police told me..."). Educator classifies → **Government Impersonation**, pushes a warning the agent reads aloud.
4. **Escalation (20s):** Guardian texts "her son" (second phone), alert appears.
5. **Decision (15s):** Transfer **BLOCKED**, explainable rationale on screen.
6. **Recovery (20s):** Flip to a "too late" case → one-click evidence package PDF for the bank.
7. **Close (10s):** "Detection tells you *after*. HyperGuard intervenes *during*, and helps recover *after*."

**Every live dependency needs a fallback** (pre-recorded call audio, canned transcript, seeded decision) wired behind a "demo mode" flag.

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Live voice call fails on stage | High | "Demo mode": pre-recorded audio + scripted transcript path; backup video |
| Twilio/ElevenLabs latency | Med | Pre-warm; keep turns short; cap dialogue length |
| Scope creep across 5 agents | High | Lock MVP golden path; Guardian/Recovery are stretch |
| LLM nondeterminism in demo | Med | Low temperature; seeded inputs; few-shot prompts |
| Telephony setup eats hours | High | Start Phase 2 *first*, in parallel; text-chat fallback validates the graph early |
| Secrets/billing limits | Med | Verify Twilio number + ElevenLabs quota hour 0 |

---

## 12. Team Split (suggested, 3–4 people)

- **A, Agents/Orchestration:** LangGraph graph, Digital Twin scoring, Educator classifier.
- **B, Voice/Telephony:** Twilio + ElevenLabs pipeline, dialogue loop, transcript streaming.
- **C, Frontend:** Mission Control dashboard, WebSocket live updates, demo-mode toggle.
- **D, Backend/Data + Glue:** FastAPI, Supabase schema/seed, Guardian/Recovery, deploy, demo hardening.

Daily-ish syncs: after Phase 1 (spine works), after Phase 2 (call works), before Phase 6 (freeze + rehearse).

---

## 13. Repo Structure

```
HyperGuard/
├── plan.md                  # this file
├── README.md
├── frontend/                # Next.js + Tailwind + shadcn/ui
│   └── app/                 # dashboard, live transcript, decision view
├── backend/                 # FastAPI
│   ├── main.py              # routes + websocket
│   ├── agents/              # langgraph nodes
│   │   ├── digital_twin.py
│   │   ├── negotiator.py
│   │   ├── educator.py
│   │   ├── guardian.py
│   │   └── recovery.py
│   ├── graph.py             # LangGraph assembly
│   ├── voice/               # twilio + elevenlabs adapters
│   ├── db.py                # supabase client
│   └── seed.py              # demo data
└── infra/
    └── .env.example         # OPENAI, TWILIO, ELEVENLABS, SUPABASE, REDIS keys
```

---

## 14. Definition of Done (hackathon)

- [ ] Seeded customer + high-risk transaction triggers the Digital Twin.
- [ ] Risk score + human-readable reasons render on the dashboard.
- [ ] A real outbound call runs the Negotiator↔Educator loop end to end.
- [ ] Scam narrative classified live; warning surfaced in-call.
- [ ] Final decision (APPROVE/BLOCK) shown with rationale.
- [ ] "Demo mode" fallback works with no live dependencies.
- [ ] Backup demo video recorded.
- [ ] 3-minute pitch rehearsed twice.

---

## 15. First Steps (right now)

1. Scaffold the repo structure (Section 13) and push to GitHub.
2. Create Supabase project; run schema (Section 8); seed one customer + history.
3. Verify all API keys at hour 0: OpenAI, Twilio (with a real number), ElevenLabs, Supabase, Redis.
4. Stand up the "hello swarm" LangGraph + FastAPI WebSocket → dashboard placeholder.
5. **In parallel**, spike the Twilio→ElevenLabs outbound call, it's the long pole.
```
