"""
tests/test_isotopy.py
Unit tests for the isotopy pipeline.

Run from projects/isotopy/:
    python3 -m pytest tests/ -v
or:
    python3 tests/test_isotopy.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

from isotopy import build_rings_from_dicts


# ---------------------------------------------------------------------------
# Fixtures — load definition files once for all tests
# ---------------------------------------------------------------------------

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')


def _load(name: str) -> dict:
    path = os.path.join(DATA, name)
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _get_rings():
    wk    = _load('potocki_definitions_wikt.json')
    wn    = _load('potocki_definitions_wn.json')
    mw    = _load('potocki_definitions_mw.json')
    w1828 = _load('potocki_definitions_w1828.json')
    return build_rings_from_dicts(wk=wk, wn=wn, mw=mw, w1828=w1828, verbose=False)


# ---------------------------------------------------------------------------
# test_no_dead_l2
# ---------------------------------------------------------------------------

def test_no_dead_l2():
    """
    Confirm expand() produces non-empty profiles for representative lemmas.

    If L2 expansion were incorrectly left in and still dead, 'ghost' would
    still have a non-empty profile (L1 alone is enough), but the test also
    verifies that expected semantic semes are present — catching any regression
    that silently zeroes the profile.
    """
    rings = _get_rings()
    expanded = rings.expanded

    # ghost must have a non-empty IDF profile
    assert len(expanded['ghost']) > 0, \
        "ghost has an empty IDF profile — expand() may be broken"

    # ghost's profile must contain at least one expected supernatural seme
    ghost_semes = set(expanded['ghost'].keys())
    expected_semes = {'soul', 'spirit', 'dead', 'apparition', 'supernatural'}
    found = ghost_semes & expected_semes
    assert found, (
        f"ghost profile contains none of {expected_semes}; "
        f"got: {sorted(ghost_semes)[:10]}"
    )

    # all 81 lemmas must have non-empty profiles
    empty = [l for l, profile in expanded.items() if len(profile) == 0]
    assert not empty, f"Lemmas with empty profiles: {empty}"

    # no lemma should have IDF scores of exactly 0.5 * anything
    # (a sign the dead L2 loop was re-introduced with the 0.5 weight)
    for lemma, profile in expanded.items():
        for seme, weight in profile.items():
            # L1 weights are math.log(N/c); for N=81 and c=1, log(81)≈4.39
            # The only way to get a suspiciously small weight near 0 is via
            # a 0.5× multiplier on a very low-IDF term. Flag anything < 0.5.
            assert weight >= 0.5, (
                f"Suspiciously low weight {weight:.4f} for seme '{seme}' "
                f"under lemma '{lemma}' — possible L2 residue"
            )


if __name__ == '__main__':
    test_no_dead_l2()
    print("test_no_dead_l2 PASSED")
