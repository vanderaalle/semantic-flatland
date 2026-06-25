"""
Generate all figures for "Computational Lexicon-Based Isotopy Detection for Dummies"
"""
import sys
sys.path.insert(0, '/home/claude')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import json, re, math
from collections import defaultdict, Counter

from style import PlotStyle
style = PlotStyle.book_grayscale()
style.apply()

FIGS = '/home/claude/figs'
import os; os.makedirs(FIGS, exist_ok=True)

BLACK  = '#1a1a1a'
DARK   = '#444444'
MID    = '#888888'
LIGHT  = '#cccccc'
PALE   = '#f0f0f0'
ACCENT = '#2a2a2a'

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIG 1 — What is isotopy? Two lemmas sharing semes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
fig, ax = plt.subplots(figsize=(7, 3.2))
ax.set_xlim(0, 10); ax.set_ylim(0, 4); ax.axis('off')

# lemma boxes
for x, label, sems in [(1.5, 'GHOST', ['soul','spirit','disembodied','deceased','death']),
                        (8.5, 'DEMON', ['evil','spirit','supernatural','wicked','soul'])]:
    ax.add_patch(FancyBboxPatch((x-1.3, 0.5), 2.6, 3.0,
        boxstyle='round,pad=0.1', facecolor=PALE, edgecolor=BLACK, linewidth=1.2))
    ax.text(x, 3.2, label, ha='center', va='center', fontsize=10,
            fontweight='bold', color=BLACK)
    for i, s in enumerate(sems):
        color = BLACK if s in ['soul','spirit'] else MID
        fw = 'bold' if s in ['soul','spirit'] else 'normal'
        ax.text(x, 2.6 - i*0.5, s, ha='center', va='center',
                fontsize=8.5, color=color, fontweight=fw)

# shared semes in centre
for i, word in enumerate(['soul', 'spirit']):
    y = 2.8 - i*0.8
    ax.add_patch(plt.Rectangle((3.8, y-0.22), 2.4, 0.44,
        facecolor=BLACK, edgecolor='none', zorder=2))
    ax.text(5, y, word, ha='center', va='center', fontsize=9,
            color='white', fontweight='bold')
    # arrows
    ax.annotate('', xy=(3.85, y), xytext=(2.85, y),
                arrowprops=dict(arrowstyle='->', color=BLACK, lw=1.2))
    ax.annotate('', xy=(6.15, y), xytext=(7.15, y),
                arrowprops=dict(arrowstyle='->', color=BLACK, lw=1.2))

ax.text(5, 0.15, 'shared semes → isotopy /supernatural–death/', ha='center',
        va='center', fontsize=8, color=DARK, style='italic')

fig.tight_layout()
fig.savefig(f'{FIGS}/fig1_isotopy_concept.png', dpi=250, bbox_inches='tight')
plt.close()
print('fig1 done')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIG 2 — The pipeline overview
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
fig, ax = plt.subplots(figsize=(7, 2.4))
ax.set_xlim(0, 10); ax.set_ylim(0, 3); ax.axis('off')

steps = [
    (0.7,  'Literary\npassage'),
    (2.5,  'Content\nwords'),
    (4.3,  'Dictionary\ndefinitions'),
    (6.1,  'Seme\nextraction'),
    (7.9,  'Graph &\nclustering'),
    (9.5,  'Isotopy\nclusters'),
]
for i, (x, label) in enumerate(steps):
    w = 1.4
    ax.add_patch(FancyBboxPatch((x-w/2, 0.8), w, 1.4,
        boxstyle='round,pad=0.08',
        facecolor=BLACK if i in [0,5] else PALE,
        edgecolor=BLACK, linewidth=1.0))
    ax.text(x, 1.5, label, ha='center', va='center', fontsize=7.5,
            color='white' if i in [0,5] else BLACK)
    if i < len(steps)-1:
        ax.annotate('', xy=(x+w/2+0.12, 1.5), xytext=(x+w/2+0.02, 1.5),
                    arrowprops=dict(arrowstyle='->', color=DARK, lw=1.0))

