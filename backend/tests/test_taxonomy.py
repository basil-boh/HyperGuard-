"""Scam taxonomy — every archetype must recognise its own victim script.

The demo path feeds each archetype's `victim_script` back through `classify()`. If an
archetype's indicators drift away from the language in its own script, the Educator
never confirms the pattern, the guardian is never alerted, and the console shows
"No scam pattern detected" over an obvious scam. These tests pin that closed.
"""

from __future__ import annotations

import pytest

from app.services.scam_taxonomy import _LIBRARY, ScamTaxonomy

# The confidence the graph requires before it treats a pattern as confirmed
# (see `SwarmOrchestrator._route_after_educator`).
CONFIRMATION_THRESHOLD = 0.6

ARCHETYPES = [arch.key for arch in _LIBRARY]


@pytest.mark.parametrize("key", ARCHETYPES, ids=[k.value for k in ARCHETYPES])
def test_archetype_recognises_its_own_script(key) -> None:
    taxonomy = ScamTaxonomy()
    classification = taxonomy.classify(" ".join(taxonomy.victim_script(key)))
    assert classification.archetype == key
    assert classification.confidence >= CONFIRMATION_THRESHOLD


@pytest.mark.parametrize("key", ARCHETYPES, ids=[k.value for k in ARCHETYPES])
def test_pattern_is_confirmed_before_the_script_runs_out(key) -> None:
    """Confirmation must land while the victim still has lines left to speak.

    The negotiator consumes one script line per turn; a pattern only recognised on
    the final line risks the call ending before the Educator can intervene.
    """
    taxonomy = ScamTaxonomy()
    script = taxonomy.victim_script(key)
    confirmed_at = next(
        (
            spoken
            for spoken in range(1, len(script) + 1)
            if (c := taxonomy.classify(" ".join(script[:spoken]))).archetype == key
            and c.confidence >= CONFIRMATION_THRESHOLD
        ),
        None,
    )
    assert confirmed_at is not None, f"{key.value} never confirms"
    assert confirmed_at < len(script), (
        f"{key.value} only confirms on its last line ({confirmed_at}/{len(script)})"
    )


def test_indicators_actually_appear_in_the_script() -> None:
    """At least two distinct fingerprints per archetype must be real, not aspirational."""
    taxonomy = ScamTaxonomy()
    for arch in _LIBRARY:
        text = " ".join(taxonomy.victim_script(arch.key)).lower()
        matched = [ind for ind in arch.indicators if ind in text]
        assert len(matched) >= 2, f"{arch.key.value} only matches {matched}"


def test_innocent_conversation_is_not_labelled_a_scam() -> None:
    taxonomy = ScamTaxonomy()
    legit = taxonomy.classify(" ".join(ScamTaxonomy.LEGIT_SCRIPT))
    assert legit.archetype.value in ("none", "unknown")
    assert legit.confidence < CONFIRMATION_THRESHOLD


def test_scripts_do_not_cross_classify() -> None:
    """Each script must match its own archetype more strongly than any other."""
    taxonomy = ScamTaxonomy()
    for arch in _LIBRARY:
        text = " ".join(taxonomy.victim_script(arch.key)).lower()
        own = len([i for i in arch.indicators if i in text])
        for other in _LIBRARY:
            if other.key is arch.key:
                continue
            theirs = len([i for i in other.indicators if i in text])
            assert theirs < own, (
                f"{arch.key.value}'s script matches {other.key.value} "
                f"({theirs}) as strongly as itself ({own})"
            )
