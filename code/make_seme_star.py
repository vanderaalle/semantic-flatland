#!/usr/bin/env python3
"""
make_seme_star.py
=================
Generate seme star figures and/or a connected bipartite graph for a set of
lemmas from a pipeline results JSON.

For each lemma, a star graph shows:
  - Central black node: the lemma
  - Radiating gray nodes: top-N IDF-weighted seme words
  - Node size and fill shade encode seme score (larger/darker = higher)
  - Edge weight and label show the weighted score

The connected graph merges seme nodes shared across lemmas into a single node,
making bridge semes -- and therefore isotopy edges -- visually explicit. Shared
seme nodes are given a dark border to distinguish them from private semes.

Usage
-----
    # Individual star graphs only:
    python3 make_seme_star.py \\
        --results  data/potocki_results.json \\
        --lemma    ghost hang gallows \\
        --top      10 \\
        --out-dir  figures/

    # Also produce the connected bipartite graph:
    python3 make_seme_star.py \\
        --results   data/potocki_results.json \\
        --lemma     ghost hang gallows \\
        --top       10 \\
        --connected \\
        --out-dir   figures/

Output
------
    <out_dir>/isotopy_seme_star_<lemma>.pdf      -- one per lemma
    <out_dir>/isotopy_seme_connected_<...>.pdf   -- if --connected
"""

import argparse
import json
import os
import sys

from graphviz import Graph

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_LEMMAS  = ["ghost"]
DEFAULT_TOP     = 10
DEFAULT_RESULTS = "potocki_results.json"
DEFAULT_OUT_DIR = "."
FONT            = "Open Sans Condensed"

# Visual constants
LEMMA_NODE_SIZE = 0.9
SEME_SIZE_MIN   = 0.32
SEME_SIZE_MAX   = 0.75
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
# Star graph
# ---------------------------------------------------------------------------

def make_star(lemma: str, profile: dict, idf: dict,
              top_n: int, out_path: str) -> list:
    if not profile:
        print(f"  WARNING: no seme profile for '{lemma}' -- skipping")
        return []

    top = sorted(profile.items(), key=lambda x: -x[1])[:top_n]
    lo, hi = top[-1][1], top[0][1]

    g = Graph(f"{lemma}_semes", format="pdf", engine="neato",
        graph_attr={"bgcolor": "white", "pad": "0.4", "overlap": "false",
                    "sep": "+14", "fontname": FONT},
        node_attr={"fontname": FONT}, edge_attr={"fontname": FONT})

    g.node(lemma, label=lemma, shape="circle", style="filled",
           fillcolor="#1a1a1a", fontcolor="white", fontsize="13",
           width=str(LEMMA_NODE_SIZE), fixedsize="true", penwidth="0")

    for seme, score in top:
        fill   = lerp_hex(score, lo, hi)
        sz     = lerp_float(score, lo, hi, SEME_SIZE_MIN, SEME_SIZE_MAX)
        pw     = lerp_float(score, lo, hi, EDGE_WIDTH_MIN, EDGE_WIDTH_MAX)
        ec     = lerp_hex(score, lo, hi, dark=DARK_EDGE, light=LIGHT_EDGE)
        fcolor = "white" if score > lo + 0.5 * (hi - lo) else "#1a1a1a"
        g.node(f"s_{seme}", label=seme, shape="circle", style="filled",
               fillcolor=fill, fontcolor=fcolor, fontsize="9",
               width=str(round(sz, 2)), fixedsize="true", penwidth="0")
        g.edge(lemma, f"s_{seme}", penwidth=str(round(pw, 2)), color=ec,
               label=f"{score:.1f}", fontsize="7", fontcolor="#777777")

    g.render(out_path, cleanup=True)
    print(f"  Saved {out_path}.pdf")

    raw_idf = lambda w: idf.get(w)
    for seme, score in top:
        v = raw_idf(seme)
        reps = round(score / v) if v else "?"
        print(f"    {seme:<16} score={score:.2f}  "
              f"IDF={(f'{v:.2f}' if v is not None else '?')}  (x{reps} across senses)")

    return top


# ---------------------------------------------------------------------------
# Connected bipartite graph
# ---------------------------------------------------------------------------

