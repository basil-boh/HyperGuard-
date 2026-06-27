# 🛡️ HyperGuard — Presentation Script

A presenter's script for the live demo + pitch. **Bold bracketed** lines are stage
directions (what to do on screen); quoted lines are what you say. Target ≈ 3 minutes
for the main run, with a 60-second elevator cut and Q&A prep at the bottom.

---

## 0. Before you go on (setup checklist)

```bash
# Terminal 1 — backend (from repo root)
cd backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev          # http://localhost:3000

# Terminal 3 — mobile wallet (optional, for the live phone demo)
cd mobile && npx expo start         # open in Expo Go on your phone
```

**Have these open and ready:**
- 🖥️ Browser tab A → `http://localhost:3000` (the landing page, scrolled to top)
- 🖥️ Browser tab B → `http://localhost:3000/console/live` (mission-control live view)
- 📱 Phone → the wallet app on the home screen, logged in as a seeded user

> Demo runs in **demo mode** (deterministic, no live telephony) — say "simulated" if asked.
> The intervention, transcript, risk score, guardian alert and verdict are all real
> system output; only the outbound phone call is scripted.

---

## 1. The hook — 20s

**[Tab A: landing hero. Let the shield render. Don't scroll yet.]**

> "Banks have spent billions on fraud detection. And yet last year, most fraud
> losses came from payments the victims sent **with their own hands** — because a
> scammer talked them into it.
>
> You can't firewall a phone call. The defences were never breached — the *person* was."

**[Point at the headline: "Detection tells you *after*. HyperGuard intervenes *during*."]**

> "That's the gap HyperGuard closes."

---

## 2. The problem, in their own numbers — 30s

**[Scroll slowly to the stats row.]**

> "Ninety-four percent of fraud losses are payments the customer authorised
> themselves. The whole scam lives in a sixty-second window — between *'I'll send
> it'* and *'sent.'* No human fraud team can be in that moment for every customer."

**[Keep scrolling — the live interceptions feed is streaming, counter ticking up.]**

> "So we built a layer that can. This is the swarm working in real time — every row
> is a scam caught mid-payment and blocked."

**[Scroll to the before/after "gap" panel — the dead grey card vs the glowing live card.]**

> "Existing shields **detect and report** — after the money's gone. HyperGuard
> **intervenes, educates, and recovers** — while it's still happening."

---

## 3. The swarm — 30s

**[Scroll to the five-agent section.]**

> "Five agents, working as one. A **Digital Twin** that learns each customer's normal
> and scores every transfer. A **Voice Negotiator** that calls them the instant risk
> spikes. An **Educator** that recognises the scam script live and feeds back the
> right warning. A **Guardian** that loops in a trusted family member. And a
> **Recovery Coordinator** that builds the evidence pack if money ever gets through."

**[Scroll past the "Sixty seconds that change the outcome" timeline — let it animate.]**

> "Here's that whole sequence — call, transfer, risk spike, intervention, block —
> in the sixty seconds it actually takes. Now let me show you it live."

---

## 4. Live demo — 75s ⭐ (the part judges remember)

**[Pick up the phone. This is "Auntie May."]**

> "This is a customer's banking app. She's just been told by someone posing as the
> police that her account is compromised, and to move eight thousand dollars to a
> 'safe account' to protect it."

**[On phone: Transfer → enter $8,000 → the scam payee → Send.]**

> "She authorises it herself. No password stolen, nothing flagged by a normal bank
> check — it sails straight through. Watch what HyperGuard does."

**[Switch to Tab B (console live view). Narrate as the swarm fires in real time:]**

> "The Digital Twin scores it instantly — **new payee, four times her normal amount,
> off-hours.** Risk goes critical."

**[Risk meter swings red; transcript starts streaming.]**

> "It calls her. The Educator reads her replies, recognises the **police-impersonation
> script** — and pushes back the line no real agency would ever cross: *we never ask
> you to move money to a safe account.*"

**[Guardian alert appears.]**

> "It loops in her son as a second pair of eyes."

**[Verdict card lands: BLOCKED.]**

> "And it holds the transfer. The money never leaves the account — and there's a
> full, explainable audit trail for every decision the swarm made."

**[Glance back at the phone — the transfer shows blocked too.]**

> "She sees the same thing on her side. Protected, in real time, in the one moment
> that actually mattered."

---

## 5. The close — 15s

**[Back to Tab A, the headline.]**

> "Detection tells you *after*. HyperGuard intervenes *during* — and if it's ever too
> late, it helps recover *after*. We put an AI agent in the room at the exact moment
> someone's about to be robbed. That's HyperGuard."

**[Stop. Smile. Take questions.]**

---

## ⏱️ 60-second elevator cut

> "Most fraud losses today are payments victims send themselves — a scammer talks
> them into it, so nothing gets flagged. HyperGuard is a five-agent AI layer that
> catches the victim mid-payment: it scores the transfer, calls them, recognises the
> scam script live, warns them, loops in family, and blocks the money before it
> leaves — with a full audit trail. Detection tells you after; we intervene during.
> *[If demoing:]* Here — watch it stop an eight-thousand-dollar police-impersonation
> scam in real time."

---

## 🎤 Likely judge questions (and answers)

- **"Is the phone call real?"** — "The orchestration, risk scoring, scam
  classification, guardian alert and verdict are all live system output. For the demo
  the call audio is scripted; the production path wires Twilio + ElevenLabs — it's
  capability-gated, flip the keys on and it places a real call."
- **"How is this different from ScamShield / existing fraud tools?"** — "Those detect
  and report after the fact. We're the only layer that *intervenes during* the
  payment — voice negotiation, live scam education, family escalation, and recovery."
- **"Won't it annoy legitimate users?"** — "It only engages on genuine anomalies vs
  the customer's own baseline — low-risk transfers clear instantly on the fast path.
  You saw the feed: most activity never triggers an intervention."
- **"How does the risk model work?"** — "A behavioural Digital Twin per customer:
  z-scores on amount/time/velocity plus rules like new-payee and overseas, with an
  LLM explainer that turns the signals into human-readable reasons."
- **"What's the business model / who buys it?"** — "It's a drop-in layer banks and
  wallets add between intent and settlement — no rip-and-replace of their stack."

---

## 🧯 If the live demo breaks (fallbacks, in order)

1. **Console didn't update?** Refresh Tab B and re-send the transfer on the phone.
2. **Phone/Expo flaky?** Skip the phone — trigger the same scenario from the console's
   scenario launcher (`/console/live` → pick *police impersonation* → run). Same swarm,
   same verdict.
3. **Everything's down?** Narrate over the landing page's **live interceptions feed**
   and the **"Sixty seconds"** timeline — they tell the whole story on their own.
4. Keep a **screen recording** of one clean run on your desktop as the ultimate backup.

---

## 📋 One-line cue card (tape to your laptop)

`HOOK → 94% / 60s → live feed → before/after → 5 agents → PHONE: $8k scam → CONSOLE: score→call→educate→guardian→BLOCKED → "intervene during" → questions`