labels2 = ['§2', '§3', '§4', '§5', '§6', '§7']
for i, (x, _) in enumerate(steps):
    ax.text(x, 0.55, labels2[i], ha='center', va='center', fontsize=7, color=MID)

fig.tight_layout()
fig.savefig(f'{FIGS}/fig2_pipeline.png', dpi=250, bbox_inches='tight')
plt.close()
print('fig2 done')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIG 3 — Passage with content words annotated
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
passage_tokens = [
    ('The', False), ('brothers', True), ('Zoto', False), ('had', False),
    ('been', False), ('executed', True), ('on', False), ('the', False),
    ('gallows', True), ('and', False), ('their', False), ('corpses', True),
    ('still', False), ('hung', True), ('there', False), ('.', False),
    ('The', False), ('gyrations', True), ('of', False), ('these', False),
    ('ghastly', True), ('bodies', True), ('prompted', True), ('in', False),
    ('me', False), ('a', False), ('curiosity', True), ('to', False),
    ('see', True), ('them', False), ('more', False), ('closely', False), ('.', False),
]

fig, ax = plt.subplots(figsize=(7, 2.0))
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')

x, y = 0.02, 0.78
line_h = 0.32
words_per_line = 17

for i, (word, is_content) in enumerate(passage_tokens):
    if i > 0 and i % words_per_line == 0:
        x = 0.02; y -= line_h

    fw = 'bold' if is_content else 'normal'
    col = BLACK if is_content else MID
    ax.text(x, y, word, fontsize=8.5, color=col, fontweight=fw,
            transform=ax.transAxes, ha='left', va='top')
    if is_content:
        ax.annotate('', xy=(x + len(word)*0.013 + 0.008, y - 0.06),
                    xytext=(x, y - 0.06),
                    xycoords='axes fraction', textcoords='axes fraction',
                    arrowprops=dict(arrowstyle='-', color=BLACK, lw=0.7))
    x += len(word) * 0.012 + 0.013

ax.text(0.02, 0.08, 'Content words (bold, underlined) = lemmatized → 81 lemmas',
        fontsize=7.5, color=DARK, style='italic', transform=ax.transAxes)

fig.tight_layout()
fig.savefig(f'{FIGS}/fig3_passage_annotation.png', dpi=250, bbox_inches='tight')
plt.close()
print('fig3 done')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIG 4 — Definition → seme extraction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
fig, ax = plt.subplots(figsize=(7, 3.2))
ax.set_xlim(0, 10); ax.set_ylim(0, 4.2); ax.axis('off')
ax.add_patch(plt.Rectangle((0.1, 1.6), 1.8, 1.0, facecolor=BLACK, edgecolor='none'))
ax.text(1.0, 2.1, 'GHOST', ha='center', va='center', fontsize=10, fontweight='bold', color='white')
ax.annotate('', xy=(2.25, 2.1), xytext=(1.95, 2.1), arrowprops=dict(arrowstyle='->', color=DARK, lw=1.2))
ax.text(2.1, 2.38, 'dictionary\nlookup', ha='center', va='center', fontsize=6.5, color=DARK)
ax.add_patch(FancyBboxPatch((2.3, 0.6), 4.75, 2.9, boxstyle='round,pad=0.1', facecolor=PALE, edgecolor=DARK, linewidth=0.8))
ax.text(4.675, 3.32, 'Raw definition', ha='center', va='center', fontsize=7.5, fontweight='bold', color=BLACK)
defn_text = ('"the visible disembodied soul\n of a dead person; a spirit\n appearing after death"')
ax.text(4.675, 2.35, defn_text, ha='center', va='center', fontsize=8, color=DARK, style='italic', linespacing=1.55)
ax.plot([2.5, 6.9], [1.55, 1.55], color=LIGHT, lw=0.7)
ax.text(4.675, 1.32, 'kept:', ha='center', va='center', fontsize=6.5, color=MID, style='italic')
ax.text(4.675, 1.05, 'visible  disembodied  soul  dead  spirit  appearing  death', ha='center', va='center', fontsize=7, color=BLACK, fontweight='bold')
ax.text(4.675, 0.78, 'filtered:  the  of  a  person  after  …', ha='center', va='center', fontsize=6.5, color=LIGHT)
ax.annotate('', xy=(7.95, 2.1), xytext=(7.1, 2.1), arrowprops=dict(arrowstyle='->', color=DARK, lw=1.2))
ax.text(7.52, 2.38, '− NUCLEAR\n− len > 2', ha='center', va='center', fontsize=6.5, color=DARK)
semes = ['visible','disembodied','soul','dead','spirit','appearing','death']
ax.add_patch(FancyBboxPatch((8.05, 0.5), 1.85, 3.0, boxstyle='round,pad=0.1', facecolor=PALE, edgecolor=BLACK, linewidth=1.0))
ax.text(8.975, 3.32, 'Semes', ha='center', va='center', fontsize=7.5, fontweight='bold', color=BLACK)
for i, c in enumerate(semes):
    ax.text(8.975, 2.95 - i*0.35, c, ha='center', va='center', fontsize=7, color=BLACK)
