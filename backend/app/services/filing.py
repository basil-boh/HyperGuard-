"""Simulated anti-scam authority filing.

**Nothing here contacts anyone.** HyperGuard has no integration with the Singapore
Police Force, the National Anti-Scam Centre, ScamShield, or any other body, and this
module deliberately has no network access of any kind. It generates a plausible
*artefact* — a reference number, a status, a timeline — so the demo can show what
the hand-off to authorities would look like once a real integration existed.

Three things keep that honest, and they should stay:

1. Every reference is prefixed `SIM-`.
2. Every payload carries `simulated: true` and a disclaimer naming the real channel.
3. The status timeline stops at "referred" — it never fabricates an outcome such as
   funds recovered or an arrest.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.wallet.network import SIMULATION_DISCLAIMER, AuthorityFiling
from app.wallet.store import CaseRecord

logger = logging.getLogger("hyperguard.filing")

AUTHORITY = "National Anti-Scam Centre (NASC), Singapore — SIMULATED"

# The real channels, surfaced alongside the simulation so the useful information is
# never crowded out by the demo artefact.
REAL_CHANNELS = [
    "ScamShield helpline: 1799",
    "Police i-Witness / e-services: police.gov.sg",
    "Your bank's 24-hour fraud line (freeze the account first)",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def build_reference(case_id: str, at: datetime | None = None) -> str:
    """`SIM-NASC-<year>-<6 hex>`. The SIM- prefix is not decorative — keep it."""
    at = at or _now()
    suffix = uuid4().hex[:6].upper()
    return f"SIM-NASC-{at.year}-{suffix}"


def file_case(
    case: CaseRecord, *, filed_by_user_id: str, reference: str | None = None
) -> AuthorityFiling:
    """Produce the simulated filing artefact for a case.

    Pure and side-effect free apart from a log line: the caller persists it.
    """
    at = _now()
    filing = AuthorityFiling(
        case_id=case.case_id,
        reference=reference or build_reference(case.case_id, at),
        authority=AUTHORITY,
        filed_by_user_id=filed_by_user_id,
        filed_at=at,
        status="referred",
        timeline=[
            {
                "at": at.isoformat(),
                "status": "received",
                "note": (
                    f"Report received for case {case.case_id}: attempted "
                    f"{case.transaction.get('currency', 'SGD')} "
                    f"{float(case.transaction.get('amount') or 0):,.0f} to "
                    f"{case.transaction.get('payee_name')}."
                ),
            },
            {
                "at": (at + timedelta(seconds=90)).isoformat(),
                "status": "under_review",
                "note": (
                    "Evidence package acknowledged: risk rationale, call transcript, "
                    f"scam classification ({case.classification.get('title') if case.classification else 'unclassified'}) "
                    "and guardian actions."
                ),
            },
            {
                "at": (at + timedelta(minutes=6)).isoformat(),
                "status": "referred",
                "note": (
                    f"Beneficiary account {case.transaction.get('payee_account') or '—'} "
                    "referred to the receiving institution for freeze and trace."
                ),
            },
        ],
        simulated=True,
    )
    logger.info(
        "SIMULATED filing %s for case %s by %s — nothing was transmitted",
        filing.reference, case.case_id, filed_by_user_id,
    )
    return filing


def filing_payload(filing: AuthorityFiling) -> dict:
    """The filing as the API returns it, with the real reporting channels attached."""
    return {**filing.json(), "real_channels": REAL_CHANNELS, "disclaimer": SIMULATION_DISCLAIMER}
