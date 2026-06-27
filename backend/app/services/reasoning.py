"""LLM reasoning over the victim's real answers.

After the interactive call gathers what the customer says — who they're paying, why,
and whether someone instructed them — this module asks the LLM to judge whether it's a
scam and what to do, then drafts a formal incident report. Both have deterministic
fallbacks so the path works (less richly) even if the LLM is unavailable.
"""

from __future__ import annotations

import logging

from app.services.llm import LLMClient

logger = logging.getLogger("hyperguard.reasoning")

_ASSESS_SYSTEM = (
    "You are HyperGuard's fraud adjudicator. You are given a flagged bank transfer, its "
    "behavioural risk signals, and the customer's own answers from a verification call. "
    "Decide whether this is an authorised-push-payment scam in progress. Weigh: was the "
    "customer instructed by someone (caller, message, 'official'); urgency, threats, "
    "secrecy; overseas/unknown recipient; investment/prize/refund/safe-account framing; "
    "and whether the stated purpose plausibly matches a genuine, self-initiated payment. "
    "Do NOT accuse a customer paying a known person for a normal reason. Respond ONLY as "
    'JSON: {"scam_likelihood": 0.0-1.0, "is_scam": bool, "reasoning": "<2-3 sentences>", '
    '"recommended_action": "clear"|"monitor"|"escalate", "escalation_reasons": ["..."]}'
)

_REPORT_SYSTEM = (
    "You are HyperGuard's recovery coordinator. Write a concise, formal scam incident "
    "report suitable for the customer's next-of-kin and for filing with the bank's "
    "anti-scam unit / police. Use clear sections: Summary, Customer, Transaction, Why it "
    "was flagged, What the customer said, Assessment, Recommended actions. Plain text, no "
    "markdown headers beyond simple labels. Keep it under ~250 words."
)

_PRESSURE = (
    "urgent", "officer", "police", "arrest", "safe account", "secret", "don't tell",
    "do not tell", "gift card", "crypto", "investment", "guarantee", "prize", "release fee",
    "fee", "verify", "refund", "government", "tax", "fine", "penalty",
)
_INSTRUCTED = (
    "told me", "asked me", "someone", "official", "officer", "they said", "whatsapp",
    "message", "called me", "instructed", "agent", "company",
)


def _heuristic(transaction: dict, risk: dict, answers: list[dict]) -> dict:
    score = float((risk or {}).get("score") or 0.0)
    text = " ".join((a.get("answer") or "").lower() for a in answers)
    coercion = sorted({w for w in _PRESSURE if w in text})
    instructed = any(w in text for w in _INSTRUCTED)

    if score >= 0.85 or coercion or (score >= 0.6 and instructed):
        action = "escalate"
    elif score >= 0.35:
        action = "monitor"
    else:
        action = "clear"

    likelihood = max(score, 0.75 if coercion else score, 0.6 if (score >= 0.6 and instructed) else 0.0)
    reasons = []
    if coercion:
        reasons.append("Scam/coercion language in the customer's answers: " + ", ".join(coercion))
    if score >= 0.85:
        reasons.append("Critical behavioural risk score")
    if instructed and score >= 0.6:
        reasons.append("Customer indicates a third party directed the transfer")
    return {
        "scam_likelihood": round(min(likelihood, 0.99), 2),
        "is_scam": action == "escalate",
        "reasoning": (
            "Automated assessment: "
            + ("; ".join(reasons) if reasons else "no strong scam indicators in the customer's account.")
        ),
        "recommended_action": action,
        "escalation_reasons": reasons,
    }