fig.tight_layout()
fig.savefig(f'{FIGS}/fig4_seme_extraction.png', dpi=250, bbox_inches='tight')
plt.close()
print('fig4 done')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIG 5 — Bipartite graph (small example)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
fig, ax = plt.subplots(figsize=(7, 3.8))
ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.axis('off')

lemmas_b = ['ghost', 'demon', 'ghastly', 'eerie', 'strange']
semes_b = ['soul', 'spirit', 'evil', 'supernatural', 'dead',
               'mysterious', 'unusual', 'odd']

edges_b = {
    'ghost':   ['soul', 'spirit', 'dead'],
    'demon':   ['soul', 'evil', 'supernatural'],
    'ghastly': ['spirit', 'dead'],
    'eerie':   ['supernatural', 'mysterious'],
    'strange': ['mysterious', 'unusual', 'odd'],
}

lx, cx = 1.5, 8.0
ly = np.linspace(4.3, 0.7, len(lemmas_b))
cy = np.linspace(4.5, 0.5, len(semes_b))

lpos = {l: (lx, ly[i]) for i, l in enumerate(lemmas_b)}
cpos = {c: (cx, cy[i]) for i, c in enumerate(semes_b)}

# shared semes (degree ≥ 2)
from collections import Counter as C2
deg = C2(c for cs in edges_b.values() for c in cs)
shared_class = {c for c, n in deg.items() if n >= 2}

# draw edges
for lemma, cs in edges_b.items():
    for c in cs:
        lp, cp = lpos[lemma], cpos[c]
        lw = 1.5 if c in shared_class else 0.6
        col = BLACK if c in shared_class else LIGHT
        ax.plot([lp[0], cp[0]], [lp[1], cp[1]], '-',
                color=col, lw=lw, zorder=1)

# draw lemma nodes
for l, (x, y) in lpos.items():
    ax.add_patch(plt.Circle((x, y), 0.38, facecolor=BLACK,
                             edgecolor='none', zorder=3))
    ax.text(x, y, l, ha='center', va='center',
            fontsize=8, color='white', fontweight='bold', zorder=4)

# draw seme nodes
for c, (x, y) in cpos.items():
    fc = BLACK if c in shared_class else PALE
    ec = BLACK
    tc = 'white' if c in shared_class else DARK
    ax.add_patch(FancyBboxPatch((x-0.7, y-0.22), 1.4, 0.44,
        boxstyle='round,pad=0.05', facecolor=fc, edgecolor=ec,
        linewidth=1.0 if c in shared_class else 0.5, zorder=3))
    ax.text(x, y, c, ha='center', va='center',
            fontsize=8, color=tc, zorder=4)

# labels
ax.text(lx, 4.85, 'LEMMAS', ha='center', fontsize=8.5,
        fontweight='bold', color=BLACK)
