#!/usr/bin/env python3
"""
experiment_tautology_context.py
================================
Compares pipeline output with tautology_in_context=False (default) vs True.

Checks:
  1. Baseline numbers match verified ground truth
  2. Edge counts, power-law slopes for both flag values / both passages
  3. Changes in the ten representative Potocki pairs and ten Poe pairs
  4. Number of lemmas whose Lesk context size (pass-1 seme count) changed
  5. Specific pairs: gallows–hang, body–ghost

Run from projects/isotopy/code/:
    python3 experiment_tautology_context.py
"""

import json
import math
import sys
import os
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import isotopy as iso

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.normpath(os.path.join(_HERE, "..", "data"))

POTOCKI = dict(
    path_wk    = os.path.join(_DATA, "potocki_definitions_wikt.json"),
    path_wn    = os.path.join(_DATA, "potocki_definitions_wn.json"),
    path_mw    = os.path.join(_DATA, "potocki_definitions_mw.json"),
    path_w1828 = os.path.join(_DATA, "potocki_definitions_w1828.json"),
)
POE = dict(
    path_wk    = os.path.join(_DATA, "poe_definitions_wikt.json"),
    path_wn    = os.path.join(_DATA, "poe_definitions_wn.json"),
    path_mw    = os.path.join(_DATA, "poe_definitions_mw.json"),
    path_w1828 = os.path.join(_DATA, "poe_definitions_w1828.json"),
)

