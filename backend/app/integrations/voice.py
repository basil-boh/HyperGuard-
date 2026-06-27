"""Telephony + speech adapter (Twilio + ElevenLabs).

`is_live` is true only when Twilio credentials are present. In that mode
`initiate` places a genuine outbound call that speaks the intervention's opening
line; in demo mode it returns a synthetic handle so the negotiator's dialogue loop
runs identically against a simulated victim. Bidirectional media-stream transcription
is the documented production seam, the swarm logic above it is transport-agnostic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import uuid4

from app.config import Settings

logger = logging.getLogger("hyperguard.voice")


@dataclass
class CallSession:
    sid: str
    to_number: str
    live: bool


class VoiceGateway:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._twilio = None

    @property
    def is_live(self) -> bool:
        return self._settings.telephony_enabled

    def _client(self):
        if not self.is_live:
            return None
        if self._twilio is None:
            try:
                from twilio.rest import Client

                self._twilio = Client(
                    self._settings.twilio_account_sid, self._settings.twilio_auth_token
                )
            except Exception as exc:  # pragma: no cover - dep optional
                logger.warning("Twilio client unavailable: %s", exc)
                return None
        return self._twilio

    async def initiate(self, to_number: str, opening_line: str) -> CallSession:
        client = self._client()
        if client is None:
            logger.info("[demo-voice] would call %s: %r", to_number, opening_line)
            return CallSession(sid=f"demo-{uuid4().hex[:12]}", to_number=to_number, live=False)
        try:
            from twilio.twiml.voice_response import VoiceResponse

            twiml = VoiceResponse()
            twiml.say(opening_line, voice="Polly.Joanna")
            twiml.pause(length=1)
            call = client.calls.create(
                to=to_number,
                from_=self._settings.twilio_phone_number,
                twiml=str(twiml),
            )
            return CallSession(sid=call.sid, to_number=to_number, live=True)
        except Exception as exc:  # pragma: no cover - network
            logger.warning("Outbound call failed, degrading to demo: %s", exc)
            return CallSession(sid=f"demo-{uuid4().hex[:12]}", to_number=to_number, live=False)

    async def synthesize(self, text: str) -> bytes | None:
        """Render a line with ElevenLabs; returns audio bytes or None when unavailable."""
        if not self._settings.speech_enabled:
            return None
        try:
            import httpx

            url = (
                "https://api.elevenlabs.io/v1/text-to-speech/"
                f"{self._settings.elevenlabs_voice_id}"
            )
            async with httpx.AsyncClient(timeout=20) as http:
                resp = await http.post(
                    url,
                    headers={"xi-api-key": self._settings.elevenlabs_api_key or ""},
                    json={"text": text, "model_id": "eleven_turbo_v2"},
                )
                resp.raise_for_status()
                return resp.content
        except Exception as exc:  # pragma: no cover - network
            logger.warning("Speech synthesis failed: %s", exc)
            return None