ax.text(cx, 4.95, 'CLASSEMES', ha='center', fontsize=8.5,
        fontweight='bold', color=BLACK)
ax.text(5, 0.1, 'Filled semes (degree ≥ 2) are shared by multiple lemmas → isotopy evidence',
        ha='center', fontsize=7.5, color=DARK, style='italic')

# legend
ax.add_patch(plt.Rectangle((3.5, 4.5), 0.25, 0.25, facecolor=BLACK))
ax.text(3.85, 4.625, '= shared seme (degree ≥ 2)', fontsize=7.5, va='center', color=DARK)

fig.tight_layout()
fig.savefig(f'{FIGS}/fig5_bipartite.png', dpi=250, bbox_inches='tight')
plt.close()
print('fig5 done')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIG 6 — IDF weighting concept
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
fig, ax = plt.subplots(figsize=(5.5, 2.8))
N = 81
counts = np.array([1, 2, 3, 5, 8, 12, 20, 36])
idf_vals = np.log(N / counts)
ax.plot(counts, idf_vals, 'o-', color=BLACK, lw=1.5, ms=5)
ax.set_xlabel('Number of lemmas sharing this seme', fontsize=9)
ax.set_ylabel('IDF weight', fontsize=9)
ax.set_title('Rare semes carry more isotopy evidence', fontsize=9)

# annotate examples
examples = [(1, 'cadaver'), (2, 'soul'), (5, 'dead'), (20, 'person')]
for cnt, word in examples:
    idf = math.log(N/cnt)
    ax.annotate(f'  "{word}"', xy=(cnt, idf), fontsize=7.5, color=DARK,
                va='center')

ax.axvline(x=N*0.45, color=MID, lw=1.0, ls='--')
ax.text(N*0.45+1, 0.5, 'IDF cutoff\n(too common)', fontsize=7, color=MID)
ax.set_xlim(0, 45); ax.set_ylim(0, 5)
fig.tight_layout()
fig.savefig(f'{FIGS}/fig6_idf.png', dpi=250, bbox_inches='tight')
plt.close()
print('fig6 done')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIG 7 — L2 expansion and the corpus-lemma problem
# Three panels:
#   A: TEAR — L1 only (direct semes from definition)
#   B: FORCE — its own L1 ring (what would flood into TEAR via L2 without fix)
#   C: TEAR — L2 with fix (force skipped; legitimate intermediates followed)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.4))

def lemma_circle(ax, x, y, label, r=0.42, col=BLACK):
    ax.add_patch(plt.Circle((x, y), r, facecolor=col, zorder=3))
    ax.text(x, y, label, ha='center', va='center', color='white',
            fontsize=8, fontweight='bold', zorder=4)

def seme_box(ax, x, y, label, style='solid', fc=PALE, ec=DARK, tc=BLACK, fs=7):
    ax.add_patch(FancyBboxPatch((x-0.52, y-0.24), 1.04, 0.48,
        boxstyle='round,pad=0.04', facecolor=fc, edgecolor=ec,
        linewidth=0.7, ls=style, zorder=3))
    ax.text(x, y, label, ha='center', va='center', fontsize=fs, color=tc, zorder=4)

def edge(ax, x0, y0, x1, y1, style='-', col=DARK, lw=0.7):
    ax.plot([x0, x1], [y0, y1], style, color=col, lw=lw, zorder=2)

# ── Panel A: TEAR — L1 only ───────────────────────────────────────────────────
ax = axes[0]
ax.set_xlim(0, 6); ax.set_ylim(0, 5.2); ax.axis('off')
ax.set_title('TEAR — L1 semes', fontsize=8.5, pad=6)

lemma_circle(ax, 3, 3.6, 'tear')
tear_l1 = [('rend',1.1,4.2),('pull',2.0,4.6),('apart',4.0,4.6),
           ('violence',4.8,4.0),('lacerate',5.0,3.0),('wound',4.6,2.1),
           ('force',2.2,2.2)]   # ← force appears in tear's definition
