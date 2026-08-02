"""The guardian network: consent, delivery, access control, and the simulated filing."""

from __future__ import annotations

import pytest

from app.api.network import effective_transfer_limit
from app.services.filing import build_reference, file_case, filing_payload
from app.wallet.network import (
    ACTIVE,
    PENDING,
    REVOKED,
    GuardianLink,
    IncidentReport,
    new_link_id,
    row_to_filing,
    row_to_link,
    row_to_report,
    filing_to_row,
    link_to_row,
    report_to_row,
)
from app.wallet.repository import InMemoryRepository
from app.wallet.store import Bank


@pytest.fixture
def bank() -> Bank:
    return Bank()


@pytest.fixture
def repo(bank: Bank) -> InMemoryRepository:
    return InMemoryRepository(bank)


# ── Seeded network ─────────────────────────────────────────────────────────────
def test_marcus_protects_both_parents(bank: Bank) -> None:
    protecting = {
        link.protected_user_id: link for link in bank.links_as_guardian("acc_marcus", status=ACTIVE)
    }
    assert set(protecting) == {"acc_alex", "acc_may"}
    assert protecting["acc_may"].relationship == "son"


def test_seeded_guardians_have_real_accounts(bank: Bank) -> None:
    """A link is only meaningful if both ends can actually sign in."""
    for link in bank.links.values():
        assert bank.account(link.guardian_user_id) is not None, link.id
        assert bank.account(link.protected_user_id) is not None, link.id
        assert bank.account(link.guardian_user_id).pin_hash


def test_a_pending_invitation_is_waiting_for_wong(bank: Bank) -> None:
    invitations = bank.links_as_protected("acc_wong", status=PENDING)
    assert len(invitations) == 1
    assert invitations[0].guardian_user_id == "acc_marcus"


def test_nobody_guards_themselves(bank: Bank) -> None:
    assert all(l.guardian_user_id != l.protected_user_id for l in bank.links.values())


def test_incidents_only_exist_for_active_links(bank: Bank) -> None:
    active = {
        (l.guardian_user_id, l.protected_user_id)
        for l in bank.links.values()
        if l.status == ACTIVE
    }
    for report in bank.incidents.values():
        assert (report.guardian_user_id, report.protected_user_id) in active


def test_seeded_inbox_has_both_read_and_unread(bank: Bank) -> None:
    inbox = bank.incidents_for_guardian("acc_marcus")
    assert any(r.unread for r in inbox)
    assert any(not r.unread for r in inbox)


def test_seeded_reports_point_at_real_cases(bank: Bank) -> None:
    for report in bank.incidents.values():
        case = bank.cases.get(report.case_id)
        assert case is not None, report.case_id
        assert case.user_id == report.protected_user_id
        assert report.amount == float(case.transaction.get("amount") or 0)


# ── Link bookkeeping ───────────────────────────────────────────────────────────
async def test_find_link_is_direction_sensitive(repo: InMemoryRepository) -> None:
    assert await repo.find_link("acc_marcus", "acc_may") is not None
    # May does not guard Marcus — the reverse pair is a different relationship.
    assert await repo.find_link("acc_may", "acc_marcus") is None


async def test_revoking_removes_it_from_both_views(repo: InMemoryRepository) -> None:
    link = await repo.find_link("acc_marcus", "acc_may")
    link.status = REVOKED
    await repo.save_link(link)

    assert all(
        l.protected_user_id != "acc_may"
        for l in await repo.get_links_as_guardian("acc_marcus", status=ACTIVE)
    )
    assert all(
        l.guardian_user_id != "acc_marcus"
        for l in await repo.get_links_as_protected("acc_may", status=ACTIVE)
    )
    # The row survives, so past access remains auditable.
    assert await repo.get_link(link.id) is not None


async def test_user_brief_never_carries_credentials(repo: InMemoryRepository) -> None:
    briefs = await repo.get_user_brief(["acc_may", "acc_marcus"])
    assert set(briefs) == {"acc_may", "acc_marcus"}
    for brief in briefs.values():
        assert "pin" not in str(brief).lower()
        assert "balance" not in brief


async def test_unknown_ids_are_omitted_not_raised(repo: InMemoryRepository) -> None:
    briefs = await repo.get_user_brief(["acc_may", "acc_nope"])
    assert briefs.keys() == {"acc_may"}


# ── Incident reports ───────────────────────────────────────────────────────────
async def test_saving_a_report_makes_it_visible_to_that_guardian(
    repo: InMemoryRepository, bank: Bank
) -> None:
    case = bank.cases_for("acc_priya")[0]
    report = IncidentReport(
        id="inc_test",
        case_id=case.case_id,
        protected_user_id="acc_priya",
        protected_name="Priya Nair",
        guardian_user_id="acc_linda",
    )
    await repo.save_incident(report)
    assert any(r.id == "inc_test" for r in await repo.get_incidents_for_guardian("acc_linda"))
    assert not any(r.id == "inc_test" for r in await repo.get_incidents_for_guardian("acc_marcus"))


def test_reading_flips_unread(bank: Bank) -> None:
    from datetime import datetime, timezone

    report = next(r for r in bank.incidents.values() if r.unread)
    assert report.unread
    report.read_at = datetime.now(timezone.utc)
    assert not report.unread


# ── Guardian transfer limit ────────────────────────────────────────────────────
async def test_no_limit_by_default(repo: InMemoryRepository) -> None:
    """Seeded accounts start unrestricted, so no existing demo path changes."""
    assert await effective_transfer_limit(repo, "acc_may") is None


