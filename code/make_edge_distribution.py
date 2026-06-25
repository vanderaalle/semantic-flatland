#!/usr/bin/env python3
"""
make_edge_distribution.py
=========================
Generate the edge score distribution figure from pipeline results JSONs.

Produces a 2×2 figure:
  Top row    — ranked edge scores (strongest → weakest) with tier threshold lines
  Bottom row — log-log plot with linear regression fit confirming power-law structure

One column per passage (Potocki left, Poe right).

Usage
-----
    python3 make_edge_distribution.py \\
        --potocki  data/potocki_results.json \\
        --poe      data/poe_results.json \\
        --out      figures/isotopy_edge_distribution.pdf

    # Or run with defaults:
    python3 make_edge_distribution.py

Output
------
    isotopy_edge_distribution.pdf  (300 DPI, book_grayscale style)
"""

import argparse
import json
import os
import sys

import numpy as np
from scipy import stats

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Resolve style module
# Script lives at projects/isotopy/code/ → style.py is at repo root.
# Adjust STYLE_DIR below if your layout differs.
# ---------------------------------------------------------------------------
_HERE      = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))

# style.py search order: repo root, then brainstorming/assets (legacy location)
for _STYLE_DIR in [_REPO_ROOT, os.path.join(_REPO_ROOT, "brainstorming", "assets")]:
    sys.path.insert(0, _STYLE_DIR)
    try:
        from style import PlotStyle  # noqa: E402
        break
    except ImportError:
        continue
else:
    raise ImportError(
        "Could not import PlotStyle. Ensure style.py is in the repo root "
        "or set the path manually at the top of this script."
    )

# ---------------------------------------------------------------------------
# Tier thresholds
# ---------------------------------------------------------------------------
THRESHOLDS = [
    ("STRONG", 10, "#1a1a1a"),
    ("MEDIUM",  8, "#555555"),
    ("WEAK",    5, "#999999"),
]
SHADES = {"STRONG": "#e0e0e0", "MEDIUM": "#cccccc", "WEAK": "#b8b8b8"}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_edges(json_path: str) -> np.ndarray:
    """Load raw edges from a results JSON and return sorted descending scores."""
    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)
    scores = [e[2] for e in data["raw_edges"]]
    return np.array(sorted(scores, reverse=True))


# ---------------------------------------------------------------------------
# Figure generation
# ---------------------------------------------------------------------------

def make_figure(datasets: dict[str, np.ndarray], out_path: str) -> None:
    """
    datasets : {passage_name: sorted_edge_scores_array}
    out_path : PDF output path
    """
    style = PlotStyle.book_grayscale()
    style.apply()

    fig, axes = plt.subplots(2, 2, figsize=(7.0, 7.0 * 0.9))
    for ax in axes.flat:
        style._style_axes(ax)

    for col, (name, edges) in enumerate(datasets.items()):
        n     = len(edges)
        x     = np.arange(1, n + 1)
        log_x = np.log(x)
        log_y = np.log(edges)

        ax_top = axes[0, col]
        ax_bot = axes[1, col]

        # ── top panel: ranked scores ──────────────────────────────────────
        ax_top.plot(x, edges, color=style.c.primary, linewidth=0.8, zorder=3)

        prev_idx = 0
        for label, t, _ in THRESHOLDS:
            idx = int(np.sum(edges >= t))
            ax_top.axvspan(prev_idx, idx, alpha=0.20, color=SHADES[label], zorder=1)
            prev_idx = idx

        for label, t, color in THRESHOLDS:
            ax_top.axhline(y=t, color=color,
                           linewidth=style.geometry.linewidth_thin,
                           linestyle="--", zorder=2)
            ax_top.text(n * 0.68, t + 0.6, label,
                        fontsize=6.5, color=color, va="bottom")

        ax_top.set_xlabel("edge rank", fontsize=style.typography.size_label)
        if col == 0:
            ax_top.set_ylabel("score", fontsize=style.typography.size_label)
        ax_top.set_title(name, fontsize=style.typography.size_title)
        ax_top.set_xlim(1, n)
        ax_top.set_ylim(0, float(edges[0]) * 1.05)

        # ── bottom panel: log-log ─────────────────────────────────────────
        slope, intercept, r, _, _ = stats.linregress(log_x, log_y)
        fit_y = intercept + slope * log_x

        ax_bot.scatter(log_x, log_y, s=2, color=style.c.muted,
                       zorder=2, linewidths=0)
        ax_bot.plot(log_x, fit_y, color=style.c.primary,
                    linewidth=style.geometry.linewidth, zorder=3,
                    label=f"slope = {slope:.3f},  R² = {r**2:.3f}")

        for label, t, color in THRESHOLDS:
            ax_bot.axhline(y=np.log(t), color=color,
                           linewidth=style.geometry.linewidth_thin,
                           linestyle="--", zorder=2)
            ax_bot.text(log_x[-1] * 0.02, np.log(t) + 0.05,
                        label, fontsize=6.5, color=color, va="bottom")

        ax_bot.set_xlabel("log rank", fontsize=style.typography.size_label)
        if col == 0:
            ax_bot.set_ylabel("log score", fontsize=style.typography.size_label)
        ax_bot.legend(fontsize=6.5, framealpha=0, loc="upper right")
        ax_bot.set_xlim(0, log_x[-1] * 1.02)

        print(f"  {name}: slope={slope:.3f}, R²={r**2:.3f}, "
              f"n={n}, max={edges[0]:.2f}, median={np.median(edges):.2f}")

    fig.tight_layout(pad=1.0, h_pad=1.5, w_pad=1.2)
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print(f"  Saved {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--potocki", default="potocki_results.json",
                        help="Potocki results JSON (default: potocki_results.json)")
    parser.add_argument("--poe",     default="poe_results.json",
                        help="Poe results JSON (default: poe_results.json)")
    parser.add_argument("--out",     default="isotopy_edge_distribution.pdf",
                        help="Output PDF path (default: isotopy_edge_distribution.pdf)")
    args = parser.parse_args()

    datasets = {}
    for name, path in [("Potocki", args.potocki), ("Poe", args.poe)]:
        if not os.path.exists(path):
            print(f"ERROR: {path} not found", file=sys.stderr)
            sys.exit(1)
        datasets[name] = load_edges(path)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    print("Generating edge distribution figure...")
    make_figure(datasets, args.out)
    print("Done.")


if __name__ == "__main__":
    main()