for w, x, y in tear_l1:
    fc = '#fff0f0' if w == 'force' else PALE
    ec = '#cc4444' if w == 'force' else DARK
    tc = '#cc4444' if w == 'force' else BLACK
    seme_box(ax, x, y, w, fc=fc, ec=ec, tc=tc)
    edge(ax, 3, 3.6, x, y)

ax.text(2.2, 1.7, '← corpus lemma!', fontsize=6, color='#cc4444', style='italic', ha='center')
ax.text(3, 0.3, 'L1: direct definition words', ha='center', fontsize=6.5, color=MID)

# ── Panel B: FORCE — its own L1 ring ─────────────────────────────────────────
ax = axes[1]
ax.set_xlim(0, 6); ax.set_ylim(0, 5.2); ax.axis('off')
ax.set_title('FORCE — its own L1 semes', fontsize=8.5, pad=6)
ax.text(3, 5.0, '(what L2 would import into TEAR)', fontsize=6.5, color='#cc4444',
        ha='center', va='bottom', style='italic')

lemma_circle(ax, 3, 3.6, 'force', col='#cc4444')
force_l1 = [('compel',0.9,4.5),('coercion',2.0,4.9),('vigor',4.0,4.9),
            ('might',4.9,4.2),('efficacy',5.1,3.2),('military',4.8,2.2),
            ('army',3.6,1.6),('troop',2.2,1.6)]
for w, x, y in force_l1:
    seme_box(ax, x, y, w, fc='#fff0f0', ec='#cc9999', tc='#884444', fs=6.5)
    edge(ax, 3, 3.6, x, y, col='#cc9999')

ax.text(3, 0.3, 'none of these belong to TEAR\'s isotopy',
        ha='center', fontsize=6.5, color='#cc4444', style='italic')

# ── Panel C: TEAR — L2 with fix ───────────────────────────────────────────────
ax = axes[2]
ax.set_xlim(0, 6); ax.set_ylim(0, 5.2); ax.axis('off')
ax.set_title('TEAR — L2 with corpus-lemma fix', fontsize=8.5, pad=6)

lemma_circle(ax, 3, 3.6, 'tear')
# L1 nodes — force greyed out (skipped as intermediate)
for w, x, y in tear_l1:
    if w == 'force':
        seme_box(ax, x, y, w+'  ✗', fc='#f0f0f0', ec=LIGHT, tc=LIGHT, fs=6.5)
        edge(ax, 3, 3.6, x, y, col=LIGHT, style=':')
    else:
        seme_box(ax, x, y, w)
        edge(ax, 3, 3.6, x, y)

# L2 via legitimate intermediate 'rend' (not a corpus lemma)
l2_nodes = [('separate',0.5,1.8),('divide',1.6,1.4)]
for w, x, y in l2_nodes:
    seme_box(ax, x, y, w, style='--', fc='#e8e8e8', ec=MID, tc=DARK, fs=6.5)
    edge(ax, 1.1, 4.2-0.24, x, y+0.24, style='--', col=MID, lw=0.6)

ax.text(1.1, 0.85, '↑ L2 via rend (×0.5)', fontsize=6, color=MID, ha='center')
ax.text(3, 0.3, 'force skipped; legitimate L2 via rend', ha='center', fontsize=6.5, color=DARK)

fig.tight_layout()
fig.savefig(f'{FIGS}/fig7_l2_expansion.png', dpi=250, bbox_inches='tight')
plt.close()
print('fig7 done')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIG 8 — Score distribution with natural gaps
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# real scores from the merged pipeline
top_scores = [60.28, 27.26, 21.40, 20.42, 19.44, 18.76, 17.12, 16.31,
              15.24, 14.81, 14.11, 13.71, 13.59, 13.48, 13.30, 12.39,
              11.10, 10.70, 10.41, 10.01,
              7.2, 6.8, 6.5, 6.1, 5.9, 5.5, 5.2, 4.9, 4.6, 4.2,
              3.90, 3.85, 3.80, 3.75, 3.72, 3.71, 3.71, 3.71, 3.71]

