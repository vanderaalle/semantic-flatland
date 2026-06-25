#!/usr/bin/env python3
"""
make_comparison_svg.py
======================
Generate isotopy resource-comparison SVG figures from ablation JSON output.

For each passage, produces two stacked comparison tables:
  - Three modern resources (WK / WN / MW) in isolation
  - All four resources including Webster 1828

Column headers are rotated 45° to avoid overlap.
Pills encode detection tier: S = STRONG, M = MEDIUM, W = WEAK, — = absent.

Usage
-----
    python3 make_comparison_svg.py \\
        --potocki  data/potocki_ablation.json \\
        --poe      data/poe_ablation.json \\
        --out-dir  figures/

    # Or run with defaults (looks for files in the same directory):
    python3 make_comparison_svg.py

Outputs
-------
    <out_dir>/isotopy_potocki_comparison.svg
    <out_dir>/isotopy_poe_comparison.svg

Pair lists
----------
Edit POTOCKI_PAIRS and POE_PAIRS below to change the representative pairs
shown in the figures. Each entry is a (lemma1, lemma2) tuple; the pipeline
will look up the highest tier at which both lemmas co-cluster.
"""

import argparse
import json
import os
import sys

# ---------------------------------------------------------------------------
# Representative pair lists — edit as needed
# ---------------------------------------------------------------------------

POTOCKI_PAIRS = [
    ("story",   "tale"),
    ("ghastly", "hideous"),
    ("gyration","swing"),
    ("agree",   "consent"),
    ("body",    "ghost"),
    ("gallows", "hang"),
    ("break",   "tear"),
    ("demon",   "innocent"),
    ("body",    "flesh"),
    ("attest",  "prove"),
]

POE_PAIRS = [
    ("life",       "soul"),
    ("life",       "spirit"),
    ("soul",       "spirit"),
    ("heart",      "life"),
    ("decay",      "sense"),
    ("dark",       "shade"),
    ("gloom",      "shade"),
    ("dreariness", "dreary"),
    ("dropping",   "sink"),
    ("hideous",    "terrible"),
]

# Ablation config names → data keys used in each JSON run
CONFIGS_3 = ["WK", "WN", "MW"]
CONFIGS_4 = ["WK", "WN", "MW", "W1828", "WK+WN+MW", "WK+WN+MW+W1828"]

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

ROW_H     = 24
PAIR_W    = 138
COL_W     = 48
PAD_X     = 20
PAD_Y     = 20
GAP       = 44
LEGEND_H  = 28
CAPTION_H = 28
HEADER_H  = 52   # taller row to accommodate rotated labels

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_tier(tiers: list, l1: str, l2: str) -> str:
    """Return the highest tier label in which both lemmas co-cluster, or '—'."""
    pair = {l1, l2}
    for tier_name in ["STRONG", "MEDIUM", "WEAK"]:
        tier = next((t for t in tiers if t["label"] == tier_name), None)
        if tier:
            for cluster in tier["clusters"]:
                if pair.issubset(set(cluster["lemmas"])):
                    return tier_name
    return "—"


def extract_matrix(ablation_data: list, pairs: list, configs: list) -> list[dict]:
    """
    Build a list of row dicts from ablation JSON and a list of (l1, l2) pairs.

    Each row dict has keys: 'pair', plus one key per config in CONFIGS_4
    mapped to the detection tier string or '—'.
    """
    runs = {run["config"]: run["tiers"] for run in ablation_data}
    rows = []
    for l1, l2 in pairs:
        row = {"pair": f"{l1}–{l2}"}
        for cfg in CONFIGS_4:
            row[cfg] = get_tier(runs[cfg], l1, l2) if cfg in runs else "—"
        rows.append(row)
    return rows


def pill_attrs(tier: str) -> tuple[str | None, str, str]:
    """Return (background, foreground, label) for a tier pill."""
    return {
        "STRONG": ("#E1F5EE", "#0F6E56", "S"),
        "MEDIUM": ("#EEEDFE", "#534AB7", "M"),
        "WEAK":   ("#FAEEDA", "#854F0B", "W"),
    }.get(tier, (None, "#b0b0b0", "—"))

