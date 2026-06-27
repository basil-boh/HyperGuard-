// Shared script + scene metadata. Imported by narrate.mjs (TTS) and render.mjs
// (timeline/captions) so the spoken words and on-screen captions never drift.
//
// Each scene:
//   id        – stable key, also the <section data-scene> id in composition.html
//   narration – exact words spoken by ElevenLabs (drives scene DURATION)
//   captions  – subtitle chunks, shown sequentially across the scene's audio
//   tail      – seconds of breathing room appended after the voice ends

export const SCENES = [
  {
    id: 'hook',
    narration:
      "It's two a.m. Auntie May is about to wire eight thousand dollars to a scammer — and she believes she's doing the right thing.",
    captions: [
      '2:00 AM.',
      'Auntie May is about to wire $8,000 to a scammer.',
      'She thinks she’s doing the right thing.',
    ],
    tail: 0.9,
  },
  {
    id: 'problem',
    narration:
      "Fraud systems today flag suspicious transactions — but only after the money is gone. The victim sends it willingly, by their own hand. The real gap is the human moment: the sixty seconds between, I'll send it, and, money sent.",
    captions: [
      'Detection flags fraud — AFTER the money is gone.',
      'The victim sends it willingly, by their own hand.',
      'The gap is the human moment.',
      'The 60 seconds between “I’ll send it” and “money sent.”',
    ],
    tail: 0.8,
  },
  {
    id: 'solution',
    narration:
      "HyperGuard is an autonomous AI agent swarm that steps into that moment. It catches the victim mid-scam, calls them, talks them out of it, loops in their family — and if it's too late, builds the evidence to get their money back.",
    captions: [
      'HyperGuard — an autonomous fraud-intervention swarm.',
      'It catches the victim mid-scam.',
      'Calls them. Talks them out of it. Loops in family.',
      'And if it’s too late — builds the evidence to recover.',
    ],
    tail: 0.8,
  },
  {
    id: 'different',
    narration:
      "Existing shields, like ScamShield, stop at detection and reporting. They don't intervene in real time. They don't loop in family. They don't orchestrate recovery. HyperGuard owns the entire loop. That's why it isn't just better — it's necessary.",
    captions: [
      'Existing shields stop at DETECT + REPORT.',
      'No real-time intervention. No family layer. No recovery.',
      'HyperGuard owns the entire loop.',
      'Not just better — necessary.',
    ],
    tail: 0.8,
  },
  {
    id: 'swarm',
    narration:
      'Five specialized agents act as one. The Digital Twin scores every transaction against your behavioral baseline. The Voice Negotiator calls you live. The Educator names the exact scam playbook and feeds warnings into the call. The Guardian alerts someone you trust. And the Recovery Coordinator builds the evidence package.',
    captions: [
      'Five specialized agents act as one.',
      'Digital Twin — scores risk vs. your baseline.',
      'Voice Negotiator — calls you live.',
      'Educator — names the scam, warns in real time.',
      'Guardian — alerts someone you trust.',
      'Recovery Coordinator — builds the evidence package.',
    ],
    tail: 0.8,
  },
  {
    id: 'architecture',
    narration:
      'Under the hood, it is a LangGraph state machine. Low risk is approved instantly. High risk triggers a live call. Conditional edges route on risk score, verification, and scam type — until one explainable decision: approve, or block.',
    captions: [
      'Under the hood: a LangGraph state machine.',
      'Low risk → approved instantly.',
      'High risk → live intervention.',
      'Edges route on risk, verification & scam type.',
      'One explainable decision: APPROVE or BLOCK.',
    ],
    tail: 0.8,
  },
  {
    id: 'stack',
    narration:
      'It runs on a real-time stack — a Next.js mission-control console, a FastAPI and LangGraph backend, Twilio and ElevenLabs for live voice, and Supabase with Redis Streams wiring the swarm together.',
    captions: [
      'Built on a real-time stack.',
      'Next.js console · FastAPI · LangGraph',
      'GPT-class reasoning · Twilio · ElevenLabs voice',
      'Supabase + pgvector · Redis Streams',
    ],
    tail: 0.8,
  },
  {
    id: 'close',
    narration:
      'Detection tells you after. HyperGuard intervenes during — and helps recover after. An AI agent in the room, when it matters most.',
    captions: [
      'Detection tells you AFTER.',
      'HyperGuard intervenes DURING — and recovers AFTER.',
      'An AI agent in the room, when it matters most.',
    ],
    tail: 1.4,
  },
];

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;
export const VOICE_ID = 'hpp4J3VqNfWAUOO0d1Us'; // ElevenLabs "Bella" — professional, bright, warm female (premade, free-tier OK)