fig, ax = plt.subplots(figsize=(7, 2.8))
ranks = np.arange(1, len(top_scores)+1)
ax.bar(ranks, top_scores, color=BLACK, width=0.8)

# threshold bands
thresholds = [(10.0, 'strong (t=10)', 0.85), (8.0, 'medium (t=8)', 0.6), (5.0, 'weak (t=5)', 0.35)]
fills = [0.18, 0.12, 0.07]
colors = [BLACK, DARK, MID]
for t, label, alpha in thresholds:
    ax.axhline(y=t, color=LIGHT, lw=1.0, ls='--')
    ax.text(len(top_scores)+0.5, t, f't={t:.0f}', fontsize=7, va='center', color=DARK)

ax.set_xlabel('Edge rank (strongest → weakest)', fontsize=8.5)
ax.set_ylabel('Raw score', fontsize=8.5)
ax.set_title('Edge score distribution — merged lexicon (81 lemmas)', fontsize=9)

# annotate top edges
for rank, score, label in [(1,60.28,'story–tale'), (2,27.26,'argument–thesis'),
                            (3,21.40,'break–tear'), (5,19.44,'hear–see')]:
    ax.text(rank, score+1.5, label, ha='center', fontsize=6.5, color=DARK, rotation=45)

ax.set_xlim(0, len(top_scores)+3)
ax.set_ylim(0, 68)
fig.tight_layout()
fig.savefig(f'{FIGS}/fig8_score_dist.png', dpi=250, bbox_inches='tight')
plt.close()
print('fig8 done')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIG 9 — Single-linkage vs complete-linkage
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
fig, axes = plt.subplots(1, 2, figsize=(7, 3.2))

for ax, title, show_weak, valid in zip(axes,
    ['Single-linkage: chain artifact', 'Complete-linkage: direct evidence only'],
    [True, False],
    [False, True]):

    ax.set_xlim(0, 6); ax.set_ylim(0, 5); ax.axis('off')
    ax.set_title(title, fontsize=8.5, pad=4)

    nodes = {'A': (1.2, 3.8), 'B': (3.0, 4.2), 'C': (4.8, 3.8),
             'D': (1.2, 1.5), 'E': (3.0, 1.0), 'F': (4.8, 1.5)}
    labels_n = {'A':'ghost','B':'demon','C':'eerie','D':'corpse','E':'night','F':'strange'}

    # strong edges
    strong = [('A','B'), ('B','C'), ('D','E'), ('E','F'), ('C','F')]
    # weak chain edge A-D (only in single linkage)
    weak   = [('A','D')]

    for n1, n2 in strong:
        p1, p2 = nodes[n1], nodes[n2]
        ax.plot([p1[0],p2[0]], [p1[1],p2[1]], '-', color=BLACK, lw=1.8, zorder=2)

    if show_weak:
        for n1, n2 in weak:
            p1, p2 = nodes[n1], nodes[n2]
            ax.plot([p1[0],p2[0]], [p1[1],p2[1]], '--', color=LIGHT, lw=1.2, zorder=1)
        # one big cluster oval
        from matplotlib.patches import Ellipse
        ax.add_patch(Ellipse((3,2.6), 4.8, 4.0, angle=0,
            facecolor='none', edgecolor=DARK, lw=1.0, ls=':', zorder=1))
        ax.text(3, 0.2, '→ all 6 in one cluster via weak bridge A–D',
                ha='center', fontsize=7, color=DARK, style='italic')
    else:
        # two cluster ovals
        ax.add_patch(plt.Polygon([[0.3,2.8],[0.3,4.8],[5.5,4.8],[5.5,2.8]],
            facecolor='none', edgecolor=DARK, lw=1.0, ls=':', closed=True))
        ax.add_patch(plt.Polygon([[0.3,0.2],[0.3,2.2],[5.5,2.2],[5.5,0.2]],
            facecolor='none', edgecolor=DARK, lw=1.0, ls=':', closed=True))
        ax.text(3, 0.05, '→ two clusters: only directly connected pairs merge',
                ha='center', fontsize=7, color=DARK, style='italic')

    for n, (x, y) in nodes.items():
        ax.add_patch(plt.Circle((x,y), 0.42, facecolor=BLACK, zorder=3))
        ax.text(x, y, labels_n[n], ha='center', va='center',
                fontsize=7.5, color='white', fontweight='bold', zorder=4)

