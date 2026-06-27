"""Post-call follow-up: reason over the victim's answers, then escalate.

Triggered when the interactive intervention call ends. It pulls the case context the
registry captured from the event stream + the customer's spoken answers, asks the LLM to
adjudicate, and — when warranted — alerts the guardians by SMS and files a generated
incident report. Everything is emitted onto the bus (so the app + console update live)
and persisted to the case.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.domain.events import EventType, SwarmEvent
from app.graph import get_orchestrator
from app.schemas import CustomerProfile
from app.services.reasoning import assess, incident_report
from app.wallet.registry import get_registry
from app.wallet.repository import get_repository

logger = logging.getLogger("hyperguard.followup")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guardian_message(customer_name: str, transaction: dict, assessment: dict) -> str:
    amount = f"{transaction.get('currency', 'SGD')} {transaction.get('amount'):,.0f}"
    return (
        f"HyperGuard alert: we blocked a {amount} transfer by {customer_name} to "
        f"{transaction.get('payee_name')}. After speaking with them our assessment is a likely "
        f"scam ({int(assessment.get('scam_likelihood', 0) * 100)}%). {assessment.get('reasoning')} "
        "Please check on them now."
    )


async def finalize_followup(case_id: str) -> None:
    reg = get_registry()
    bucket = reg.get(case_id)
    if bucket is None:
        logger.warning("finalize_followup: unknown case %s", case_id)
        return

    rt = get_orchestrator().rt
    customer_d = bucket.get("customer") or {}
    txn_d = bucket.get("transaction") or {}
    risk_d = bucket.get("risk") or {}
    classification_d = bucket.get("classification")
    answers = bucket.get("context") or []

    assessment = await assess(
        rt.llm, transaction=txn_d, risk=risk_d, classification=classification_d, answers=answers
    )
    await rt.bus.publish(
        SwarmEvent(
            type=EventType.assessment_ready, case_id=case_id, agent="educator",
            payload={"assessment": assessment},
        )
    )

    escalate = assessment.get("recommended_action") == "escalate"
    guardian_alerts: list[dict] = []
    report: str | None = None

    if escalate:
        customer = None
        try:
            customer = CustomerProfile(**customer_d)
        except Exception:  # pragma: no cover - defensive
            logger.warning("finalize_followup: could not rebuild customer for %s", case_id)

        if customer and customer.trusted_contacts:
            message = _guardian_message(customer.name, txn_d, assessment)
            for contact in sorted(customer.trusted_contacts, key=lambda c: c.priority):
                alert = await rt.notify.send_sms(contact, message)
                if not rt.notify.is_live:
                    alert.acknowledged = True
                    alert.status = "acknowledged"
                payload = alert.model_dump(mode="json")
                guardian_alerts.append(payload)
                await rt.bus.publish(
                    SwarmEvent(
                        type=EventType.guardian_alerted, case_id=case_id, agent="guardian",
                        payload={"alert": payload},
                    )
                )

        report = await incident_report(
            rt.llm, case_id=case_id, customer=customer_d, transaction=txn_d,
            risk=risk_d, answers=answers, assessment=assessment,
        )

    escalation = {
        "escalated": escalate,
        "guardians_notified": len(guardian_alerts),
        "guardian_alerts": guardian_alerts,
        # No real police API exists; the filing is generated and recorded.
        "filed_with_authorities": escalate,
        "reasons": assessment.get("escalation_reasons", []),
    }

    if escalate:
        await rt.bus.publish(
            SwarmEvent(
                type=EventType.report_filed, case_id=case_id, agent="recovery_coordinator",
                payload={"escalation": escalation, "report": report},
            )
        )

    reg.set_followup(case_id, assessment=assessment, escalation=escalation, report=report)

    # Build the call transcript from the synchronously-stored Q&A (the bus-recorded
    # turns can race finalize), and persist it into the case so the control centre's
    # case detail shows the conversation — the case row was first written at block
    # time, before the interview happened.
    ts = _now_iso()
    transcript: list[dict] = []
    for i, qa in enumerate(answers):
        transcript.append({"index": 2 * i, "speaker": "agent", "text": qa.get("question", ""), "ts": ts, "tags": []})
        transcript.append({"index": 2 * i + 1, "speaker": "customer", "text": qa.get("answer", ""), "ts": ts, "tags": []})

    try:
        await get_repository().update_followup(
            case_id, context=answers, assessment=assessment, escalation=escalation,
            report=report, transcript=transcript,
        )
    except Exception as exc:  # pragma: no cover - persistence best-effort
        logger.warning("persisting follow-up for %s failed: %s", case_id, exc)

    logger.info(
        "Follow-up complete for %s: action=%s, guardians=%d, filed=%s",
        case_id, assessment.get("recommended_action"), len(guardian_alerts), escalate,
    )
