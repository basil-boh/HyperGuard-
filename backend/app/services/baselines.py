"""Learned behavioural baselines.

The risk engine scores a transfer against the customer's *normal* behaviour. In the
demo that normal was a static seeded constant; here we derive it from the account's
real, persisted history so the platform actually learns each user:

- average / spread of past outbound amounts  → `amount_anomaly`
- the set of payees and phone numbers paid before → `new_payee` / `unknown_number`
- the hours the customer is usually active     → `off_hours`
- typical transfers per day                    → `velocity_spike`

"Known" means *paid before* or *explicitly trusted* — deliberately NOT "merely saved
as a recipient", so a saved-but-never-paid payee still trips `new_payee`/`unknown_number`
on the first transfer (that's exactly "first time transfer to that person").

Cold start: under `LEARNING_MIN_TRANSACTIONS` of history we fall back to wide, lenient
defaults for the history-dependent axes (amount/hours/velocity) so a brand-new user
isn't drowned in false positives — while the history-free signals (new payee, unknown
number, overseas number, coercion language) stay fully active from transaction #1.
"""

from __future__ import annotations

import statistics

from app.schemas import CustomerProfile
from app.wallet.store import Account

LEARNING_MIN_TRANSACTIONS = 5

# Lenient cold-start defaults: a wide std suppresses spurious amount anomalies while
# still catching an order-of-magnitude spike. Hours span the full day so a user with
# no learned pattern is never flagged for "off-hours" (we have no baseline yet); the
# history-free signals still protect them from transaction #1.
_DEFAULT_AVG = 200.0
_DEFAULT_STD = 400.0
_DEFAULT_HOUR_START = 0
_DEFAULT_HOUR_END = 24
_DEFAULT_VELOCITY = 2.0


def derive_profile(account: Account) -> CustomerProfile:
    """Return a copy of the account owner's profile with baselines learned from history."""
    owner = account.owner
    paid = [
        e
        for e in account.ledger
        if e.direction == "out" and e.status in ("approved", "completed")
    ]
    amounts = [e.amount for e in paid]

    known_payees = sorted(
        {e.counterparty for e in paid}
        | {c.name for c in owner.trusted_contacts}
        | set(owner.known_payees)
    )
    known_payee_phones = sorted(
        {e.counterparty_phone for e in paid if e.counterparty_phone}
        | {c.phone for c in owner.trusted_contacts}
        | set(owner.known_payee_phones)
    )

    if len(amounts) >= LEARNING_MIN_TRANSACTIONS:
        avg = statistics.fmean(amounts)
        std = statistics.pstdev(amounts) or _DEFAULT_STD
        hours = [e.ts.hour for e in paid]
        hour_start, hour_end = min(hours), max(hours) + 1
        span_days = max((max(e.ts for e in paid) - min(e.ts for e in paid)).days, 1)
        velocity = len(paid) / span_days
    else:
        avg, std = _DEFAULT_AVG, _DEFAULT_STD
        hour_start, hour_end = _DEFAULT_HOUR_START, _DEFAULT_HOUR_END
        velocity = _DEFAULT_VELOCITY

    return owner.model_copy(
        update={
            "baseline_avg_amount": avg,
            "baseline_std_amount": std,
            "typical_hour_start": hour_start,
            "typical_hour_end": hour_end,
            "typical_velocity_per_day": velocity,
            "known_payees": known_payees,
            "known_payee_phones": known_payee_phones,
        }
    )