fig.tight_layout()
fig.savefig(f'{FIGS}/fig9_clustering.png', dpi=250, bbox_inches='tight')
plt.close()
print('fig9 done')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIG 10 — Final isotopy clusters (three-tier)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
fig, ax = plt.subplots(figsize=(7, 4.5))
ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.axis('off')

tiers = [
    ('STRONG  t ≥ 10', [
        ('story · tale · fact', 'narrative–testimony'),
        ('argument · thesis · supposition', 'argumentation'),
        ('agree · consent', 'legal–social accord'),
        ('attest · prove', 'verification'),
        ('body · flesh', 'corporeal matter'),
        ('break · tear', 'physical rupture'),
    ], 5.5, 0.28),
    ('MEDIUM  t ≥ 8', [
        ('gyration · swing', 'rotary motion'),
        ('escape · prison', 'confinement'),
        ('execute · hang', 'capital punishment'),
        ('eye · hear · see', 'perception'),
    ], 3.1, 0.28),
    ('WEAK  t ≥ 5', [
        ('ghost · demon · eerie', 'supernatural'),
        ('ghastly · hideous · revolting', 'repulsion'),
        ('corpse · ghost · living', 'undead–life'),
        ('gallows · prison', 'captivity'),
    ], 1.0, 0.28),
]

for tier_label, clusters, y_top, dy in tiers:
    # tier label
    ax.text(0.15, y_top+0.35, tier_label, fontsize=8.5,
            fontweight='bold', color=BLACK, va='center')
    ax.axhline(y=y_top+0.15, xmin=0.01, xmax=0.99,
               color=LIGHT, lw=0.7)
    for i, (members, label) in enumerate(clusters):
        y = y_top - i*dy
        # member pill
        ax.add_patch(FancyBboxPatch((0.15, y-0.11), 3.6, 0.24,
            boxstyle='round,pad=0.04', facecolor=PALE,
            edgecolor=DARK, linewidth=0.5))
        ax.text(0.35, y, members, va='center', fontsize=7.5, color=BLACK)
        # label
        ax.text(4.0, y, f'/{label}/', va='center', fontsize=7.5,
                color=DARK, style='italic')

ax.text(5, 0.1, 'Three-tier structure reflects isotopy density in the passage',
        ha='center', fontsize=7.5, color=MID, style='italic')

fig.tight_layout()
fig.savefig(f'{FIGS}/fig10_tiers.png', dpi=250, bbox_inches='tight')
plt.close()
print('fig10 done')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIG 11a — Three-resource comparison  →  §8
# FIG 11b — Four-resource comparison   →  §10
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
isotopies = [
    'story–tale', 'argument–thesis', 'eerie–strange', 'ghost–demon',
    'break–tear', 'gyration–swing', 'escape–prison', 'corpse–living',
    'agree–consent', 'execute–hang',
]
data_full = np.array([
    [2, 1, 2, 2], [2, 0, 2, 2], [2, 1, 2, 2], [2, 0, 2, 2],
    [2, 0, 2, 2], [2, 0, 0, 2], [1, 1, 2, 2], [2, 1, 2, 2],
    [0, 0, 2, 2], [0, 0, 2, 2],
])
data_three = data_full[:, :3]
cmap = matplotlib.colors.ListedColormap([PALE, '#888888', BLACK])