# ---------------------------------------------------------------------------
# SVG builder
# ---------------------------------------------------------------------------

def make_svg(
    title: str,
    caption3: str,
    caption4: str,
    rows: list[dict],
    configs3: list[str],
    configs4: list[str],
    outpath: str,
) -> None:
    n_rows  = len(rows)
    t3_w    = PAIR_W + len(configs3) * COL_W
    t4_w    = PAIR_W + len(configs4) * COL_W
    total_w = max(t3_w, t4_w) + 2 * PAD_X
    table_h = HEADER_H + n_rows * ROW_H
    total_h = (PAD_Y + LEGEND_H + 16
               + table_h + CAPTION_H
               + PAD_Y + 10)

    lines: list[str] = []
    lines.append(
        f'<svg width="{total_w}" height="{total_h}" '
        f'viewBox="0 0 {total_w} {total_h}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'font-family="Helvetica Neue, Helvetica, Arial, sans-serif">'
    )
    lines.append(f'<rect width="{total_w}" height="{total_h}" fill="white"/>')

    # ── Legend ──────────────────────────────────────────────────────────────
    lx, ly = PAD_X, PAD_Y + 14
    for pill_txt, bg, fg, label in [
        ("S", "#E1F5EE", "#0F6E56", "STRONG (t ≥ 10)"),
        ("M", "#EEEDFE", "#534AB7", "MEDIUM (t ≥ 8)"),
        ("W", "#FAEEDA", "#854F0B", "WEAK (t ≥ 5)"),
    ]:
        lines.append(f'<rect x="{lx}" y="{ly-10}" width="18" height="16" rx="3" fill="{bg}"/>')
        lines.append(
            f'<text x="{lx+9}" y="{ly+2}" text-anchor="middle" '
            f'font-size="10" font-weight="600" fill="{fg}">{pill_txt}</text>'
        )
        lines.append(
            f'<text x="{lx+22}" y="{ly+2}" font-size="10" fill="#6b6b6b">{label}</text>'
        )
        lx += 130
    lines.append(f'<text x="{lx}" y="{ly+2}" font-size="13" fill="#b0b0b0">—</text>')
    lines.append(f'<text x="{lx+14}" y="{ly+2}" font-size="10" fill="#6b6b6b">absent</text>')

    # ── Table drawing function ───────────────────────────────────────────────
    def draw_table(
        ox: int,
        oy: int,
        cols: list[str],
        dashed_col: int | None,
        label_text: str,
        caption_text: str,
    ) -> None:
        tw = PAIR_W + len(cols) * COL_W

        # Section label
        lines.append(
            f'<text x="{ox}" y="{oy-6}" font-size="10" font-weight="600" '
            f'fill="#6b6b6b" letter-spacing="0.5">{label_text.upper()}</text>'
        )

        # "Pair" header
        lines.append(
            f'<text x="{ox}" y="{oy+HEADER_H-6}" '
            f'font-size="10" fill="#6b6b6b" font-weight="500">Pair</text>'
        )

        # Rotated column headers
        for ci, col in enumerate(cols):
            cx = ox + PAIR_W + ci * COL_W + COL_W // 2
            cy = oy + HEADER_H - 6
            lines.append(
                f'<text x="{cx}" y="{cy}" font-size="10" fill="#6b6b6b" '
                f'font-weight="500" text-anchor="start" '
                f'transform="rotate(-45,{cx},{cy})">{col}</text>'
            )

        # Header bottom border
        lines.append(
            f'<line x1="{ox}" y1="{oy+HEADER_H}" x2="{ox+tw}" y2="{oy+HEADER_H}" '
            f'stroke="rgba(0,0,0,0.3)" stroke-width="0.5"/>'
        )

        # Dashed W1828 separator
        if dashed_col is not None:
            dx = ox + PAIR_W + dashed_col * COL_W
            lines.append(
                f'<line x1="{dx}" y1="{oy+HEADER_H//2}" x2="{dx}" '
                f'y2="{oy+HEADER_H+n_rows*ROW_H}" '
                f'stroke="rgba(0,0,0,0.25)" stroke-width="1.5" stroke-dasharray="4 3"/>'
            )

        # Data rows
        for ri, row in enumerate(rows):
            ry = oy + HEADER_H + ri * ROW_H
            # Pair label
            lines.append(
                f'<text x="{ox}" y="{ry+15}" font-size="11" fill="#1a1a1a" '
                f'font-family="Courier New, monospace">{row["pair"]}</text>'
            )
            # Row separator
            if ri < n_rows - 1:
                lines.append(
                    f'<line x1="{ox}" y1="{ry+ROW_H}" x2="{ox+tw}" y2="{ry+ROW_H}" '
                    f'stroke="rgba(0,0,0,0.12)" stroke-width="0.5"/>'
                )
            # Pills
            for ci, col in enumerate(cols):
                tier = row.get(col, "—")
                cx   = ox + PAIR_W + ci * COL_W + COL_W // 2
                bg, fg, txt = pill_attrs(tier)
                if bg:
                    lines.append(
                        f'<rect x="{cx-12}" y="{ry+4}" width="24" height="16" '
                        f'rx="3" fill="{bg}"/>'
                    )
                    lines.append(
                        f'<text x="{cx}" y="{ry+16}" text-anchor="middle" '
                        f'font-size="10" font-weight="600" fill="{fg}">{txt}</text>'
                    )
                else:
                    lines.append(
                        f'<text x="{cx}" y="{ry+16}" text-anchor="middle" '
                        f'font-size="13" fill="#b0b0b0">—</text>'
                    )

        # Caption
        lines.append(
            f'<text x="{ox}" y="{oy+HEADER_H+n_rows*ROW_H+14}" '
            f'font-size="10" fill="#6b6b6b">{caption_text}</text>'
        )

    # ── Render two tables ────────────────────────────────────────────────────
    oy4 = PAD_Y + LEGEND_H + 16
    dash_idx = configs4.index("W1828") if "W1828" in configs4 else None
    draw_table(
        PAD_X, oy4, configs4,
        dashed_col=dash_idx,
        label_text=title,
        caption_text=caption4,
    )

    lines.append('</svg>')
    with open(outpath, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"  Saved {outpath}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--potocki",  default="potocki_ablation.json",
                        help="Potocki ablation JSON (default: potocki_ablation.json)")
    parser.add_argument("--poe",      default="poe_ablation.json",
                        help="Poe ablation JSON (default: poe_ablation.json)")
    parser.add_argument("--out-dir",  default=".",
                        help="Output directory for SVG files (default: current dir)")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    corpora = [
        (
            args.potocki,
            POTOCKI_PAIRS,
            "Potocki, Day 1",
            "Isotopy detection across Wiktionary (WK), WordNet 3.1 (WN), "
            "and Merriam-Webster (MW) in isolation.",
            "Full four-resource comparison. Dashed column separates modern "
            "resources from Webster 1828.",
            os.path.join(args.out_dir, "isotopy_potocki_comparison.svg"),
        ),
        (
            args.poe,
            POE_PAIRS,
            "Poe, House of Usher",
            "Isotopy detection across Wiktionary (WK), WordNet 3.1 (WN), "
            "and Merriam-Webster (MW) in isolation.",
            "Full four-resource comparison. Dashed column separates modern "
            "resources from Webster 1828.",
            os.path.join(args.out_dir, "isotopy_poe_comparison.svg"),
        ),
    ]

    for json_path, pairs, title, cap3, cap4, out_svg in corpora:
        print(f"\n{title}")
        if not os.path.exists(json_path):
            print(f"  ERROR: {json_path} not found — skipping", file=sys.stderr)
            continue
        with open(json_path, encoding="utf-8") as fh:
            ablation = json.load(fh)
        rows = extract_matrix(ablation, pairs, CONFIGS_4)
        make_svg(title, cap3, cap4, rows, CONFIGS_3, CONFIGS_4, out_svg)

    print("\nDone.")


if __name__ == "__main__":
    main()
