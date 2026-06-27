"""Phone-number → country resolution, dependency-free.

A small E.164 calling-code map, longest-prefix-wins, sufficient for the risk
engine's `overseas_number` signal. We deliberately avoid pulling in a full
libphonenumber dependency: the only question we ask is "is this calling code the
customer's home country or not", and a legible prefix table answers it
transparently (and keeps the scoring auditable).

A number without a leading `+` is treated as *local* (returns None) so the engine
falls back to the customer's home country and never raises a spurious overseas flag.
"""

from __future__ import annotations

import re

# ISO-3166 alpha-2 keyed by E.164 calling code. Ordered loosely by relevance to a
# Singapore customer; lookup tries 3-, then 2-, then 1-digit prefixes.
_CALLING_CODES: dict[str, str] = {
    "65": "SG",
    "60": "MY",
    "62": "ID",
    "66": "TH",
    "63": "PH",
    "84": "VN",
    "91": "IN",
    "86": "CN",
    "852": "HK",
    "853": "MO",
    "886": "TW",
    "81": "JP",
    "82": "KR",
    "61": "AU",
    "64": "NZ",
    "44": "GB",
    "49": "DE",
    "33": "FR",
    "971": "AE",
    "1": "US",
}


def parse_country(phone: str | None) -> str | None:
    """Resolve an E.164 phone to an ISO country code.

    Returns None when the input is empty or local (no `+`). Returns "INTL" for a
    valid international number whose calling code isn't in the table — still
    overseas, just unidentified.
    """
    if not phone:
        return None
    cleaned = re.sub(r"[^\d+]", "", phone)
    if not cleaned.startswith("+"):
        return None
    digits = cleaned[1:]
    for n in (3, 2, 1):
        if len(digits) >= n and digits[:n] in _CALLING_CODES:
            return _CALLING_CODES[digits[:n]]
    return "INTL"