# ---------------------------------------------------------------------------
# Representative pairs (same sets used in make_comparison_svg.py)
# ---------------------------------------------------------------------------
POTOCKI_PAIRS = [
    ("gallows", "hang"),
    ("body",    "ghost"),
    ("corpse",  "ghost"),
    ("demon",   "vampire"),
    ("heaven",  "demon"),
    ("gallows", "corpse"),
    ("flesh",   "body"),
    ("ghost",   "vampire"),
    ("living",  "corpse"),
    ("break",   "gallows"),
]
POE_PAIRS = [
    ("soul",    "spirit"),
    ("heart",   "life"),
    ("feeling", "sensation"),
    ("sense",   "mind"),
    ("decay",   "soul"),
    ("spirit",  "mind"),
    ("sentiment","feeling"),
    ("life",    "decay"),
    ("heart",   "spirit"),
    ("sense",   "sensation"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
T_STRONG = iso.T_STRONG
T_MEDIUM = iso.T_MEDIUM
T_WEAK   = iso.T_WEAK


def power_law_slope(raw_edges: dict) -> tuple[float, float]:
    """Fit log(score) ~ slope*log(rank); return (slope, R²)."""
    scores = sorted(raw_edges.values(), reverse=True)
    n = len(scores)
    log_r = [math.log(i + 1) for i in range(n)]
    log_s = [math.log(s)     for s in scores]
    xm = sum(log_r) / n
    ym = sum(log_s) / n
    ss_xy = sum((x - xm) * (y - ym) for x, y in zip(log_r, log_s))
    ss_xx = sum((x - xm) ** 2        for x in log_r)
    slope = ss_xy / ss_xx if ss_xx else 0.0
    y_pred = [ym + slope * (x - xm) for x in log_r]
    ss_res = sum((y - p) ** 2 for y, p in zip(log_s, y_pred))
    ss_tot = sum((y - ym) ** 2 for y in log_s)
    r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
    return slope, r2


def tier_label(raw_edges: dict, l1: str, l2: str) -> str:
    """Return STRONG / MEDIUM / WEAK / sub-weak / — for a pair."""
    key   = (l1, l2) if (l1, l2) in raw_edges else (l2, l1)
    score = raw_edges.get(key, 0.0)
    if score == 0.0:
        return "—"
    if score >= T_STRONG:
        return f"STRONG  ({score:.2f})"
    if score >= T_MEDIUM:
        return f"MEDIUM  ({score:.2f})"
    if score >= T_WEAK:
        return f"WEAK    ({score:.2f})"
    return f"sub-weak ({score:.2f})"


def run_one(passage_paths: dict, flag: bool, label: str) -> tuple[dict, dict]:
    """Run pipeline, return (raw_edges, context_sizes_per_lemma)."""
    print(f"  [{label}] tautology_in_context={flag} ...", end=" ", flush=True)

    # We need pass-1 context sizes — instrument build_rings_from_dicts manually
    import json as _json
    with open(passage_paths["path_wk"])    as f: wk    = _json.load(f)
    with open(passage_paths["path_wn"])    as f: wn    = _json.load(f)
    with open(passage_paths["path_mw"])    as f: mw    = _json.load(f)
    with open(passage_paths["path_w1828"]) as f: w1828 = _json.load(f)

    rings = iso.build_rings_from_dicts(
        wk=wk, wn=wn, mw=mw, w1828=w1828,
        verbose=False,
        tautology_in_context=flag,
    )

    # Context sizes: number of distinct semes each lemma contributed to pass-1
    # We can proxy this with len(rings.lemma_words[l]) since pass-2 keeps the
    # same filter (any reduction from the gate is visible there).
    ctx_sizes = {l: len(rings.lemma_words[l]) for l in rings.lemmas}

    n = len(rings.raw_edges)
    slope, r2 = power_law_slope(rings.raw_edges)
    print(f"{n} edges  slope={slope:.4f}  R²={r2:.4f}")
    return rings.raw_edges, ctx_sizes


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 72)
    print("  EXPERIMENT: tautology gate in pass-1 context building")
    print("=" * 72)

    # ── 1. Run all four combinations ──────────────────────────────────────
    print("\n── Potocki ──")
    pot_f, pot_ctx_f = run_one(POTOCKI, False, "Potocki")
    pot_t, pot_ctx_t = run_one(POTOCKI, True,  "Potocki")

    print("\n── Poe ──")
    poe_f, poe_ctx_f = run_one(POE, False, "Poe")
    poe_t, poe_ctx_t = run_one(POE, True,  "Poe")

    # ── 2. Baseline verification ──────────────────────────────────────────
    print("\n── Baseline verification (False == verified ground truth) ──")
    pot_n_f = len(pot_f); pot_sl_f, pot_r2_f = power_law_slope(pot_f)
    poe_n_f = len(poe_f); poe_sl_f, poe_r2_f = power_law_slope(poe_f)

    ok_pot = (pot_n_f == 943 and abs(pot_sl_f - (-0.5154)) < 0.002)
    ok_poe = (poe_n_f == 1613 and abs(poe_sl_f - (-0.5340)) < 0.002)

    print(f"  Potocki: edges={pot_n_f}, slope={pot_sl_f:.4f}  {'✓' if ok_pot else '✗ MISMATCH'}")
    print(f"  Poe:     edges={poe_n_f}, slope={poe_sl_f:.4f}  {'✓' if ok_poe else '✗ MISMATCH'}")
    if not (ok_pot and ok_poe):
        print("  ERROR: baseline mismatch — aborting experiment.")
        sys.exit(1)

    # ── 3. Metrics table ──────────────────────────────────────────────────
    pot_n_t = len(pot_t); pot_sl_t, pot_r2_t = power_law_slope(pot_t)
    poe_n_t = len(poe_t); poe_sl_t, poe_r2_t = power_law_slope(poe_t)

    print("\n── Metrics ──────────────────────────────────────────────────────")
    print(f"{'':20s}  {'edges':>7}  {'slope':>8}  {'R²':>7}")
    print(f"  {'Potocki  False':20s}  {pot_n_f:>7}  {pot_sl_f:>8.4f}  {pot_r2_f:>7.4f}")
    print(f"  {'Potocki  True':20s}  {pot_n_t:>7}  {pot_sl_t:>8.4f}  {pot_r2_t:>7.4f}")
    print(f"  {'Poe      False':20s}  {poe_n_f:>7}  {poe_sl_f:>8.4f}  {poe_r2_f:>7.4f}")
    print(f"  {'Poe      True':20s}  {poe_n_t:>7}  {poe_sl_t:>8.4f}  {poe_r2_t:>7.4f}")

    # ── 4. Potocki representative pairs ───────────────────────────────────
    print("\n── Potocki representative pairs ─────────────────────────────────")
    print(f"  {'Pair':<22}  {'False':>22}  {'True':>22}  {'Δ'}")
    print("  " + "─" * 76)
    any_change_pot = False
    for l1, l2 in POTOCKI_PAIRS:
        tf = tier_label(pot_f, l1, l2)
        tt = tier_label(pot_t, l1, l2)
        changed = tf != tt
        if changed:
            any_change_pot = True
        marker = " ◀" if changed else ""
        print(f"  {l1}–{l2:<17}  {tf:>22}  {tt:>22}{marker}")

    # ── 5. Poe representative pairs ───────────────────────────────────────
    print("\n── Poe representative pairs ─────────────────────────────────────")
    print(f"  {'Pair':<24}  {'False':>22}  {'True':>22}  {'Δ'}")
    print("  " + "─" * 78)
    any_change_poe = False
    for l1, l2 in POE_PAIRS:
        tf = tier_label(poe_f, l1, l2)
        tt = tier_label(poe_t, l1, l2)
        changed = tf != tt
        if changed:
            any_change_poe = True
        marker = " ◀" if changed else ""
        print(f"  {l1}–{l2:<19}  {tf:>22}  {tt:>22}{marker}")

    # ── 6. Context-size changes ───────────────────────────────────────────
    print("\n── Context size changes (lemma_words count, Potocki) ────────────")
    changed_ctx_pot = {
        l: (pot_ctx_f[l], pot_ctx_t[l])
        for l in pot_ctx_f
        if pot_ctx_f[l] != pot_ctx_t[l]
    }
    if changed_ctx_pot:
        print(f"  {len(changed_ctx_pot)} / {len(pot_ctx_f)} lemmas changed:")
        for l, (old, new) in sorted(changed_ctx_pot.items(), key=lambda x: -(x[1][0]-x[1][1])):
            print(f"    {l:<20} {old:>3} → {new:>3}  (Δ {new-old:+d})")
    else:
        print("  0 lemmas changed (context identical).")

    print("\n── Context size changes (lemma_words count, Poe) ───────────────")
    changed_ctx_poe = {
        l: (poe_ctx_f[l], poe_ctx_t[l])
        for l in poe_ctx_f
        if poe_ctx_f[l] != poe_ctx_t[l]
    }
    if changed_ctx_poe:
        print(f"  {len(changed_ctx_poe)} / {len(poe_ctx_f)} lemmas changed:")
        for l, (old, new) in sorted(changed_ctx_poe.items(), key=lambda x: -(x[1][0]-x[1][1])):
            print(f"    {l:<20} {old:>3} → {new:>3}  (Δ {new-old:+d})")
    else:
        print("  0 lemmas changed (context identical).")

    # ── 7. Verdict ────────────────────────────────────────────────────────
    any_edge_change = (pot_n_f != pot_n_t or poe_n_f != poe_n_t)
    any_pair_change = any_change_pot or any_change_poe
    any_ctx_change  = bool(changed_ctx_pot or changed_ctx_poe)

    print("\n── Verdict ──────────────────────────────────────────────────────")
    if not any_edge_change and not any_pair_change and not any_ctx_change:
        print("  NEUTRAL — no measurable change. Keep tautology_in_context=False.")
    elif any_pair_change:
        # Determine if changes are improvements or regressions
        print("  CHANGES DETECTED in representative pairs — manual review required.")
        print("  Review ◀ rows above to classify as improvement or regression.")
    elif any_edge_change or any_ctx_change:
        print("  MINOR changes (edge count / context sizes) but no pair-level changes.")
        print("  Effectively NEUTRAL for the paper's results.")
    print()


if __name__ == "__main__":
    main()
