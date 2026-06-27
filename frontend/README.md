# HyperGuard Console (frontend)

The operator console for the HyperGuard swarm, a bespoke Next.js app with a
hand-built design system ("interdiction console"), a 3D React-Three-Fiber hero,
and GSAP scroll choreography on the landing page.

## Develop

```bash
npm install
npm run dev          # http://localhost:3000
```

`/api/*` is proxied to the backend (`http://localhost:8000` by default, override
with `API_PROXY_TARGET`). The live event WebSocket connects to
`ws://<host>:8000/ws/events` (override with `NEXT_PUBLIC_WS_URL`). See
`.env.local.example`.

Start the backend first (`cd ../backend && uvicorn app.main:app --reload`), then
open `/console` and hit **Initiate intervention**, no API keys required.

## Routes

| Route       | What it is                                                       |
| ----------- | --------------------------------------------------------------- |
| `/`         | Brand landing, 3D shield hero (R3F + bloom), GSAP reveals       |
| `/console`  | Mission Control, live risk meter, agent relay, transcript, verdict |
| `/recovery` | Investigator evidence dossier (print-ready)                     |

## Design system

Tokens live in `app/globals.css` (CSS variables) and `tailwind.config.ts`. The
visual language is deliberately distinct per surface, a 3D landing, a HUD
console, and a document-style dossier, rather than one repeated card component.