def make_heatmap(data, resources, fname, show_divider=False, figw=5.5):
    fig, ax = plt.subplots(figsize=(figw, 4.2))
    ax.imshow(data, cmap=cmap, aspect='auto', vmin=0, vmax=2)
    ax.set_xticks(range(len(resources))); ax.set_xticklabels(resources, fontsize=8.5)
    ax.set_yticks(range(len(isotopies))); ax.set_yticklabels(isotopies, fontsize=8)
    ax.xaxis.tick_top()
    if show_divider:
        ax.axvline(x=2.5, color='white', lw=2.5, zorder=3)
        ax.axvline(x=2.5, color=DARK,   lw=0.8, ls='--', zorder=4)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            val = data[i, j]
            sym = '✓' if val == 2 else ('~' if val == 1 else '–')
            col = 'white' if val == 2 else (DARK if val == 1 else LIGHT)
            ax.text(j, i, sym, ha='center', va='center', fontsize=10, color=col)
    ax.set_title('Isotopy detection across lexical resources', fontsize=9, pad=18)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.12)
    legend_items = [('✓ detected', BLACK, 'white'), ('~ weak', MID, DARK), ('– absent', PALE, DARK)]
    for i, (label, fc, tc) in enumerate(legend_items):
        x = 0.25 + i * 0.25
        rect = matplotlib.patches.FancyBboxPatch((x - 0.07, 0.02), 0.14, 0.055,
            boxstyle='round,pad=0.005', facecolor=fc, edgecolor=DARK, lw=0.5,
            transform=fig.transFigure, clip_on=False)
        fig.add_artist(rect)
        fig.text(x, 0.047, label, ha='center', va='center',
                 fontsize=7.5, color=tc, transform=fig.transFigure)
    fig.savefig(f'{FIGS}/{fname}', dpi=250, bbox_inches='tight')
    plt.close()

make_heatmap(data_three, ['Wiktionary', 'WordNet 3.1', 'Merriam-\nWebster'],
             'fig11a_three_resources.png', show_divider=False, figw=5.0)
print('fig11a done')
make_heatmap(data_full, ['Wiktionary', 'WordNet 3.1', 'Merriam-\nWebster', 'Webster\n1828'],
             'fig11b_four_resources.png', show_divider=True, figw=7.0)
print('fig11b done')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIG 12 — NUCLEAR taxonomy
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
fig, ax = plt.subplots(figsize=(7, 3.2))
ax.set_xlim(0, 10); ax.set_ylim(0, 4); ax.axis('off')

categories = [
    (1.5, 'Semantic universals',
     'person, thing, state,\nact, cause, way, form…',
     'Too general for any corpus.\nTheoretical exclusion.'),
    (5.0, 'Domain junk',
     'eggs, fowl, hatching,\niso 639, gyrating…',
     'Wrong sense in a specific\ndictionary. Documented per resource.'),
    (8.5, 'Corpus-lemma semes',
     'force, free, dead,\nwind, tear, body…',
     'Passage vocabulary in definitions\n= circular. L2 fix applies.'),
]

for x, title, examples, rationale in categories:
    # box
    ax.add_patch(FancyBboxPatch((x-1.4, 0.4), 2.8, 3.2,
        boxstyle='round,pad=0.1', facecolor=PALE, edgecolor=BLACK, linewidth=1.0))
    ax.text(x, 3.3, title, ha='center', va='center',
            fontsize=8.5, fontweight='bold', color=BLACK)
    ax.axhline(y=2.9, xmin=(x-1.3)/10, xmax=(x+1.3)/10, color=LIGHT, lw=0.6)
    ax.text(x, 2.4, examples, ha='center', va='center',
            fontsize=7.5, color=DARK, style='italic')
    ax.axhline(y=1.8, xmin=(x-1.3)/10, xmax=(x+1.3)/10, color=LIGHT, lw=0.6)
    ax.text(x, 1.15, rationale, ha='center', va='center',
            fontsize=7, color=BLACK)

ax.text(5, 0.15, 'Three-category taxonomy of the NUCLEAR stop set',
        ha='center', fontsize=8, color=DARK, style='italic')

fig.tight_layout()
fig.savefig(f'{FIGS}/fig12_nuclear.png', dpi=250, bbox_inches='tight')
plt.close()
print('fig12 done')

print('\nAll figures saved to', FIGS)
