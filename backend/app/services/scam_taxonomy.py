"""The Educator's knowledge base.

Each archetype carries the linguistic fingerprints we listen for, the guidance the
negotiator reads back into the call, and, for hermetic demos, a victim script
the simulator follows when there is no live human on the line. Classification is a
transparent indicator-density match; an LLM, when present, only *refines* the
guidance wording, never the safety logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas import ScamArchetype, ScamClassification


@dataclass(frozen=True)
class Archetype:
    key: ScamArchetype
    title: str
    indicators: tuple[str, ...]
    guidance: str
    victim_script: tuple[str, ...] = field(default_factory=tuple)


_LIBRARY: tuple[Archetype, ...] = (
    Archetype(
        key=ScamArchetype.government_impersonation,
        title="Government / Police Impersonation",
        indicators=(
            "police",
            "officer",
            "arrest",
            "warrant",
            "money laundering",
            "safe account",
            "investigation",
            "court",
            "cpib",
            "mas",
            "case number",
            "customs",
            "interpol",
        ),
        guidance=(
            "No police force, court, or government agency will ever phone you to demand "
            "a transfer to a 'safe account'. That phrase is the scam. Real investigations "
            "are never resolved by moving your savings. Hang up and call the agency back "
            "on its official published number, not the one that called you."
        ),
        victim_script=(
            "An officer from the police anti-fraud unit called me.",
            "He said my bank account is linked to a money-laundering case.",
            "He told me to move my money to a government safe account for protection.",
            "He said if I don't do it now there's a warrant for my arrest.",
            "He told me not to tell anyone, not even the bank, or I'll be charged too.",
        ),
    ),
    Archetype(
        key=ScamArchetype.bank_impersonation,
        title="Bank / Institution Impersonation",
        indicators=(
            "bank",
            "fraud department",
            "verify your account",
            "suspended",
            "one-time password",
            "otp",
            "security team",
            "compromised",
            "reverse the transaction",
            "card blocked",
        ),
        guidance=(
            "Your bank already knows your account number, it will never ask you to "
            "'verify' it, read out an OTP, or move money to keep it safe. Anyone who does "
            "is impersonating us. Do not share the code. We will freeze the transfer from "
            "our side while you confirm directly through the app you installed yourself."
        ),
        victim_script=(
            "Someone from the bank's fraud department called me.",
            "They said my account was compromised and someone is draining it.",
            "They asked me to confirm a one-time password they sent.",
            "They told me to move everything to a new secure account they set up.",
        ),
    ),
    Archetype(
        key=ScamArchetype.investment,
        title="Investment / Crypto Scam",
        indicators=(
            "investment",
            "crypto",
            "bitcoin",
            "guaranteed",
            "returns",
            "trading platform",
            "broker",
            "profit",
            "double your",
            "opportunity",
            "withdraw my earnings",
        ),
        guidance=(
            "Guaranteed high returns do not exist, that promise is the defining mark of "
            "an investment scam. Platforms that block your withdrawal until you 'top up' "
            "or 'pay tax' are stealing from you. Stop here before sending more, and check "
            "the firm against the official regulator's register."
        ),
        victim_script=(
            "I joined an online trading group that promised guaranteed returns.",
            "My portfolio shows huge profits on their platform.",
            "To withdraw my earnings they say I must pay a release fee first.",
            "The broker is rushing me to send it before the offer closes.",
        ),
    ),
    Archetype(
        key=ScamArchetype.romance,
        title="Romance / Relationship Scam",
        indicators=(
            "boyfriend",
            "girlfriend",
            "partner online",
            "never met",
            "emergency",
            "stranded",
            "hospital",
            "soldier",
            "send money for a flight",
            "love",
        ),
        guidance=(
            "Someone you have only met online, who now urgently needs money for an "
            "emergency, a flight, or customs fees, is following a scam script. Genuine "
            "partners do not ask. Please pause and talk to someone you trust before "
            "sending anything to a person you have never met in real life."
        ),
        victim_script=(
            "I'm helping my partner, we met online a few months ago.",
            "We haven't met in person yet but we talk every day.",
            "He's stuck overseas and needs money for an emergency.",
            "He promised to pay me back as soon as he flies over.",
        ),
    ),
    Archetype(
        key=ScamArchetype.job,
        title="Job / Task Scam",
        indicators=(
            "job offer",
            "work from home",
            "commission",
            "complete tasks",
            "prepay",
            "deposit to start",
            "recruiter",
            "easy money",
            "telegram task",
        ),
        guidance=(
            "A real employer pays you, it never asks you to deposit your own money to "
            "'unlock tasks' or earn commission. That up-front payment is the scam, and the "
            "early small payouts exist only to make the big deposit feel safe. Do not send it."
        ),
        victim_script=(
            "I got a part-time job doing simple online tasks for commission.",
            "The first few payouts came through fine.",
            "Now they say I need to deposit my own money to unlock the next batch.",
            "They promise I'll get it all back plus a bonus.",
        ),
    ),
    Archetype(
        key=ScamArchetype.tech_support,
        title="Tech Support Scam",
        indicators=(
            "virus",
            "microsoft",
            "remote access",
            "anydesk",
            "teamviewer",
            "refund too much",
            "computer infected",
            "support team",
            "install",
        ),
        guidance=(
            "Microsoft, Apple, and your antivirus will never call you about a virus or ask "
            "for remote access to your device. Once they are in, they watch you log in and "
            "move the money themselves. Disconnect now and do not install anything they sent."
        ),
        victim_script=(
            "A support technician called saying my computer is infected.",
            "He had me install a program so he could fix it remotely.",
            "He said a refund was sent by mistake and I must return the difference.",
        ),
    ),
)

_BY_KEY = {a.key: a for a in _LIBRARY}


class ScamTaxonomy:
    """Indicator-density classifier over the conversation so far."""

    SAFE_GUIDANCE = (
        "Thanks for confirming. Everything you've described lines up with a normal, "
        "expected transfer, so we'll let it through right away."
    )

    def get(self, key: ScamArchetype) -> Archetype | None:
        return _BY_KEY.get(key)

    # What a genuine customer says when there's no scam, used for legitimate
    # transfers to new payees, so the swarm verifies and releases them.
    LEGIT_SCRIPT: tuple[str, ...] = (
        "Oh, hello, yes, I'm making this payment myself.",
        "It's for someone I know; nobody pressured me into it.",
        "I just set it up because I needed to pay them. Everything's fine.",
    )

    def victim_script(self, key: ScamArchetype | None) -> tuple[str, ...]:
        if key and key in _BY_KEY:
            return _BY_KEY[key].victim_script
        return self.LEGIT_SCRIPT

    def classify(self, conversation: str) -> ScamClassification:
        text = conversation.lower()
        best: Archetype | None = None
        best_hits: list[str] = []

        for arch in _LIBRARY:
            hits = [ind for ind in arch.indicators if ind in text]
            if len(hits) > len(best_hits):
                best, best_hits = arch, hits

        if not best or not best_hits:
            return ScamClassification(
                archetype=ScamArchetype.none,
                title="No scam pattern detected",
                confidence=0.0,
                indicators=[],
                guidance=self.SAFE_GUIDANCE,
            )

        # Confidence scales with how many distinct fingerprints lit up, saturating fast.
        confidence = round(min(0.4 + 0.18 * len(best_hits), 0.98), 2)
        return ScamClassification(
            archetype=best.key,
            title=best.title,
            confidence=confidence,
            indicators=best_hits,
            guidance=best.guidance,
        )
