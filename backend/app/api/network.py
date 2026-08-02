"""The guardian network and the incident reports that flow across it.

Two routers:

- `/api/network` — who watches over whom. A guardian invites a relative; the relative
  accepts. Consent always belongs to the protected person, so the only way an account
  gains a watcher is that account saying yes (or adding the guardian itself).
- `/api/incidents` — the reports delivered along those links, and the *simulated*
  filing a guardian can raise from one.

Access control is explicit on every route rather than implied by the link table:
a report is readable only by the guardian it was addressed to, and a case can only
be sent onward by the customer it belongs to.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import current_user_id, repository
from app.services.auth import normalize_phone
from app.services.filing import file_case, filing_payload
from app.wallet.network import (
    ACTIVE,
    BY_GUARDIAN,
    BY_PROTECTED,
    DECLINED,
    PENDING,
    REVOKED,
    GuardianLink,
    IncidentReport,
    new_link_id,
    new_report_id,
)
from app.wallet.repository import MigrationRequired, WalletRepository
from app.wallet.store import CaseRecord

logger = logging.getLogger("hyperguard.network")

router = APIRouter(prefix="/api/network", tags=["network"])
incidents_router = APIRouter(prefix="/api/incidents", tags=["incidents"])


# ── Payloads ───────────────────────────────────────────────────────────────────
class ProtectRequest(BaseModel):
    phone: str = Field(min_length=3)
    relationship: str = Field(default="family", min_length=1)


class RespondRequest(BaseModel):
    accept: bool


class SendReportRequest(BaseModel):
    case_id: str = Field(min_length=1)
    note: str | None = None


class TransferLimitRequest(BaseModel):
    # None clears the limit. 0 is rejected rather than treated as "block everything",
    # which would be an easy way to lock someone out of their own money by accident.
    amount: float | None = Field(default=None, gt=0)


@dataclass
class EffectiveLimit:
    """The binding per-transfer ceiling on an account, and who set it."""

    amount: float
    guardian_user_id: str
    relationship: str


async def effective_transfer_limit(
    repo: WalletRepository, user_id: str
) -> EffectiveLimit | None:
    """The lowest limit set by any *active* guardian, or None if unrestricted.

    Lowest-wins means adding a guardian can only tighten protection, never loosen
    it, and revoking a link drops its limit automatically.
    """
    candidates = [
        EffectiveLimit(
            amount=float(link.transfer_limit),
            guardian_user_id=link.guardian_user_id,
            relationship=link.relationship,
        )
        for link in await repo.get_links_as_protected(user_id, status=ACTIVE)
        if link.transfer_limit is not None
    ]
    return min(candidates, key=lambda c: c.amount) if candidates else None


# ── Shared helpers ─────────────────────────────────────────────────────────────
async def deliver_incident_report(
    repo: WalletRepository,
    case: CaseRecord,
    *,
    sent_by_user_id: str | None = None,
    note: str | None = None,
) -> list[IncidentReport]:
    """Deliver a case report to every active guardian of the customer it concerns.

    Idempotent per (case, guardian): re-sending updates the existing report rather
    than filling the inbox with duplicates of the same incident.
    """
    if not case.user_id:
        return []
    links = await repo.get_links_as_protected(case.user_id, status=ACTIVE)
    if not links:
        return []

    existing = {r.guardian_user_id: r for r in await repo.get_incidents_for_case(case.case_id)}
    delivered: list[IncidentReport] = []
    for link in links:
        report = existing.get(link.guardian_user_id)
        if report is None:
            report = IncidentReport(
                id=new_report_id(),
                case_id=case.case_id,
                protected_user_id=case.user_id,
                protected_name=case.user_name or "",
                guardian_user_id=link.guardian_user_id,
                sent_by_user_id=sent_by_user_id,
            )
        report.note = note or report.note
        report.amount = float(case.transaction.get("amount") or 0)
        report.currency = case.transaction.get("currency", "SGD")
        report.payee_name = case.transaction.get("payee_name") or ""
        report.scam_title = (case.classification or {}).get("title")
        report.decision = case.decision
        report.risk_score = case.risk_score
        await repo.save_incident(report)
        delivered.append(report)

    logger.info(
        "incident %s delivered to %d guardian(s) of %s", case.case_id, len(delivered), case.user_id
    )
    return delivered


async def link_existing_guardian(
    repo: WalletRepository,
    *,
    protected_user_id: str,
    phone: str,
    relationship: str,
) -> dict | None:
    """Join a newly-added trusted contact to their HyperGuard account, if they have one.

    This is the protected-person-initiated half of the network, so it activates at
    once — the person whose consent matters is the one asking. Returns the guardian's
    brief when a link was made, else None.
    """
    target = await repo.get_credentials(normalize_phone(phone))
    if target is None or target["id"] == protected_user_id:
        return None

    link = await repo.find_link(target["id"], protected_user_id)
    if link is None:
        link = GuardianLink(
            id=new_link_id(),
            guardian_user_id=target["id"],
            protected_user_id=protected_user_id,
            relationship=relationship,
            status=ACTIVE,
            invited_by=BY_PROTECTED,
        )
    elif link.status != ACTIVE:
        link.status = ACTIVE
        link.relationship = relationship
        link.invited_by = BY_PROTECTED
    else:
        return {"id": target["id"], "name": target["name"], "already_linked": True}

    from datetime import datetime, timezone

    link.responded_at = datetime.now(timezone.utc)
    await repo.save_link(link)

    for case in await _cases_for(repo, protected_user_id):
        if case.decision == "block":
            await deliver_incident_report(repo, case)

    logger.info("guardian %s linked to %s via contact add", target["id"], protected_user_id)
    return {"id": target["id"], "name": target["name"], "already_linked": False}


async def _ensure_trusted_contact(
    repo: WalletRepository, protected_user_id: str, guardian: dict, relationship: str
) -> None:
    """Mirror an active link into the protected account's trusted contacts.

    Without this the network would be cosmetic: the Guardian *agent* alerts people
    from `trusted_contacts` during a live intervention, so a guardian who isn't on
    that list would never actually be called mid-scam.
    """
    account = await repo.get_account(protected_user_id)
    if account is None:
        return
    wanted = normalize_phone(guardian.get("phone"))
    already = any(
        normalize_phone(contact.phone) == wanted for contact in account.owner.trusted_contacts
    )
    if already or not wanted:
        return
    await repo.add_contact(protected_user_id, guardian["name"], guardian["phone"], relationship)


async def _briefs(repo: WalletRepository, links: list[GuardianLink]) -> dict[str, dict]:
    ids = [link.guardian_user_id for link in links] + [link.protected_user_id for link in links]
    return await repo.get_user_brief(ids)


def _render(link: GuardianLink, briefs: dict[str, dict], *, counts: dict | None = None) -> dict:
    guardian = briefs.get(link.guardian_user_id, {})
    protected = briefs.get(link.protected_user_id, {})
    payload = link.json(
        guardian_name=guardian.get("name", ""), protected_name=protected.get("name", "")
    )
    payload["guardian"] = guardian
    payload["protected"] = protected
    if counts is not None:
        payload["incidents"] = counts.get(link.protected_user_id, {"total": 0, "unread": 0})
    return payload


# ── Network ────────────────────────────────────────────────────────────────────
@router.get("")
async def my_network(
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> dict:
    """Both sides of the network, plus any invitation awaiting my answer."""
    protecting = await repo.get_links_as_guardian(user_id, status=ACTIVE)
    guardians = await repo.get_links_as_protected(user_id, status=ACTIVE)
    invitations = await repo.get_links_as_protected(user_id, status=PENDING)
    sent = await repo.get_links_as_guardian(user_id, status=PENDING)

    all_links = protecting + guardians + invitations + sent
    briefs = await _briefs(repo, all_links)

    # Unread/total incident counts per protected person, for the "I'm protecting" rows.
    reports = await repo.get_incidents_for_guardian(user_id)
    counts: dict[str, dict] = {}
    for report in reports:
        bucket = counts.setdefault(report.protected_user_id, {"total": 0, "unread": 0})
        bucket["total"] += 1
        bucket["unread"] += 1 if report.unread else 0

    return {
        "protecting": [_render(link, briefs, counts=counts) for link in protecting],
        "guardians": [_render(link, briefs) for link in guardians],
        "invitations": [_render(link, briefs) for link in invitations],
        "invitations_sent": [_render(link, briefs) for link in sent],
        "unread_incidents": sum(bucket["unread"] for bucket in counts.values()),
    }


@router.post("/protect", status_code=201)
async def invite_to_protect(
    body: ProtectRequest,
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> dict:
    """Invite a relative to be protected. They must accept before anything is shared."""
    phone = normalize_phone(body.phone)
    target = await repo.get_credentials(phone)
    if target is None:
        raise HTTPException(
            status_code=404,
            detail="No HyperGuard account uses that number. Ask them to sign up first, "
            "then invite them again.",
        )
    if target["id"] == user_id:
        raise HTTPException(status_code=422, detail="You can't add yourself.")

    existing = await repo.find_link(user_id, target["id"])
    if existing and existing.status == ACTIVE:
        raise HTTPException(status_code=409, detail=f"You already protect {target['name']}.")
    if existing and existing.status == PENDING:
        raise HTTPException(
            status_code=409, detail=f"{target['name']} hasn't answered your last invitation yet."
        )

    if existing:
        # Revive a previously declined or revoked link instead of stacking rows.
        link = existing
        link.status = PENDING
        link.relationship = body.relationship
        link.invited_by = BY_GUARDIAN
        link.responded_at = None
    else:
        link = GuardianLink(
            id=new_link_id(),
            guardian_user_id=user_id,
            protected_user_id=target["id"],
            relationship=body.relationship,
            status=PENDING,
            invited_by=BY_GUARDIAN,
        )
    await repo.save_link(link)

    briefs = await _briefs(repo, [link])
    logger.info("guardian invite %s: %s → %s", link.id, user_id, target["id"])
    return _render(link, briefs)


@router.post("/invitations/{link_id}/respond")
async def respond_to_invitation(
    link_id: str,
    body: RespondRequest,
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> dict:
    """Accept or decline being watched over. Only the protected person may answer."""
    link = await repo.get_link(link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="invitation not found")
    if link.protected_user_id != user_id:
        raise HTTPException(status_code=403, detail="This invitation isn't yours to answer.")
    if link.status != PENDING:
        raise HTTPException(status_code=409, detail="That invitation has already been answered.")

    from datetime import datetime, timezone

    link.status = ACTIVE if body.accept else DECLINED
    link.responded_at = datetime.now(timezone.utc)
    await repo.save_link(link)

    briefs = await _briefs(repo, [link])
    if body.accept:
        guardian = briefs.get(link.guardian_user_id)
        if guardian:
            await _ensure_trusted_contact(repo, user_id, guardian, link.relationship)
        # Backfill: everything already on file is what they signed up to see.
        for case in await _cases_for(repo, user_id):
            if case.decision == "block":
                await deliver_incident_report(repo, case)

    logger.info("invitation %s %s by %s", link_id, link.status, user_id)
    return _render(link, briefs)


@router.post("/links/{link_id}/limit")
async def set_transfer_limit(
    link_id: str,
    body: TransferLimitRequest,
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> dict:
    """Cap what the person you protect can send in one transfer.

    Only the guardian sets it — the whole point is that it survives someone being
    talked into raising it mid-scam. The protected person always *sees* the limit and
    who set it, and can revoke the guardian entirely if they disagree; that's the
    escape hatch, and it's a deliberate one because it can't be done in thirty
    seconds on a phone call.
    """
    link = await repo.get_link(link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="link not found")
    if link.guardian_user_id != user_id:
        raise HTTPException(
            status_code=403, detail="Only the guardian can set a limit on this account."
        )
    if link.status != ACTIVE:
        raise HTTPException(
            status_code=409, detail="They haven't accepted your invitation yet."
        )

    link.transfer_limit = body.amount
    try:
        await repo.save_link(link)
    except MigrationRequired as exc:
        logger.error("%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    logger.info(
        "transfer limit for %s set to %s by %s",
        link.protected_user_id, body.amount, user_id,
    )
    briefs = await _briefs(repo, [link])
    return _render(link, briefs)


@router.delete("/links/{link_id}")
async def revoke_link(
    link_id: str,
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> dict:
    """Either side can end the relationship."""
    link = await repo.get_link(link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="link not found")
    if user_id not in (link.guardian_user_id, link.protected_user_id):
        raise HTTPException(status_code=403, detail="Not your link.")

    from datetime import datetime, timezone

    link.status = REVOKED
    link.responded_at = datetime.now(timezone.utc)
    await repo.save_link(link)
    logger.info("link %s revoked by %s", link_id, user_id)
    return {"revoked": link_id}


async def _cases_for(repo: WalletRepository, user_id: str) -> list[CaseRecord]:
    bank = await repo.load_bank()
    return bank.cases_for(user_id)


# ── Incident reports ───────────────────────────────────────────────────────────
@incidents_router.get("")
async def my_incidents(
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> list[dict]:
    """Reports delivered to me as a guardian, newest first."""
    return [report.json() for report in await repo.get_incidents_for_guardian(user_id)]


@incidents_router.post("/send", status_code=201)
async def send_report(
    body: SendReportRequest,
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> dict:
    """Send one of my own case reports to my active guardians."""
    case = await repo.get_case(body.case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="case not found")
    if case.user_id != user_id:
        raise HTTPException(status_code=403, detail="That case isn't yours to share.")

    delivered = await deliver_incident_report(
        repo, case, sent_by_user_id=user_id, note=body.note
    )
    if not delivered:
        raise HTTPException(
            status_code=409,
            detail="You don't have any guardians yet. Add one from the Network tab first.",
        )
    briefs = await repo.get_user_brief([r.guardian_user_id for r in delivered])
    return {
        "case_id": case.case_id,
        "delivered_to": [
            {"guardian_user_id": r.guardian_user_id,
             "name": briefs.get(r.guardian_user_id, {}).get("name", ""),
             "report_id": r.id}
            for r in delivered
        ],
    }


@incidents_router.get("/{report_id}")
async def incident_detail(
    report_id: str,
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> dict:
    """The full account of what happened, and any filing already raised.

    Opening it marks it read — the guardian equivalent of an acknowledgement.
    """
    report = await _authorised_report(repo, report_id, user_id)
    case = await repo.get_case(report.case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="case not found")

    if report.unread:
        from datetime import datetime, timezone

        report.read_at = datetime.now(timezone.utc)
        await repo.save_incident(report)

    filing = await repo.get_filing(report.case_id)
    briefs = await repo.get_user_brief([report.protected_user_id])
    return {
        "report": report.json(),
        "protected": briefs.get(report.protected_user_id, {}),
        "case": case.detail(),
        "filing": filing_payload(filing) if filing else None,
    }


@incidents_router.post("/{report_id}/file", status_code=201)
async def file_with_authorities(
    report_id: str,
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> dict:
    """Raise a SIMULATED report to the anti-scam authorities.

    Nothing is transmitted anywhere — see `services/filing`. The response carries
    `simulated: true`, a `SIM-` reference and the real reporting channels, and the
    client is expected to display all three.
    """
    report = await _authorised_report(repo, report_id, user_id)
    case = await repo.get_case(report.case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="case not found")

    existing = await repo.get_filing(report.case_id)
    if existing is not None:
        # Filing twice for one case would produce two references for one incident.
        return {"filing": filing_payload(existing), "already_filed": True}

    filing = file_case(case, filed_by_user_id=user_id)
    await repo.save_filing(filing)
    return {"filing": filing_payload(filing), "already_filed": False}


async def _authorised_report(
    repo: WalletRepository, report_id: str, user_id: str
) -> IncidentReport:
    """A report is readable by the guardian it was sent to, or the person it is about."""
    report = await repo.get_incident(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    if user_id not in (report.guardian_user_id, report.protected_user_id):
        raise HTTPException(status_code=403, detail="This report wasn't shared with you.")
    return report
