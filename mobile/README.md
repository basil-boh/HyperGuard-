# HyperGuard Wallet (mobile)

A simulated banking app, fake money, transaction history, transfers, payees, and
next-of-kin, built so the HyperGuard swarm has real data to act on. Every transfer
runs through the backend's fraud-intervention agents; transfers to a (hidden) scam
payee are caught and blocked live, in front of you.

Built with **Expo + Expo Router** (React Native, TypeScript). No API keys needed to
run the simulation, add Twilio/ElevenLabs/OpenAI keys to the backend later and the
same flow places real calls.

## Run

1. **Start the backend on your LAN** (so a phone can reach it):

   ```bash
   cd ../backend && source .venv/bin/activate
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. **Start the app:**

   ```bash
   npm install
   npx expo start
   ```

   Open it in **Expo Go** (scan the QR) or an iOS/Android simulator (`i` / `a`).

The app auto-discovers the backend at `http://<your-dev-machine-ip>:8000` by reading
the Expo dev-server host, so on a physical phone in Expo Go it just works. To point
somewhere else, set `extra.apiBase` in `app.json` or edit `lib/config.ts`.

## Signing in

The app opens on a sign-in screen: **phone number + 6-digit PIN**. Tap **Demo accounts**
at the bottom to sign straight in as any seeded customer — the list is served by the
backend (`GET /api/auth/demo-accounts`), so it always matches what's actually in the
database.

| Phone | PIN | Customer | Why you'd pick them |
| --- | --- | --- | --- |
| `+6580001234` | `112233` | Alex Tan, 67 | The default demo account, two hidden scam payees |
| `+6580000001` | `445566` | May Tan, 72 | Already has two blocked scams on file |
| `+6580000002` | `778899` | Daniel Lim, 34 | High volume — big transfers look normal here |
| `+6580000003` | `102030` | Wong Ah Kow, 81 | Tiny baseline — anything four-figure is critical |
| `+6580000004` | `135791` | Priya Nair, 58 | Tech-support scam on file |
| `+6580000005` | `246810` | Siti Rahman, 29 | Gig worker: frequent small payouts |
| `+6580000006` | `909090` | Robert Chen, 46 | SME owner: five-figure transfers are routine |
| `+6580000010` | `321321` | Marcus Tan, 41 | **Guardian** to Alex + May — incident inbox already populated |
| `+6580000013` | `654654` | Linda Wong, 52 | **Guardian** to Wong Ah Kow — one unread incident |

Each account has its own balance, payees, guardians and transaction history. The
person icon on the wallet header opens **Your account**, where you can change your PIN,
switch accounts, or sign out. Tap **Create a new account** on sign-in to register a
fresh customer with its own PIN — it starts with a thin file, so the risk engine treats
it with cold-start caution.

## What to try

The same transfer lands very differently depending on who you signed in as — sign in as
**Wong** and send 3,000, then as **Robert** and send 6,800, to see learned baselines at work.

| Action | What happens |
| ------ | ------------ |
| Transfer **$80 to NTUC FairPrice** | In-pattern → approved instantly, balance drops |
| Transfer **$8,000 to "Quick Holdings Pte Ltd"** | Digital Twin spikes → HyperGuard "calls" you → Educator detects **police impersonation** → Guardian alerts your next of kin → **blocked**, money kept |
| Transfer **$15,000 to "CryptoGain Capital"** | Caught as an **investment scam** → blocked |
| Add a **new payee** + transfer a large amount | Higher risk (new payee) → HyperGuard verifies on the call → approved once you confirm it's genuine |
| Add / remove **guardians** (next of kin) | Changes who gets alerted during an intervention |

The recipients look ordinary in the app, the scam ones carry a hidden risk profile
on the backend, so the agents reveal the danger the customer can't see.

## The guardian side

Sign in as **Marcus Tan** (`+6580000010` / `321321`) and open the **Network** tab: he
protects Alex and May, with two of May's incidents already in his inbox. Tap May →
an incident → you get the whole account of what happened, and the **Alert authorities**
action.

> **The authorities filing is a simulation.** HyperGuard is a prototype with no
> connection to the police, the National Anti-Scam Centre, or anyone else. Every
> reference is prefixed `SIM-`, every response is flagged `simulated: true`, and the
> real reporting channel (ScamShield, **1799**) is shown alongside. Nothing is sent.

The two-device demo, in full:

| Step | On the guardian's phone (Marcus) | On the relative's phone (Wong) |
| --- | --- | --- |
| 1 | Network → **Add someone to protect** → `+6580000003`, "nephew" | — |
| 2 | "Waiting for Wong Ah Kow to accept" | Network → **Invitation** → Accept |
| 3 | Wong appears under *I'm protecting*, his history backfilled | Marcus is now on his guardian list |
| 4 | — | Transfer **$3,000 to "Daniel Ashworth"** → romance scam → blocked |
| 5 | The incident lands in Marcus's inbox, unread | The intervention screen offers **Send incident report** |
| 6 | Open it → **Alert authorities** → `SIM-NASC-…` reference + timeline | — |

A pending invitation from Marcus to Wong is already seeded, so steps 1–2 can be
skipped if you only have one device.

### Transfer limits

From **Network → (someone you protect) → Transfer limit**, a guardian can cap what
that person sends in a single transfer. Sign in as Marcus, cap May at SGD 500, then
sign in as May and try to send 2,500 — it's refused before the swarm even runs, with
a message naming who set the limit.

Only the guardian can change it, on purpose: a limit the victim can raise mid-call is
a limit a scammer can talk them through raising. May sees the cap on her balance card
and next to Marcus's name in her Network tab, and can remove him as a guardian if she
disagrees. Where several guardians set one, the lowest wins.

## Structure

```
mobile/
├── app/                      # Expo Router screens
│   ├── login.tsx             # phone + PIN sign-in, with the demo-account picker
│   ├── register.tsx          # create an account (name, phone, PIN)
│   ├── account.tsx           # signed-in profile · change PIN · switch account · sign out
│   ├── (tabs)/               # Wallet · Activity · Guardians
│   ├── transfer.tsx          # transfer flow → triggers the swarm
│   ├── intervention/[caseId].tsx   # live agents-at-work view (polls backend)
│   ├── add-recipient.tsx · add-contact.tsx
├── components/               # AgentRelay · RiskGauge · Transcript · TxnRow · ui
└── lib/                      # api · session (token store) · config (auto host) · useIntervention · theme
```
