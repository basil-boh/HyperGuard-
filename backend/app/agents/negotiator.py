"""Agent 2, The Voice Negotiator.

Owns the live call. On its first pass it places the outbound call and opens the
conversation; on every subsequent pass it asks the next question, folding in the
Educator's guidance once a scam pattern surfaces. The human's replies arrive over
real telephony in production, or from the deterministic victim simulator in a
hermetic demo. Either way the negotiator only appends turns to the transcript.
"""

from __future__ import annotations

from app.agents.base import Agent
from app.domain.events import EventType
from app.schemas import Speaker, TranscriptTurn
from app.state import SwarmState


class VoiceNegotiator(Agent):
    name = "voice_negotiator"

    async def __call__(self, state: SwarmState) -> dict:
        case_id = state["case_id"]
        customer = state["customer"]
        txn = state["transaction"]
        risk = state["risk"]
        classification = state.get("classification")
        transcript = list(state.get("transcript", []))
        turn = state.get("turn_count", 0)

        await self.emit(case_id, EventType.agent_engaged)
        new_turns: list[TranscriptTurn] = []
        cursor = len(transcript)

        if turn == 0:
            opening = await self.rt.negotiator.opening(customer, txn, risk)
            session = await self.rt.voice.initiate(customer.phone, opening)
            await self.emit(
                case_id,
                EventType.call_started,
                payload={"call_sid": session.sid, "live": session.live, "to": customer.phone},
            )
            cursor = await self._add(case_id, new_turns, cursor, Speaker.agent, opening)
        else:
            history = [f"{t.speaker.value}: {t.text}" for t in transcript]
            line = await self.rt.negotiator.respond(history, risk, classification)
            tags = ["guidance"] if classification and classification.archetype.value not in ("none", "unknown") else []
            cursor = await self._add(case_id, new_turns, cursor, Speaker.agent, line, tags)

        # The customer's reply for this round (script-driven in demo mode).
        script = txn.victim_script or self.rt.taxonomy.victim_script(txn.seeded_archetype)
        victim_line = self.rt.simulator.next_line(script, turn)
        if victim_line:
            cursor = await self._add(case_id, new_turns, cursor, Speaker.customer, victim_line)

        await self.emit(case_id, EventType.agent_completed)
        return {"transcript": new_turns, "turn_count": turn + 1}

    async def _add(
        self,
        case_id: str,
        sink: list[TranscriptTurn],
        index: int,
        speaker: Speaker,
        text: str,
        tags: list[str] | None = None,
    ) -> int:
        turn = TranscriptTurn(
            index=index, speaker=speaker, text=text, ts=self.now(), tags=tags or []
        )
        sink.append(turn)
        await self.emit(
            case_id, EventType.transcript_turn, payload={"turn": turn.model_dump(mode="json")}
        )
        return index + 1