def make_connected(lemmas: list, lemma_tops: dict,
                   out_path: str) -> None:
    all_scores = [s for top in lemma_tops.values() for _, s in top]
    glo, ghi   = min(all_scores), max(all_scores)

    # Build seme → {lemma: score} index
    seme_index: dict[str, dict[str, float]] = {}
    for lemma, top in lemma_tops.items():
        for seme, score in top:
            seme_index.setdefault(seme, {})[lemma] = score

    g = Graph("connected", format="pdf", engine="neato",
        graph_attr={"bgcolor": "white", "pad": "0.5", "overlap": "false",
                    "sep": "+16", "fontname": FONT},
        node_attr={"fontname": FONT}, edge_attr={"fontname": FONT})

    # Lemma nodes
    for lemma in lemmas:
        g.node(lemma, label=lemma, shape="circle", style="filled",
               fillcolor="#1a1a1a", fontcolor="white", fontsize="13",
               width=str(LEMMA_NODE_SIZE), fixedsize="true", penwidth="0")

    # Seme nodes -- shared semes get a dark border
    for seme, ls in seme_index.items():
        max_score  = max(ls.values())
        is_shared  = len(ls) > 1
        fill       = lerp_hex(max_score, glo, ghi)
        sz         = lerp_float(max_score, glo, ghi, SEME_SIZE_MIN, SEME_SIZE_MAX)
        fcolor     = "white" if max_score > glo + 0.5*(ghi-glo) else "#1a1a1a"
        border_c   = "#1a1a1a" if is_shared else "none"
        border_w   = "1.2"    if is_shared else "0"
        g.node(f"s_{seme}", label=seme, shape="circle", style="filled",
               fillcolor=fill, fontcolor=fcolor, fontsize="9",
               width=str(round(sz, 2)), fixedsize="true",
               color=border_c, penwidth=border_w)

        for lemma, score in ls.items():
            pw = lerp_float(score, glo, ghi, EDGE_WIDTH_MIN, EDGE_WIDTH_MAX)
            ec = lerp_hex(score, glo, ghi, dark=DARK_EDGE, light=LIGHT_EDGE)
            g.edge(lemma, f"s_{seme}", penwidth=str(round(pw, 2)), color=ec,
                   label=f"{score:.1f}", fontsize="7", fontcolor="#777777")

    g.render(out_path, cleanup=True)
    print(f"  Saved {out_path}.pdf")

    # Report shared semes
    shared = {s: ls for s, ls in seme_index.items() if len(ls) > 1}
    if shared:
        print(f"  Shared semes ({len(shared)}):")
        for seme, ls in sorted(shared.items(),
                                key=lambda x: -max(x[1].values())):
            print(f"    {seme:<16} " +
                  "  ".join(f"{l}={s:.1f}" for l, s in ls.items()))
    else:
        print("  No shared semes in top-N for these lemmas.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--results",   default=DEFAULT_RESULTS)
    parser.add_argument("--lemma",     nargs="+", default=DEFAULT_LEMMAS)
    parser.add_argument("--top",       type=int, default=DEFAULT_TOP)
    parser.add_argument("--connected", action="store_true",
                        help="Also produce a connected bipartite graph")
    parser.add_argument("--out-dir",   default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    if not os.path.exists(args.results):
        print(f"ERROR: {args.results} not found", file=sys.stderr)
        sys.exit(1)

    with open(args.results, encoding="utf-8") as fh:
        data = json.load(fh)

    expanded = data.get("expanded", {})
    idf      = data.get("idf", {})
    os.makedirs(args.out_dir, exist_ok=True)

    lemma_tops: dict[str, list] = {}
    for lemma in args.lemma:
        if lemma not in expanded:
            print(f"  WARNING: '{lemma}' not in results -- skipping")
            continue
        print(f"\n{lemma.upper()}")
        out_path = os.path.join(args.out_dir, f"isotopy_seme_star_{lemma}")
        top = make_star(lemma, expanded[lemma], idf, args.top, out_path)
        lemma_tops[lemma] = top

    if args.connected and len(lemma_tops) > 1:
        lemma_list = [l for l in args.lemma if l in lemma_tops]
        tag = "_".join(lemma_list)
        out_path = os.path.join(args.out_dir, f"isotopy_seme_connected_{tag}")
        print(f"\nCONNECTED GRAPH: {' + '.join(lemma_list)}")
        make_connected(lemma_list, lemma_tops, out_path)

    print("\nDone.")


if __name__ == "__main__":
    main()