async def test_a_guardians_limit_binds_the_protected_account(
    repo: InMemoryRepository,
) -> None:
    link = await repo.find_link("acc_marcus", "acc_may")
    link.transfer_limit = 500.0
    await repo.save_link(link)

    limit = await effective_transfer_limit(repo, "acc_may")
    assert limit is not None
    assert limit.amount == 500.0
    assert limit.guardian_user_id == "acc_marcus"
    assert limit.relationship == "son"


async def test_the_lowest_limit_wins(repo: InMemoryRepository, bank: Bank) -> None:
    """Adding a guardian can only tighten protection, never loosen it."""
    first = await repo.find_link("acc_marcus", "acc_may")
    first.transfer_limit = 500.0
    await repo.save_link(first)

    second = GuardianLink(
        id=new_link_id(),
        guardian_user_id="acc_linda",
        protected_user_id="acc_may",
        relationship="daughter",
        status=ACTIVE,
        transfer_limit=200.0,
    )
    await repo.save_link(second)

    limit = await effective_transfer_limit(repo, "acc_may")
    assert limit.amount == 200.0 and limit.guardian_user_id == "acc_linda"


async def test_a_pending_guardian_cannot_impose_a_limit(repo: InMemoryRepository) -> None:
    """Marcus's invitation to Wong is unanswered — it must not bind anything yet."""
    pending = await repo.find_link("acc_marcus", "acc_wong")
    assert pending.status == PENDING
    pending.transfer_limit = 50.0
    await repo.save_link(pending)

    assert await effective_transfer_limit(repo, "acc_wong") is None


async def test_revoking_a_guardian_drops_their_limit(repo: InMemoryRepository) -> None:
    link = await repo.find_link("acc_marcus", "acc_may")
    link.transfer_limit = 500.0
    await repo.save_link(link)
    assert await effective_transfer_limit(repo, "acc_may") is not None

    link.status = REVOKED
    await repo.save_link(link)
    assert await effective_transfer_limit(repo, "acc_may") is None


async def test_clearing_a_limit_restores_full_access(repo: InMemoryRepository) -> None:
    link = await repo.find_link("acc_marcus", "acc_may")
    link.transfer_limit = 500.0
    await repo.save_link(link)

    link.transfer_limit = None
    await repo.save_link(link)
    assert await effective_transfer_limit(repo, "acc_may") is None


def test_limit_survives_a_row_round_trip() -> None:
    link = GuardianLink(
        id=new_link_id(),
        guardian_user_id="acc_marcus",
        protected_user_id="acc_may",
        relationship="son",
        status=ACTIVE,
        transfer_limit=500.0,
    )
    assert row_to_link(link_to_row(link)).transfer_limit == 500.0
    link.transfer_limit = None
    assert row_to_link(link_to_row(link)).transfer_limit is None


# ── Simulated filing ───────────────────────────────────────────────────────────
def test_reference_is_marked_simulated() -> None:
    assert build_reference("HG-X").startswith("SIM-")


def test_filing_declares_itself_simulated(bank: Bank) -> None:
    case = bank.cases_for("acc_may")[0]
    filing = file_case(case, filed_by_user_id="acc_marcus")
    assert filing.simulated is True
    assert filing.reference.startswith("SIM-")
    assert "SIMULATED" in filing.authority


def test_filing_payload_carries_disclaimer_and_real_channels(bank: Bank) -> None:
    """The useful information must travel with the fake artefact, always."""
    filing = file_case(bank.cases_for("acc_may")[0], filed_by_user_id="acc_marcus")
    payload = filing_payload(filing)
    assert payload["simulated"] is True
    assert "not connected to the police" in payload["disclaimer"]
    assert any("1799" in channel for channel in payload["real_channels"])


def test_filing_timeline_never_claims_an_outcome(bank: Bank) -> None:
    """It may say a report was received and referred — never that anyone was caught
    or that money came back."""
    filing = file_case(bank.cases_for("acc_may")[0], filed_by_user_id="acc_marcus")
    text = " ".join(step["note"] for step in filing.timeline).lower()
    for invented in ("recovered", "arrest", "refund", "convicted", "returned to"):
        assert invented not in text
    assert filing.status == "referred"


def test_seeded_filing_is_simulated_too(bank: Bank) -> None:
    assert bank.filings
    for filing in bank.filings.values():
        assert filing.simulated and filing.reference.startswith("SIM-")


# ── Row round-trips (the Supabase path) ────────────────────────────────────────
def test_link_row_round_trip() -> None:
    link = GuardianLink(
        id=new_link_id(),
        guardian_user_id="acc_marcus",
        protected_user_id="acc_may",
        relationship="son",
        status=ACTIVE,
    )
    restored = row_to_link(link_to_row(link))
    assert restored.id == link.id
    assert restored.status == ACTIVE
    assert restored.created_at == link.created_at


def test_report_row_round_trip(bank: Bank) -> None:
    report = next(iter(bank.incidents.values()))
    restored = row_to_report(report_to_row(report))
    assert restored.id == report.id
    assert restored.unread == report.unread
    assert restored.amount == report.amount


def test_filing_row_round_trip(bank: Bank) -> None:
    filing = file_case(bank.cases_for("acc_wong")[0], filed_by_user_id="acc_linda")
    restored = row_to_filing(filing_to_row(filing))
    assert restored.reference == filing.reference
    assert restored.simulated is True
    assert len(restored.timeline) == len(filing.timeline)
