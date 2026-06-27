"""The Digital Twin's scoring core.

A transparent, fully deterministic behavioural model: every customer carries a
baseline, each signal contributes an explainable amount of evidence, and the
signals combine through a logistic link into a 0..1 risk score. We deliberately
avoid an opaque ML model here, at the moment of intervention the *explanation*
is as important as the number, both for the customer on the phone and for the
audit trail an investigator reads later.
"""

from __future__ import annotations

import math

from app.schemas import (
    CustomerProfile,
    RiskAssessment,
    RiskBand,
    RiskSignal,
    TransactionRequest,
)

# Urgency / coercion lexicon that frequently rides along with social-engineering.
_PRESSURE_TERMS = (
    "urgent",
    "immediately",
    "safe account",
    "verify",
    "secret",
    "don't tell",
    "do not tell",
    "arrest",
    "fine",
    "penalty",
    "guarantee",
    "refund",
    "gift card",
    "crypto",
)


def _logistic(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def _band(score: float) -> RiskBand:
    if score >= 0.85:
        return RiskBand.critical
    if score >= 0.6:
        return RiskBand.high
    if score >= 0.35:
        return RiskBand.elevated
    return RiskBand.minimal


class RiskEngine:
    """Behavioural anomaly scorer. Weights are intentionally legible constants."""

    BIAS = -2.6  # pushes the baseline transaction toward "safe"
    MODEL_VERSION = "twin-heuristic-1"

    def assess(
        self, customer: CustomerProfile, txn: TransactionRequest
    ) -> RiskAssessment:
        raw: list[tuple[RiskSignal, float]] = []  # (signal, weighted evidence)

        # 1) New payee, the single strongest predictor of authorised-push fraud.
        if txn.payee_name not in customer.known_payees:
            raw.append(
                (
                    self._signal(
                        "new_payee",
                        "First-ever transfer to this payee",
                        "alarm",
                        f"'{txn.payee_name}' has never received funds from this account.",
                    ),
                    1.7,
                )
            )

        # 2) Amount anomaly, z-score against the customer's own history.
        std = max(customer.baseline_std_amount, 1.0)
        z = (txn.amount - customer.baseline_avg_amount) / std
        if z > 1.0:
            intensity = min(z / 4.0, 1.0)
            raw.append(
                (
                    self._signal(
                        "amount_anomaly",
                        f"Amount is {z:.1f}σ above normal",
                        "alarm" if z >= 3 else "warn",
                        f"{txn.currency} {txn.amount:,.0f} vs a typical "
                        f"{txn.currency} {customer.baseline_avg_amount:,.0f}.",
                    ),
                    1.6 * intensity,
                )
            )

        # 3) Off-hours activity.
        hour = txn.requested_at.hour
        if not (customer.typical_hour_start <= hour < customer.typical_hour_end):
            raw.append(
                (
                    self._signal(
                        "off_hours",
                        "Transfer outside normal active hours",
                        "warn",
                        f"Initiated at {hour:02d}:00; customer is usually active "
                        f"{customer.typical_hour_start:02d}:00–{customer.typical_hour_end:02d}:00.",
                    ),
                    0.8,
                )
            )

        # 4) Velocity spike.
        if txn.recent_transfer_count_24h > max(customer.typical_velocity_per_day * 2, 2):
            raw.append(
                (
                    self._signal(
                        "velocity_spike",
                        "Unusual burst of transfers",
                        "warn",
                        f"{txn.recent_transfer_count_24h} transfers in 24h vs a typical "
                        f"{customer.typical_velocity_per_day:.1f}/day.",
                    ),
                    0.9,
                )
            )

        # 5) Coercion language in the memo.
        memo = (txn.memo or "").lower()
        hits = sorted({term for term in _PRESSURE_TERMS if term in memo})
        if hits:
            raw.append(
                (
                    self._signal(
                        "pressure_language",
                        "Coercion language in transfer note",
                        "alarm",
                        "Matched: " + ", ".join(hits),
                    ),
                    0.7 * min(len(hits), 3),
                )
            )

        # 6) Vulnerability amplifier, never a signal on its own, but it raises the
        #    stakes of every other signal for an at-risk customer.
        amplifier = 1.0
        if customer.vulnerability_flags and raw:
            amplifier = 1.15
            raw.append(
                (
                    self._signal(
                        "elevated_vulnerability",
                        "Customer flagged as higher-risk",
                        "info",
                        "Flags: " + ", ".join(customer.vulnerability_flags),
                    ),
                    0.4,
                )
            )

        evidence = sum(weight for _, weight in raw)
        score = _logistic(self.BIAS + evidence) * amplifier
        score = round(min(score, 0.99), 4)

        # Distribute the final score across signals for an honest contribution bar.
        total_weight = sum(weight for _, weight in raw) or 1.0
        signals: list[RiskSignal] = []
        for signal, weight in raw:
            signal.contribution = round((weight / total_weight) * score, 4)
            signals.append(signal)

        return RiskAssessment(
            transaction_id=txn.id,
            score=score,
            band=_band(score),
            signals=signals,
            rationale=self._rationale(score, signals),
            model_version=self.MODEL_VERSION,
        )

    @staticmethod
    def _signal(code: str, label: str, severity: str, detail: str) -> RiskSignal:
        return RiskSignal(
            code=code, label=label, contribution=0.0, severity=severity, detail=detail
        )

    @staticmethod
    def _rationale(score: float, signals: list[RiskSignal]) -> str:
        if not signals:
            return "Transfer matches the customer's established behaviour on every axis."
        lead = sorted(signals, key=lambda s: s.contribution, reverse=True)[:3]
        drivers = "; ".join(s.label.lower() for s in lead)
        return (
            f"Risk {score:.0%}, driven primarily by {drivers}. "
            "Pattern is consistent with an authorised-push-payment scam in progress."
        )
