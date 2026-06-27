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

## What to try

| Action | What happens |
| ------ | ------------ |
| Transfer **$80 to NTUC FairPrice** | In-pattern → approved instantly, balance drops |
| Transfer **$8,000 to "Quick Holdings Pte Ltd"** | Digital Twin spikes → HyperGuard "calls" you → Educator detects **police impersonation** → Guardian alerts your next of kin → **blocked**, money kept |
| Transfer **$15,000 to "CryptoGain Capital"** | Caught as an **investment scam** → blocked |
| Add a **new payee** + transfer a large amount | Higher risk (new payee) → HyperGuard verifies on the call → approved once you confirm it's genuine |
| Add / remove **guardians** (next of kin) | Changes who gets alerted during an intervention |

The recipients look ordinary in the app, the scam ones carry a hidden risk profile
on the backend, so the agents reveal the danger the customer can't see.

## Structure

```
mobile/
├── app/                      # Expo Router screens
│   ├── (tabs)/               # Wallet · Activity · Guardians
│   ├── transfer.tsx          # transfer flow → triggers the swarm
│   ├── intervention/[caseId].tsx   # live agents-at-work view (polls backend)
│   ├── add-recipient.tsx · add-contact.tsx
├── components/               # AgentRelay · RiskGauge · Transcript · TxnRow · ui
└── lib/                      # api · config (auto host) · useIntervention (poll+reduce) · theme
```
