#!/usr/bin/env python3
"""
make_seme_bipartite.py
======================
Generate a Graphviz bipartite figure for a set of lexemes showing shared
and private semes.

Layout: lexeme nodes on the left (black), seme nodes on the right (gray).
Shared semes (appearing in ≥2 lexemes) get a dark border. Node size and
fill shade encode IDF weight. Edge width and label encode score.

Usage
-----
    python3 make_seme_bipartite.py \\
        --results  data/potocki_results.json \\
        --lemma    ghost hang gallows \\
        --top      10 \\
        --out-dir  figures/

Output
------
    <out_dir>/isotopy_seme_bipartite_<lemma1>_<lemma2>_....pdf
"""

import argparse
import json
import os
import sys

from graphviz import Digraph

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_LEMMAS  = ["ghost", "hang", "gallows"]
DEFAULT_TOP     = 10
DEFAULT_RESULTS = "potocki_results.json"
DEFAULT_OUT_DIR = "."
FONT            = "Open Sans Condensed"

LEMMA_NODE_SIZE = 0.9
SEME_SIZE_MIN   = 0.30
SEME_SIZE_MAX   = 0.70
EDGE_WIDTH_MIN  = 0.4
EDGE_WIDTH_MAX  = 2.4
DARK_FILL       = "#444444"
LIGHT_FILL      = "#cccccc"
DARK_EDGE       = "#555555"
LIGHT_EDGE      = "#cccccc"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def lerp_hex(score: float, lo: float, hi: float,
             dark: str = DARK_FILL, light: str = LIGHT_FILL) -> str:
    t = max(0.0, min(1.0, (score - lo) / (hi - lo) if hi > lo else 0.5))
    def ch(a: str, b: str) -> int:
        return int(int(a, 16) * (1 - t) + int(b, 16) * t)
    r = ch(light[1:3], dark[1:3])
    g = ch(light[3:5], dark[3:5])
    b = ch(light[5:7], dark[5:7])
    return f"#{r:02x}{g:02x}{b:02x}"


def lerp_float(score: float, lo: float, hi: float,
               vmin: float, vmax: float) -> float:
    t = max(0.0, min(1.0, (score - lo) / (hi - lo) if hi > lo else 0.5))
    return vmin + t * (vmax - vmin)


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

def make_bipartite(lemmas: list[str], lemma_tops: dict[str, dict],
                   out_path: str) -> None:

    # Build seme index: seme -> {lexeme: score}
    seme_index: dict[str, dict[str, float]] = {}
    for lemma, top in lemma_tops.items():
        for seme, score in top.items():
            seme_index.setdefault(seme, {})[lemma] = score

    # Global score range across all semes
    all_scores = [s for ls in seme_index.values() for s in ls.values()]
    glo, ghi = min(all_scores), max(all_scores)

    g = Digraph(
        "seme_bipartite",
        format="pdf",
        engine="dot",
        graph_attr={
            "bgcolor":  "white",
            "rankdir":  "LR",
            "pad":      "0.4",
            "nodesep":  "0.25",
            "ranksep":  "1.2",
            "fontname": FONT,
        },
        node_attr={"fontname": FONT},
        edge_attr={"fontname": FONT},
    )

    # Force lexemes to left rank, semes to right rank
    with g.subgraph() as left:
        left.attr(rank="same")
        for lemma in lemmas:
            left.node(
                f"lex_{lemma}",
                label=lemma,
                shape="circle",
                style="filled",
                fillcolor="#1a1a1a",
                fontcolor="white",
                fontsize="13",
                width=str(LEMMA_NODE_SIZE),
                fixedsize="true",
                penwidth="0",
            )

    with g.subgraph() as right:
        right.attr(rank="same")
        for seme, ls in seme_index.items():
            max_score = max(ls.values())
            is_shared = len(ls) > 1
            fill      = lerp_hex(max_score, glo, ghi)
            sz        = lerp_float(max_score, glo, ghi, SEME_SIZE_MIN, SEME_SIZE_MAX)
            fcolor    = "white" if max_score > glo + 0.5 * (ghi - glo) else "#1a1a1a"
            border_c  = "#1a1a1a" if is_shared else "none"
            border_w  = "1.2"    if is_shared else "0"
            right.node(
                f"sem_{seme}",
                label=seme,
                shape="circle",
                style="filled",
                fillcolor=fill,
                fontcolor=fcolor,
                fontsize="9",
                width=str(round(sz, 2)),
                fixedsize="true",
                color=border_c,
                penwidth=border_w,
            )

    # Edges: lexeme → seme
    for seme, ls in seme_index.items():
        for lemma, score in ls.items():
            pw = lerp_float(score, glo, ghi, EDGE_WIDTH_MIN, EDGE_WIDTH_MAX)
            ec = lerp_hex(score, glo, ghi, dark=DARK_EDGE, light=LIGHT_EDGE)
            g.edge(
                f"lex_{lemma}",
                f"sem_{seme}",
                penwidth=str(round(pw, 2)),
                color=ec,
                label=f"{score:.1f}",
                fontsize="7",
                fontcolor="#777777",
            )

    g.render(out_path, cleanup=True)
    print(f"  Saved {out_path}.pdf")

    # Report shared semes
    shared = {s: ls for s, ls in seme_index.items() if len(ls) > 1}
    print(f"  Shared semes ({len(shared)}):")
    for seme, ls in sorted(shared.items(), key=lambda x: -max(x[1].values())):
        print(f"    {seme:<16} " + "  ".join(f"{l}={s:.1f}" for l, s in ls.items()))
    if not shared:
        print("    (none in top-N)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--results", default=DEFAULT_RESULTS)
    parser.add_argument("--lemma",   nargs="+", default=DEFAULT_LEMMAS)
    parser.add_argument("--top",     type=int,  default=DEFAULT_TOP)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    if not os.path.exists(args.results):
        print(f"ERROR: {args.results} not found", file=sys.stderr)
        sys.exit(1)

    with open(args.results, encoding="utf-8") as fh:
        data = json.load(fh)

    expanded = data.get("expanded", {})
    os.makedirs(args.out_dir, exist_ok=True)

    lemma_tops: dict[str, dict] = {}
    missing = []
    for lemma in args.lemma:
        if lemma not in expanded:
            missing.append(lemma)
            continue
        lemma_tops[lemma] = dict(
            sorted(expanded[lemma].items(), key=lambda x: -x[1])[:args.top]
        )

    if missing:
        print(f"WARNING: not found in results: {missing}", file=sys.stderr)

    if len(lemma_tops) < 2:
        print("ERROR: need at least 2 lexemes for a bipartite figure", file=sys.stderr)
        sys.exit(1)

    tag      = "_".join(args.lemma)
    out_path = os.path.join(args.out_dir, f"isotopy_seme_bipartite_{tag}")
    print(f"\nBipartite figure: {' + '.join(lemma_tops.keys())}")
    make_bipartite(list(lemma_tops.keys()), lemma_tops, out_path)
    print("Done.")


if __name__ == "__main__":
    main()
