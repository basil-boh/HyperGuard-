"""Twilio interactive voice webhooks.

Twilio fetches `/twilio/voice/start` when our outbound intervention call connects, then
posts each spoken answer to `/twilio/voice/answer`. We ask a short series of context
questions, capture the speech, stream each turn onto the swarm bus (so the app + console
show the live conversation), and kick off the LLM follow-up when the call ends.

No auth: these are Twilio-to-us webhooks. The endpoints return TwiML (XML).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response

from app.domain.events import EventType, SwarmEvent
from app.integrations.event_bus import get_event_bus
from app.wallet.registry import get_registry

logger = logging.getLogger("hyperguard.twilio")
router = APIRouter(prefix="/twilio")

GREETING = (
    "Hello, this is HyperGuard calling from your bank's protection team. "
    "We've paused a large transfer to make sure you're safe. "
    "I just have a few quick questions."
)
CONTEXT_QUESTIONS = [
    "Who are you sending this money to, and do you know them personally?",
    "What is this payment for?",
    "Did someone contact you and ask you to make this transfer? If so, who were they, "
    "and how did they reach you?",
]
CLOSING = (
    "Thank you. For your safety we've held this transfer while we review it, and we're "
    "letting your trusted contact know. Goodbye."
)


def _twiml(xml: str) -> Response:
    return Response(content=xml, media_type="application/xml")


def _gather(case_id: str, step: int, prompt: str) -> str:
    from twilio.twiml.voice_response import Gather, VoiceResponse

    vr = VoiceResponse()
    gather = Gather(
        input="speech",
        action=f"/twilio/voice/answer?case_id={case_id}&step={step}",
        method="POST",
        speech_timeout="auto",
        language="en-SG",
        action_on_empty_result=True,
    )
    gather.say(prompt, voice="Polly.Joanna")
    vr.append(gather)
    # Fallback if the gather itself is skipped.
    vr.redirect(f"/twilio/voice/answer?case_id={case_id}&step={step}", method="POST")
    return str(vr)


async def _publish_turn(case_id: str, index: int, speaker: str, text: str) -> None:
    turn = {
        "index": index,
        "speaker": speaker,
        "text": text,
        "ts": datetime.now(timezone.utc).isoformat(),
        "tags": [],
    }
    await get_event_bus().publish(
        SwarmEvent(
            type=EventType.transcript_turn, case_id=case_id, agent="voice_negotiator",
            payload={"turn": turn},
        )
    )


@router.api_route("/voice/start", methods=["GET", "POST"])
async def voice_start(request: Request) -> Response:
    case_id = request.query_params.get("case_id", "")
    await _publish_turn(case_id, 0, "agent", f"{GREETING} {CONTEXT_QUESTIONS[0]}")
    return _twiml(_gather(case_id, 0, f"{GREETING} {CONTEXT_QUESTIONS[0]}"))


@router.api_route("/voice/answer", methods=["GET", "POST"])
async def voice_answer(request: Request) -> Response:
    case_id = request.query_params.get("case_id", "")
    step = int(request.query_params.get("step", "0"))
    form = await request.form()
    answer = (form.get("SpeechResult") or "").strip() or "(no response)"

    question = CONTEXT_QUESTIONS[step] if step < len(CONTEXT_QUESTIONS) else "(question)"
    get_registry().add_answer(case_id, question, answer)
    await _publish_turn(case_id, step * 2 + 1, "customer", answer)

    next_step = step + 1
    if next_step < len(CONTEXT_QUESTIONS):
        await _publish_turn(case_id, next_step * 2, "agent", CONTEXT_QUESTIONS[next_step])
        return _twiml(_gather(case_id, next_step, CONTEXT_QUESTIONS[next_step]))

    # Interview complete: close the call and run the LLM follow-up out-of-band.
    from twilio.twiml.voice_response import VoiceResponse

    vr = VoiceResponse()
    vr.say(CLOSING, voice="Polly.Joanna")
    vr.hangup()

    from app.wallet.followup import finalize_followup

    asyncio.create_task(finalize_followup(case_id))
    logger.info("Voice interview complete for %s; running follow-up", case_id)
    return _twiml(str(vr))
