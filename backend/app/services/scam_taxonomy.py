"""The Educator's knowledge base.

Each archetype carries the linguistic fingerprints we listen for, the guidance the
negotiator reads back into the call, and, for hermetic demos, a victim script
the simulator follows when there is no live human on the line. Classification is a
transparent indicator-density match; an LLM, when present, only *refines* the
guidance wording, never the safety logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.schemas import ScamArchetype, ScamClassification


@dataclass(frozen=True)
class Archetype:
    key: ScamArchetype
    title: str
    indicators: tuple[str, ...]
    guidance: str  # the one line the negotiator reads back during the call
    how_it_works: str = ""  # the post-call debrief: how this scam actually operates
    prevention: tuple[str, ...] = ()  # how the customer avoids it in future
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
        how_it_works=(
            "Scammers pose as the police, CPIB, MAS, or customs and invent a criminal case "
            "in your name, money laundering, a warrant, drugs found in a parcel. The fear "
            "and urgency are deliberate: they stop you thinking clearly, then offer the only "
            "'way out', moving your savings to a so-called safe or government account 'for "
            "verification'. That account belongs to them. The demand for secrecy exists only "
            "to keep anyone from talking you out of it."
        ),
        prevention=(
            "No real agency will ever ask you to transfer money to a 'safe account'.",
            "Hang up and call the agency back on its official published number.",
            "A genuine officer will never forbid you from telling your bank or family.",
            "Fear + secrecy + a deadline is the signature of this scam.",
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
        how_it_works=(
            "The caller claims to be your bank's fraud team and says your account is "
            "compromised and being drained right now. The panic is the point. They get you "
            "to read out a one-time password or move everything to a 'new secure account' "
            "they have set up, which hands them either the code that authorises a transfer "
            "or direct control of your money."
        ),
        prevention=(
            "Your bank already has your details, it will never ask you to verify them.",
            "An OTP is a password; reading it aloud authorises the very transfer you fear.",
            "Never move money to 'keep it safe', that instruction only comes from a scammer.",
            "Hang up and reach the bank through its app or the number on your card.",
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
        how_it_works=(
            "You are shown a slick platform with profits climbing, and maybe a small "
            "withdrawal that really pays out, just enough to earn your trust. When you try "
            "to take the big money out, suddenly there is a 'release fee', 'tax', or "
            "'top-up' to unlock it. Each fee is real money handed to them; the balance on "
            "the screen is just a number they control."
        ),
        prevention=(
            "Guaranteed or unusually high returns do not exist, that promise is the scam.",
            "Never pay a fee to withdraw your own money, that is how the trap closes.",
            "Check the firm against the official regulator's register before sending.",
            "'Act before the offer closes' is manufactured urgency, ignore it.",
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
        how_it_works=(
            "Over weeks or months, someone you met online builds a relationship that feels "
            "real, then an emergency strikes: stranded abroad, a hospital bill, customs fees "
            "on a gift they 'sent' you. Because the bond feels genuine, the request feels "
            "reasonable. But they never manage to meet you in person, and the emergencies "
            "never stop coming."
        ),
        prevention=(
            "Someone you have never met in person asking for money is following a script.",
            "Genuine partners do not need your savings for emergencies, flights, or customs.",
            "Be wary of anyone who always has a reason they cannot meet or video-call.",
            "Talk to a friend or family member first, these scams rely on isolating you.",
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
        how_it_works=(
            "You are offered easy work-from-home tasks for commission. The first small "
            "payouts arrive, which feels like proof it is real. Then, to 'unlock' bigger "
            "tasks, you must deposit your own money first, with the promise of getting it "
            "all back plus a bonus. The deposits keep growing, and the final payout never "
            "comes."
        ),
        prevention=(
            "A real job pays you; it never asks you to pay to start or to unlock work.",
            "Early small 'payouts' are bait to make a larger deposit feel safe.",
            "Be wary of jobs recruited over Telegram or WhatsApp paying for clicks or tasks.",
            "If you must spend your own money to earn, it is a scam.",
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
        how_it_works=(
            "A caller or a pop-up warns that your computer is infected, or that you were "
            "'accidentally refunded' too much. They talk you into installing remote-access "
            "software so they can 'fix' it, then watch you log into your bank and move the "
            "money themselves, or trick you into 'returning' a refund that never existed."
        ),
        prevention=(
            "Microsoft, Apple, and antivirus firms never cold-call you about a virus.",
            "Never install remote-access software for someone who contacted you first.",
            "Disconnect the device, anyone watching your screen can take it over.",
            "A 'refund sent by mistake' that you must repay is always a scam.",
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

    @staticmethod
    def _extract_mentions(conversation: str, hits: list[str], limit: int = 3) -> list[str]:
        """The customer's own sentences that tripped the match, so the debrief can
        quote what *they* described rather than a generic warning."""
        sentences = re.split(r"(?<=[.!?])\s+", conversation.strip())
        low_hits = [h.lower() for h in hits]
        picked: list[str] = []
        for raw in sentences:
            s = raw.strip()
            sl = s.lower()
            if s and s not in picked and any(h in sl for h in low_hits):
                picked.append(s)
            if len(picked) >= limit:
                break
        return picked

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
            mentions=self._extract_mentions(conversation, best_hits),
            how_it_works=best.how_it_works,
            prevention=list(best.prevention),
        )
