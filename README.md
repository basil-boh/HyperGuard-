<div align="center">

# 🛡️ HyperGuard

### Autonomous Fraud Intervention Swarm

**Detection tells you *after*. HyperGuard intervenes *during*, and helps recover *after*.**

An AI agent swarm that catches a victim mid-scam, calls them, talks them out of it,
loops in their family, and, if it's too late, builds the evidence to get their money back.

[Problem](#-the-problem) · [How It Works](#-how-it-works) · [The Swarm](#-the-swarm) · [Architecture](#-architecture) · [Tech Stack](#-tech-stack) · [Getting Started](#-getting-started) · [Demo](#-demo)

</div>

---

## 🔥 The Problem

Despite advanced fraud detection and public-awareness campaigns, scammers still manipulate victims into **willingly** transferring money to fraudulent accounts.

Traditional systems can flag a *suspicious transaction*, but they can't tell whether a customer is being **socially engineered in real time**. The money is sent by the victim's own hand, so simply blocking the transfer fails the user and misses the real problem.

The gap is the **human moment**: the 60 seconds between *"I'll send the money"* and *"money sent."*

> **HyperGuard inserts an AI agent into that moment.**

### How it's different

Existing shields (e.g. Singapore's **ScamShield**) focus on **detection and reporting**. They don't do **real-time intervention**, **family monitoring**, **behavioural analysis**, or **fund-recovery orchestration**.

That's exactly the gap HyperGuard fills.

---

## ⚡ How It Works

```
  💸 Transaction Request
          │
          ▼
  ① Digital Twin scores it in real time ──► low risk ──► ✅ Approved (instant)
          │ high risk
          ▼
  ② Voice Negotiator calls the customer ⇄ ③ Educator classifies the scam live
          │                                   (feeds warnings back into the call)
          ▼
  ④ Guardian alerts a trusted family contact
          │
          ▼
  🚦 Decision ──► ✅ Approved   or   🛑 Blocked
          │
          ▼ (if money already moved)
  ⑤ Recovery Coordinator builds the evidence package
```

A customer starts a transfer. The **Digital Twin** scores it against their behavioural baseline. If it's anomalous, the swarm activates: the **Voice Negotiator** calls them, the **Educator** identifies the scam narrative and feeds warnings back into the live conversation, the **Guardian** loops in a trusted contact, and a final decision approves or blocks the transfer. If fraud already slipped through, the **Recovery Coordinator** assembles everything investigators need.

---

## 🤖 The Swarm

| | Agent | What it does |
|---|-------|--------------|
| ① | **Digital Twin** | Builds a behavioural profile per customer (typical amounts, payees, times). Detects anomalies and assigns a real-time fraud **risk score** with human-readable reasons. Triggers the intervention when behaviour deviates sharply. |
| ② | **Voice Negotiator** | Places an automated outbound call the moment a high-risk transfer is detected. Conducts contextual verification through natural conversation and gathers the purpose & circumstances of the transfer. |
| ③ | **Educator** | Analyzes the customer's responses for scam indicators and social-engineering tactics. Classifies the narrative, **bank / government impersonation, investment, romance, job scam**, and delivers targeted, real-time warnings. |
| ④ | **Guardian** | Escalates high-risk cases to **pre-authorized trusted contacts** (family, caregivers). Shares transaction context and risk, adding a human verification layer for vulnerable users. |
| ⑤ | **Recovery Coordinator** | Activates when fraud has already been processed. Generates an **evidence package**, transaction details, timeline, conversation logs, formatted for banks and law enforcement to streamline recovery. |

---

## 🏗 Architecture

```
Transaction Request
        │
        ▼
┌──────────────────────┐
│ Fraud Digital Twin   │  risk < threshold ──► APPROVE (fast path)
│ (Risk Scoring)       │
└──────────┬───────────┘
           │ risk ≥ threshold
           ▼
┌──────────────────────┐         guidance script
│ AI Voice Negotiator  │◄───────────────────────┐
└──────────┬───────────┘                         │
           │ transcript chunks                   │
           ▼                                     │
┌──────────────────────┐                         │
│ Scam Education Agent  │─────────────────────────┘
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

The swarm is a **LangGraph state machine**: nodes are agents, edges are conditional transitions on `risk_score`, `verification_status`, and `scam_detected`. A shared state object carries the transaction, customer profile, risk assessment, live transcript, scam classification, decision, and evidence through the graph.

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js · TypeScript · Tailwind (bespoke design system) · React-Three-Fiber · GSAP |
| **Backend** | FastAPI |
| **AI Orchestration** | LangGraph |
| **LLM** | GPT-5.5 |
| **Voice** | Twilio · ElevenLabs |
| **Database** | Supabase (PostgreSQL + pgvector) |
| **Cache / Event Bus** | Redis · Redis Streams |
| **Workflow** | Temporal *(optional, for durable recovery flows)* |
| **Deployment** | Vercel (frontend) · Railway (backend) |

---

## 🚀 Getting Started

### Prerequisites

- Node.js 20+ and Python 3.11+
- Accounts/keys for: **OpenAI**, **Twilio** (with a provisioned phone number), **ElevenLabs**, **Supabase**
- Redis (local Docker or hosted)

### 1. Clone & configure

```bash
git clone https://github.com/<your-org>/HyperGuard.git
cd HyperGuard
cp infra/.env.example .env   # then fill in your keys
```

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py                       # smoke-test the swarm across all scenarios
uvicorn app.main:app --reload --port 8000
```

> `python seed.py` runs every scenario through the full swarm with **no API keys**,
> printing each decision, a one-command proof the orchestration is wired correctly.
> `pytest` runs the test suite.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev             # http://localhost:3000
```

### 4. Mobile wallet simulator (optional)

A companion **Expo** app that simulates a bank, fake balance, transfers, payees,
and next-of-kin, so the swarm has real transactions to act on. Every transfer runs
through the agents; sending to a (hidden) scam payee is caught and blocked live.

```bash
# backend must be reachable on your LAN:
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
# then:
cd mobile && npm install && npx expo start   # open in Expo Go
```

The app auto-discovers the backend from the Expo dev host, no config needed on a
phone. See [mobile/README.md](./mobile/README.md) for the demo script.

### Environment variables

```ini
OPENAI_API_KEY=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
ELEVENLABS_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
REDIS_URL=
DEMO_MODE=true          # uses scripted fallbacks for live deps
```

> **Tip:** Set `DEMO_MODE=true` to run the full swarm flow with scripted call audio and seeded data, no live telephony required. Ideal for development and as a stage fallback.

---

## 📁 Project Structure

```
HyperGuard/
├── plan.md                       # detailed build plan & roadmap
├── README.md                     # you are here
├── docker-compose.yml            # backend + Redis
├── backend/                      # FastAPI + LangGraph
│   ├── app/
│   │   ├── main.py               # app entrypoint (REST + WebSocket)
│   │   ├── config.py             # capability-gated settings (graceful degradation)
│   │   ├── graph.py              # LangGraph swarm orchestrator
│   │   ├── state.py · schemas.py # shared state + domain models
│   │   ├── runtime.py            # service container (DI)
│   │   ├── agents/               # the 5 agents + arbiter
│   │   ├── services/             # risk engine · scam taxonomy · dialogue · llm
│   │   ├── integrations/         # voice · notifications · event bus · persistence
│   │   ├── api/                  # routes · ws · wallet (app) · admin (control centre)
│   │   ├── wallet/               # multi-account bank: accounts, cases, registry
│   │   └── data/seed_data.py     # demo personas & scenarios
│   ├── tests/                    # risk-engine + end-to-end swarm tests
│   └── seed.py                   # one-command smoke test
├── frontend/                     # Next.js, the bank's CONTROL CENTRE
│   ├── app/console/              # overview · users/[id] · cases/[id] · live
│   ├── components/
│   │   ├── landing/              # Hero3D (R3F) · ShieldStage · ScrollStory
│   │   ├── control/              # ControlShell · MetricTile · CaseRow · CustomerRow
│   │   └── console/              # RiskMeter · RelayTrack · TranscriptStream (live view)
│   └── lib/                      # admin (control-centre API) · useSwarmStream
├── mobile/                       # Expo wallet, the CUSTOMER's banking app
│   ├── app/                      # Wallet · Activity · Guardians · transfer · intervention
│   ├── components/               # AgentRelay · RiskGauge · Transcript · TxnRow
│   └── lib/                      # api · config (auto host) · useIntervention (poll+reduce)
└── infra/
    ├── .env.example
    └── schema.sql                # optional Supabase schema
```

---

## 🎬 Demo

**The scenario:** Auntie May gets a call from a scammer posing as the police, telling her to move \$8,000 to a "safe account."

1. The transfer is initiated → **Digital Twin** flags it: *risk 0.93, new payee, 4× normal amount, 2 AM, urgency keywords.*
2. **HyperGuard calls her live.** The Negotiator asks what the transfer is for.
3. **Educator** classifies the narrative → **Government Impersonation** and pushes a warning the agent reads aloud.
4. **Guardian** texts her son, the alert lands on his phone.
5. Transfer **BLOCKED**, with a clear, explainable rationale on the dashboard.
6. For a "too late" case → one-click **evidence package** ready for the bank.

> 📹 *Demo video and live dashboard link to be added.*

---

## 🗺 Roadmap

See **[plan.md](./plan.md)** for the full build plan, phased timeline, data model, and orchestration details.

- [x] Concept, architecture, and agent design
- [x] Digital Twin risk scoring + live console dashboard
- [x] Voice Negotiator ↔ Educator live loop (LangGraph)
- [x] Guardian trusted-contact alerts
- [x] Recovery evidence packages + dossier view
- [x] Real-time event stream (WebSocket) + 3D/GSAP landing
- [ ] Wire live API keys (LLM dialogue, Twilio call, ElevenLabs voice)
- [ ] Durable recovery workflows (Temporal)

---

## ⚠️ Disclaimer

HyperGuard is a hackathon prototype for demonstration purposes. It is **not** a production financial-security system and is not integrated with real banking or payment rails. Do not use it to make real fraud-prevention decisions without appropriate review, testing, and compliance.

---

<div align="center">

Built with ❤️ to put an AI agent in the room when it matters most.

</div>
