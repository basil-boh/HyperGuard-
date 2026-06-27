# HyperGuard — Explainer Video Pipeline

A self-contained, **GSAP-driven, deterministic HTML→MP4** pipeline that renders the
HyperGuard explainer. Mirrors the technique of
[heygen-com/hyperframes](https://github.com/heygen-com/hyperframes): a single
**seekable GSAP master timeline** captured frame-by-frame in headless Chromium and
encoded with FFmpeg, with an **ElevenLabs** voiceover.

> All motion is GSAP — there are no CSS animations/transitions. CSS is layout/styling only.

## Output
`out/HyperGuard.mp4` — 1920×1080, 30 fps, ~116 s, H.264 + AAC, `+faststart`.

## Pipeline

| Step | File | What it does |
|------|------|--------------|
| 1. Script | `script.mjs` | 8-scene narration + captions (shared by TTS & renderer so they never drift). |
| 2. Voiceover | `narrate.mjs` | ElevenLabs TTS per scene → `audio/*.mp3` + `audio/durations.json`. |
| 3. Composition | `composition.html` | Seekable GSAP timeline, custom SVG vectors, HUD, particle field, captions. Exposes `window.__seek(t)` / `window.__duration` / `window.__ready`. |
| 4. Render | `render.mjs` | Playwright seeks the timeline frame-by-frame → PNGs; builds the audio track (voice + subtle ambient bed); FFmpeg encodes the MP4. |
| (debug) | `shoot.mjs` | Screenshot arbitrary timestamps: `node shoot.mjs 74 91 106`. |

Scene **durations are derived from the voiceover** (`durations.json`), so visuals and
narration stay locked together. The renderer injects the timing into the page via
`window.__TIMELINE__` before load — `composition.html` is never regenerated.

## Regenerate

```bash
cd video
node narrate.mjs        # re-synthesize voiceover (needs ../.env ELEVENLABS_API_KEY)
node render.mjs --probe # quick: render ~13 sample frames into frames/
node render.mjs         # full render → out/HyperGuard.mp4
```

## Scenes
1. **Cold open** — Auntie May, 2 AM, $8,000 to a "safe account".
2. **The problem** — detection is *after*; the 60-second human moment.
3. **The solution** — HyperGuard, the intervention swarm (shield + heartbeat logomark).
4. **Differentiation** — ScamShield (detect+report) vs HyperGuard (owns the loop).
5. **The swarm** — 5 agents around a LangGraph core.
6. **Architecture** — LangGraph state machine, live risk 0.93 → BLOCK.
7. **Tech stack** — Next.js · FastAPI · LangGraph · Twilio · ElevenLabs · Supabase · Redis.
8. **Close** — "Detection tells you after. HyperGuard intervenes during."

## Notes
- Voice: ElevenLabs **Sarah** (`EXAVITQu4vr4xnSDxMaL`), premade (free-tier OK).
- Determinism: no `Math.random` per frame — particle field is a pure function of time,
  seeded once at load; the same input always yields the same video.
- `node_modules/` here is a local Playwright install (browser binary is in the shared
  `~/Library/Caches/ms-playwright` cache).
