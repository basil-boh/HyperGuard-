"""Guardian-channel delivery (SMS / voice) to trusted contacts.

Real delivery rides Twilio when configured; otherwise messages resolve as
`delivered` in demo mode so the escalation path is fully observable on stage.
"""

from __future__ import annotations

import logging

from app.config import Settings
from app.schemas import GuardianAlert, TrustedContact

logger = logging.getLogger("hyperguard.notify")


class NotificationGateway:
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

    async def send_sms(self, contact: TrustedContact, message: str) -> GuardianAlert:
        client = self._client()
        if client is None:
            logger.info("[demo-sms] -> %s (%s): %s", contact.name, contact.phone, message)
            return GuardianAlert(
                contact=contact, channel="sms", status="delivered", message=message
            )
        try:
            client.messages.create(
                to=contact.phone, from_=self._settings.twilio_phone_number, body=message
            )
            return GuardianAlert(
                contact=contact, channel="sms", status="delivered", message=message
            )
        except Exception as exc:  # pragma: no cover - network
            logger.warning("SMS to %s failed: %s", contact.phone, exc)
            return GuardianAlert(
                contact=contact, channel="sms", status="failed", message=message
            )
