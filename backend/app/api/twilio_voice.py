"""Twilio interactive voice webhooks.

Twilio fetches `/twilio/voice/start` when our outbound intervention call connects, then
posts each spoken answer to `/twilio/voice/answer`. We ask a short series of context
questions, capture the speech, stream each turn onto the swarm bus (so the app + console
show the live conversation), and kick off the LLM follow-up when the call ends.

These are Twilio-to-us webhooks returning TwiML (XML), authenticated by verifying
the `X-Twilio-Signature` header against our auth token — anyone else posting fake
call events gets a 403. Without a Twilio token configured (local simulation) the
check is skipped in development and the routes are disabled in production.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.config import Settings, get_settings
from app.domain.events import EventType, SwarmEvent
from app.integrations.event_bus import get_event_bus
from app.wallet.registry import get_registry

logger = logging.getLogger("hyperguard.twilio")


def _webhook_url(request: Request, settings: Settings) -> str:
    """The URL Twilio signed. Behind Railway's proxy `request.url` is the internal
    http:// address, so prefer the configured public base (which is also what the
    outbound call's webhook and the relative Gather actions resolve against)."""
    if settings.public_base_url:
        base = settings.public_base_url.rstrip("/")
        query = request.url.query
        return f"{base}{request.url.path}" + (f"?{query}" if query else "")
    return str(request.url)


async def verify_twilio_signature(
    request: Request, settings: Settings = Depends(get_settings)
) -> None:
    if not settings.twilio_validation_enabled:
        if settings.is_production:
            raise HTTPException(status_code=503, detail="telephony webhooks disabled")
        return  # local simulation, nothing to validate against
    from twilio.request_validator import RequestValidator

    params: dict[str, str] = {}
    if request.method == "POST":
        form = await request.form()  # cached; the route handler re-reads it freely
        params = {key: value for key, value in form.items() if isinstance(value, str)}
    valid = RequestValidator(settings.twilio_auth_token).validate(
        _webhook_url(request, settings),
        params,
        request.headers.get("X-Twilio-Signature", ""),
    )
    if not valid:
        logger.warning("Rejected webhook with bad Twilio signature: %s", request.url.path)
        raise HTTPException(status_code=403, detail="invalid Twilio signature")


router = APIRouter(prefix="/twilio", dependencies=[Depends(verify_twilio_signature)])

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
