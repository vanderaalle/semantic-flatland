"""
isotopy_bipartite_graph.py
==========================
Bipartite Graphviz visualisation of the full lemma-seme IDF-weighted similarity
structure for the Potocki and Poe passages.

Each passage produces a two-panel figure:

  Panel A (left, ~65 % width) — full bipartite graph
    Lemma nodes : filled black (#1a1a1a), white label, circle
    Seme nodes  : filled gray, shade proportional to max IDF weight; NO labels
    Edges       : gray, penwidth and colour proportional to IDF score;
                  drawn only when score > p25 of all edge scores
    Layout      : sfdp, K=1.5, maxiter=1000 (scalable multiscale)

  Panel B (right, ~35 % width) — zoomed inset (thematic subgraph)
    Contains only a curated set of lemmas and their seme neighbours above p25
    All labels shown (lemma + seme); seme node size proportional to IDF weight
    Layout      : fdp, K=1.5, maxiter=500 (manageable at small scale)

Note on graph size
------------------
After the p25 edge threshold, ~97 % of semes connect to only one lemma (hapax
semes). These are visible as small satellite dots around each lemma node but
carry no cross-lemma isotopic information. Semes shared by ≥ 2 lemmas are the
structural isotopy markers.

Output
------
  projects/isotopy/figures/isotopy_bipartite_potocki_panel.pdf
  projects/isotopy/figures/isotopy_bipartite_poe_panel.pdf
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from collections import Counter

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from graphviz import Graph

# ---------------------------------------------------------------------------
# Sentinels
# ---------------------------------------------------------------------------
INPUT_POTOCKI = ""
INPUT_POE     = ""
OUTPUT_DIR    = ""

# ---------------------------------------------------------------------------
# Resolve defaults
# ---------------------------------------------------------------------------
_HERE      = os.path.dirname(os.path.abspath(__file__))
# script lives at projects/isotopy/code/ → repo root is three levels up
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))

_DATA_DIR  = os.path.normpath(os.path.join(_HERE, "..", "data"))
_OUT_DIR   = os.path.normpath(os.path.join(_HERE, "..", "figures"))
_STYLE_DIR = os.path.join(_REPO_ROOT, "brainstorming", "assets")

sys.path.insert(0, _STYLE_DIR)
from style import PlotStyle  # noqa: E402

def _resolve(sentinel: str, default: str) -> str:
    return sentinel if sentinel else default


# ---------------------------------------------------------------------------
# Passage-specific inset lemma sets
# ---------------------------------------------------------------------------
INSET_LEMMAS: dict[str, list[str]] = {
    "potocki": [
        "gallows", "hang", "corpse", "ghost", "body",
        "break", "flesh", "demon", "vampire", "heaven", "living",
    ],
    "poe": [
        "soul", "spirit", "heart", "life", "sense",
        "decay", "mind", "sentiment", "feeling", "sensation",
    ],
}


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _lerp_hex(t: float, dark: str, light: str) -> str:
    """Linear interpolation between two hex colours; t=0 → dark, t=1 → light."""
    def _parse(h: str) -> tuple[int, int, int]:
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    r0, g0, b0 = _parse(dark)
    r1, g1, b1 = _parse(light)
    r = int(r0 + t * (r1 - r0))
    g = int(g0 + t * (g1 - g0))
    b = int(b0 + t * (b1 - b0))
    return f"#{r:02x}{g:02x}{b:02x}"


# ---------------------------------------------------------------------------
# Shared data preparation
# ---------------------------------------------------------------------------

def _prepare(data: dict) -> dict:
    """Extract and annotate all edge/seme statistics from the results JSON."""
    expanded: dict[str, dict[str, float]] = {
        k: v for k, v in data["expanded"].items() if v
    }

    all_edge_scores = [s for v in expanded.values() for s in v.values()]
    edge_arr  = np.array(all_edge_scores)
    edge_p25  = float(np.percentile(edge_arr, 25))
    edge_max  = float(edge_arr.max())
    edge_min  = float(edge_arr.min())

    seme_max_idf: dict[str, float] = {}
    for seme_dict in expanded.values():
        for seme, score in seme_dict.items():
            if seme not in seme_max_idf or score > seme_max_idf[seme]:
                seme_max_idf[seme] = score

    seme_arr        = np.array(list(seme_max_idf.values()))
    seme_global_max = float(seme_arr.max())
    seme_global_min = float(seme_arr.min())

    return dict(
        expanded        = expanded,
        edge_p25        = edge_p25,
        edge_max        = edge_max,
        edge_min        = edge_min,
        seme_max_idf    = seme_max_idf,
        seme_global_max = seme_global_max,
        seme_global_min = seme_global_min,
    )


def _seme_fillcolor(max_idf: float, seme_global_min: float, seme_global_max: float) -> str:
    span = seme_global_max - seme_global_min
    t    = (max_idf - seme_global_min) / span if span > 0 else 0.5
    return _lerp_hex(1.0 - t, "#444444", "#cccccc")


def _edge_color(score: float, edge_min: float, edge_max: float) -> str:
    span = edge_max - edge_min
    t    = (score - edge_min) / span if span > 0 else 0.5
    return _lerp_hex(1.0 - t, "#444444", "#dddddd")


def _edge_penwidth(score: float, edge_min: float, edge_max: float) -> str:
    span = edge_max - edge_min
    t    = (score - edge_min) / span if span > 0 else 0.5
    return f"{0.3 + t * 2.7:.2f}"


# ---------------------------------------------------------------------------
# Panel A — full graph, seme labels suppressed
# ---------------------------------------------------------------------------

def build_panel_a(prep: dict, title: str) -> Graph:
    """Full bipartite graph; seme nodes visible but unlabeled."""
    expanded        = prep["expanded"]
    edge_p25        = prep["edge_p25"]
    edge_min        = prep["edge_min"]
    edge_max        = prep["edge_max"]
    seme_max_idf    = prep["seme_max_idf"]
    seme_global_min = prep["seme_global_min"]
    seme_global_max = prep["seme_global_max"]

    g = Graph(
        name=title,
        engine="sfdp",
        format="png",
        graph_attr={
            "overlap": "false",
            "splines": "line",
            "bgcolor": "white",
            "K": "1.5",
            "maxiter": "1000",
        },
        node_attr={"fixedsize": "false"},
    )

    for lemma in sorted(expanded.keys()):
        g.node(
            f"L_{lemma}",
            label=lemma,
            shape="circle",
            style="filled",
            fillcolor="#1a1a1a",
            fontcolor="white",
            fontsize="7",
            width="0.45",
        )

    active_semes: set[str] = set()
    active_edges: list[tuple[str, str, float]] = []
    for lemma, seme_dict in expanded.items():
        for seme, score in seme_dict.items():
            if score > edge_p25:
                active_semes.add(seme)
                active_edges.append((lemma, seme, score))

    for seme in sorted(active_semes):
        fill = _seme_fillcolor(seme_max_idf[seme], seme_global_min, seme_global_max)
        # Label suppressed: set label="" and fontcolor matching fill so nothing shows
        g.node(
            f"S_{seme}",
            label="",
            shape="circle",
            style="filled",
            fillcolor=fill,
            fontcolor=fill,
            fontsize="6",
            width="0.22",
        )

    for lemma, seme, score in active_edges:
        g.edge(
            f"L_{lemma}",
            f"S_{seme}",
            color=_edge_color(score, edge_min, edge_max),
            penwidth=_edge_penwidth(score, edge_min, edge_max),
        )

    return g


# ---------------------------------------------------------------------------
# Panel B — inset subgraph, all labels, seme size ∝ IDF
# ---------------------------------------------------------------------------

def build_panel_b(prep: dict, inset_lemmas: list[str], title: str) -> tuple[Graph, list[str]]:
    """
    Subgraph over `inset_lemmas` and their seme neighbours above p25.
    Returns (Graph, list_of_missing_lemmas) where missing = inset lemmas
    not found in expanded (spelling mismatches to report).
    """
    expanded        = prep["expanded"]
    edge_p25        = prep["edge_p25"]
    edge_min        = prep["edge_min"]
    edge_max        = prep["edge_max"]
    seme_max_idf    = prep["seme_max_idf"]
    seme_global_min = prep["seme_global_min"]
    seme_global_max = prep["seme_global_max"]

    # Resolve lemma keys (case-insensitive match to handle capitalisation)
    key_map = {k.lower(): k for k in expanded}
    resolved: list[str] = []
    missing:  list[str] = []
    for lem in inset_lemmas:
        if lem in expanded:
            resolved.append(lem)
        elif lem.lower() in key_map:
            resolved.append(key_map[lem.lower()])
        else:
            missing.append(lem)

    # Collect subgraph edges
    sub_edges: list[tuple[str, str, float]] = []
    sub_semes: set[str] = set()
    for lemma in resolved:
        for seme, score in expanded[lemma].items():
            if score > edge_p25:
                sub_semes.add(seme)
                sub_edges.append((lemma, seme, score))

    g = Graph(
        name=title,
        engine="fdp",
        format="png",
        graph_attr={
            "overlap": "false",
            "splines": "line",
            "bgcolor": "white",
            "K": "1.5",
            "maxiter": "500",
        },
        node_attr={"fixedsize": "false"},
    )

    for lemma in resolved:
        g.node(
            f"L_{lemma}",
            label=lemma,
            shape="circle",
            style="filled",
            fillcolor="#1a1a1a",
            fontcolor="white",
            fontsize="9",
            width="0.55",
        )

    # Label threshold: only show labels for top 25% of inset semes by IDF.
    # At fixedsize=true / width=0.30", labels overflow the circle for long words;
    # restricting to the top quartile keeps only the most discriminating semes
    # and significantly reduces the number of overflowing labels.
    inset_idf_values = [seme_max_idf.get(s, seme_global_min) for s in sub_semes]
    idf_p75 = float(np.percentile(inset_idf_values, 75)) if inset_idf_values else seme_global_min

    for seme in sorted(sub_semes):
        max_idf = seme_max_idf.get(seme, seme_global_min)
        fill    = _seme_fillcolor(max_idf, seme_global_min, seme_global_max)
        span    = seme_global_max - seme_global_min
        t       = (max_idf - seme_global_min) / span if span > 0 else 0.5
        fc      = "white" if t > 0.6 else "#1a1a1a"
        # Only label semes in the top 25% by IDF among inset semes
        label   = seme if max_idf >= idf_p75 else ""
        g.node(
            f"S_{seme}",
            label=label,
            shape="circle",
            style="filled",
            fillcolor=fill,
            fontcolor=fc,
            fontsize="6",
            width="0.30",
            height="0.30",
            fixedsize="true",
        )

    for lemma, seme, score in sub_edges:
        g.edge(
            f"L_{lemma}",
            f"S_{seme}",
            color=_edge_color(score, edge_min, edge_max),
            penwidth=_edge_penwidth(score, edge_min, edge_max),
        )

    return g, missing


# ---------------------------------------------------------------------------
# Compose two-panel figure with matplotlib
# ---------------------------------------------------------------------------

def compose_panels(
    g_a: Graph,
    g_b: Graph,
    out_path: str,
    dpi: int = 300,
) -> None:
    """Render both Graphviz graphs to PNG, compose side-by-side, save PDF."""
    ps = PlotStyle.book_grayscale()
    ps.apply()
    plt.rcParams["svg.fonttype"] = "path"

    with tempfile.TemporaryDirectory() as tmpdir:
        path_a = os.path.join(tmpdir, "panel_a")
        path_b = os.path.join(tmpdir, "panel_b")

        # Render at high DPI for crisp embedding
        g_a.graph_attr["dpi"] = str(dpi)
        g_b.graph_attr["dpi"] = str(dpi)

        g_a.render(filename=path_a, cleanup=True)
        g_b.render(filename=path_b, cleanup=True)

        img_a = mpimg.imread(path_a + ".png")
        img_b = mpimg.imread(path_b + ".png")

    # Full text-width figure; height set to accommodate the taller panel
    w_total = ps.geometry.width_double    # 7.0 inches
    # Estimate height from aspect ratios
    h_a = img_a.shape[0] / img_a.shape[1] * (w_total * 0.65)
    h_b = img_b.shape[0] / img_b.shape[1] * (w_total * 0.35)
    fig_h = max(h_a, h_b)
    fig_h = max(fig_h, 3.0)  # minimum height

    fig = plt.figure(figsize=(w_total, fig_h), facecolor="white")

    # Panel A — left 65%
    ax_a = fig.add_axes([0.00, 0.0, 0.63, 1.0])
    ax_a.imshow(img_a, aspect="equal", interpolation="lanczos")
    ax_a.axis("off")
    ax_a.set_title("A", loc="left", fontsize=9, fontweight="bold", pad=4)

    # Panel B — right 35%
    ax_b = fig.add_axes([0.65, 0.0, 0.35, 1.0])
    ax_b.imshow(img_b, aspect="equal", interpolation="lanczos")
    ax_b.axis("off")
    ax_b.set_title("B", loc="left", fontsize=9, fontweight="bold", pad=4)

    fig.savefig(out_path, dpi=dpi, bbox_inches="tight",
                pad_inches=ps.geometry.pad_inches, facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Stats helper
# ---------------------------------------------------------------------------

def _compute_stats(prep: dict) -> dict:
    expanded = prep["expanded"]
    edge_p25 = prep["edge_p25"]

    active_semes: set[str] = set()
    active_edges: list[tuple[str, str, float]] = []
    for lemma, seme_dict in expanded.items():
        for seme, score in seme_dict.items():
            if score > edge_p25:
                active_semes.add(seme)
                active_edges.append((lemma, seme, score))

    deg_post: Counter[str] = Counter()
    for _, seme, _ in active_edges:
        deg_post[seme] += 1

    deg_pre: Counter[str] = Counter()
    for seme_dict in expanded.values():
        for seme in seme_dict:
            deg_pre[seme] += 1

    return {
        "n_lemmas"       : len(expanded),
        "n_semes"        : len(active_semes),
        "total_nodes"    : len(expanded) + len(active_semes),
        "total_edges"    : len(active_edges),
        "edge_p25"       : edge_p25,
        "hubs_graph"     : sorted([(s, c) for s, c in deg_post.items() if c > 10], key=lambda x: -x[1]),
        "hubs_raw"       : sorted([(s, c) for s, c in deg_pre.items()  if c > 10], key=lambda x: -x[1]),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    input_potocki = _resolve(INPUT_POTOCKI, os.path.join(_DATA_DIR, "potocki_results.json"))
    input_poe     = _resolve(INPUT_POE,     os.path.join(_DATA_DIR, "poe_results.json"))
    output_dir    = _resolve(OUTPUT_DIR,    _OUT_DIR)

    os.makedirs(output_dir, exist_ok=True)

    passages = [
        ("Potocki", input_potocki, "potocki", "isotopy_bipartite_potocki_panel"),
        ("Poe",     input_poe,     "poe",     "isotopy_bipartite_poe_panel"),
    ]

    for label, input_path, key, out_stem in passages:
        print(f"\n── {label} ──────────────────────────────")
        with open(input_path, encoding="utf-8") as fh:
            data = json.load(fh)

        prep  = _prepare(data)
        stats = _compute_stats(prep)

        print(f"  Lemma nodes : {stats['n_lemmas']}")
        print(f"  Seme nodes  : {stats['n_semes']}  (edge p25={stats['edge_p25']:.3f})")
        print(f"  Total nodes : {stats['total_nodes']}")
        print(f"  Total edges : {stats['total_edges']}")
        if stats["hubs_graph"]:
            print(f"  Hubs in graph (post-p25, >10 lemmas): {stats['hubs_graph']}")
        else:
            print("  Hubs in graph (post-p25, >10 lemmas): none")
        if stats["hubs_raw"]:
            print(f"  Hubs raw (>10 lemmas, semantic commonplaces): {stats['hubs_raw']}")

        inset_lemmas = INSET_LEMMAS[key]
        print(f"  Inset lemmas requested: {inset_lemmas}")

        g_a = build_panel_a(prep, f"{out_stem}_A")
        g_b, missing = build_panel_b(prep, inset_lemmas, f"{out_stem}_B")

        if missing:
            print(f"  WARNING — inset lemmas not found in data: {missing}")

        out_path = os.path.join(output_dir, out_stem + ".pdf")
        compose_panels(g_a, g_b, out_path)
        print(f"  Output: {out_path}")

        # Inset label overlap check: report semes in inset with short labels
        # that share >1 lemma neighbour (potential overlap cluster)
        inset_prep = _prepare(data)
        key_map    = {k.lower(): k for k in inset_prep["expanded"]}
        resolved   = [
            inset_prep["expanded"].get(lem) and lem
            or key_map.get(lem.lower())
            for lem in inset_lemmas
            if lem in inset_prep["expanded"] or lem.lower() in key_map
        ]
        shared_semes: Counter[str] = Counter()
        for lem in resolved:
            if lem and lem in inset_prep["expanded"]:
                for seme, score in inset_prep["expanded"][lem].items():
                    if score > inset_prep["edge_p25"]:
                        shared_semes[seme] += 1
        multi = sorted([(s, c) for s, c in shared_semes.items() if c >= 2], key=lambda x: -x[1])
        if multi:
            print(f"  Inset shared semes (≥2 lemmas, potential label overlap): {multi[:15]}")
        else:
            print("  Inset: no shared semes — all seme labels satellite (no overlap clusters)")


if __name__ == "__main__":
    main()