async def assess(
    llm: LLMClient, *, transaction: dict, risk: dict, classification: dict | None,
    answers: list[dict],
) -> dict:
    fallback = _heuristic(transaction, risk, answers)
    if not llm.enabled or not answers:
        return fallback

    qa = "\n".join(f"Q: {a.get('question')}\nA: {a.get('answer')}" for a in answers)
    signals = ", ".join(s.get("code", "") for s in (risk.get("signals") or []))
    pattern = (classification or {}).get("title")
    user = (
        f"Transaction: {transaction.get('currency', 'SGD')} {transaction.get('amount')} to "
        f"'{transaction.get('payee_name')}' (phone {transaction.get('payee_phone')}, "
        f"country {transaction.get('payee_country')}).\n"
        f"Risk score: {risk.get('score')} ({risk.get('band')}). Signals: {signals or 'none'}. "
        f"Suspected pattern: {pattern or 'unclassified'}.\n\n"
        f"Verification call answers:\n{qa}\n\nAssess this transfer."
    )
    out = await llm.complete_json(_ASSESS_SYSTEM, user)
    if not out:
        return fallback

    action = out.get("recommended_action")
    if action not in ("clear", "monitor", "escalate"):
        action = fallback["recommended_action"]
    try:
        likelihood = round(float(out.get("scam_likelihood", fallback["scam_likelihood"])), 2)
    except (TypeError, ValueError):
        likelihood = fallback["scam_likelihood"]
    return {
        "scam_likelihood": likelihood,
        "is_scam": bool(out.get("is_scam", action == "escalate")),
        "reasoning": (out.get("reasoning") or fallback["reasoning"]).strip(),
        "recommended_action": action,
        "escalation_reasons": out.get("escalation_reasons") or fallback["escalation_reasons"],
    }


_REPORT_ACTIONS = [
    "Place an immediate recall/hold on the transfer with the beneficiary bank.",
    "Flag and freeze the beneficiary account for the receiving institution.",
    "File a police report citing this case reference.",
    "Report the beneficiary to the national anti-scam centre (e.g. ScamShield).",
    "Enrol the customer in step-up verification for outbound transfers for 30 days.",
]


def _fallback_report(case_id, customer, transaction, risk, answers, assessment) -> str:
    qa = "\n".join(f"- Q: {a.get('question')}\n  A: {a.get('answer')}" for a in answers)
    return (
        f"HYPERGUARD INCIDENT REPORT — {case_id}\n\n"
        f"Summary: A {transaction.get('currency','SGD')} {transaction.get('amount')} transfer to "
        f"'{transaction.get('payee_name')}' was flagged and blocked. Scam likelihood "
        f"{assessment.get('scam_likelihood')}.\n\n"
        f"Customer: {customer.get('name')} ({customer.get('phone')}).\n"
        f"Transaction: {transaction.get('currency','SGD')} {transaction.get('amount')} to "
        f"{transaction.get('payee_name')} / {transaction.get('payee_phone') or transaction.get('payee_account')} "
        f"({transaction.get('payee_country')}).\n"
        f"Why flagged: risk {risk.get('score')} ({risk.get('band')}).\n\n"
        f"What the customer said:\n{qa}\n\n"
        f"Assessment: {assessment.get('reasoning')}\n\n"
        "Recommended actions:\n- " + "\n- ".join(_REPORT_ACTIONS)
    )


async def incident_report(
    llm: LLMClient, *, case_id: str, customer: dict, transaction: dict, risk: dict,
    answers: list[dict], assessment: dict,
) -> str:
    fallback = _fallback_report(case_id, customer, transaction, risk, answers, assessment)
    if not llm.enabled:
        return fallback
    qa = "\n".join(f"Q: {a.get('question')}\nA: {a.get('answer')}" for a in answers)
    user = (
        f"Case: {case_id}\nCustomer: {customer.get('name')} ({customer.get('phone')}), "
        f"age {customer.get('age')}, flags {customer.get('vulnerability_flags')}.\n"
        f"Transaction: {transaction.get('currency','SGD')} {transaction.get('amount')} to "
        f"'{transaction.get('payee_name')}' (phone {transaction.get('payee_phone')}, "
        f"country {transaction.get('payee_country')}).\n"
        f"Risk: {risk.get('score')} ({risk.get('band')}).\n"
        f"Assessment: {assessment.get('reasoning')} (likelihood {assessment.get('scam_likelihood')}).\n"
        f"Call answers:\n{qa}\n\nWrite the incident report."
    )
    out = await llm.complete_text(_REPORT_SYSTEM, user)
    return out or fallback
