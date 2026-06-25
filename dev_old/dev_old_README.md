# dev_old/ — README

This folder holds development and test scripts that are **not part of the
canonical pipeline**. They were written against an earlier or divergent
snapshot of `isotopy.py` and should not be run as-is against the current
codebase without first checking imports and constants. Kept for reference
and possible salvage, not for reproducibility of paper results.

---

## test_freq_nuclear.py

**Purpose.** Tests whether the hand-curated `CAT1_MANUAL` stopword list
(the manually compiled "nuclear Category 1" exclusion set — closed-class
function words, generic frame nouns, etc.) can be replaced by a
data-driven criterion: exclude a word if it is *both* (a) among the
top-2000 English lemmas by corpus frequency (wordfreq/BNC) *and*
(b) has document frequency ≥ `DF_MIN` (default 2) across the passage's
own first-pass definitions.

**What it does.** Runs the full pipeline twice — once with the manual
Cat1 list, once with the frequency-derived list — and compares:
- which manual Cat1 words the frequency criterion catches vs. misses
  (`cat1_covered`, `cat1_missed`)
- which extra words the frequency criterion excludes that Cat1 didn't
  (`cat1_extra`)
- resulting top edges and cluster counts (STRONG/MEDIUM/WEAK) for both

**Self-contained.** Reimplements lemmatization (`simplemma`-based),
Lesk scoring, IDF weighting, and complete-linkage clustering locally
rather than importing from `isotopy.py`. Does not depend on the main
module.

**⚠ W1828 handling.** This script appends W1828 **unconditionally** —
only the *first* raw definition, no Lesk reranking
(`build_merged`: `w28 = W1828.get(lemma, ''); if w28: parts.append(w28)`).
This is the **opposite** of the current `isotopy.py`'s `auto_select_def`,
which applies Lesk scoring uniformly to all four resources including
W1828. **Do not use this script's output as evidence for any claim about
W1828/Lesk behavior in the paper** — it tests the nuclear-list question
only, with W1828 handling held constant on its own (older or simplified)
terms, separate from whatever the canonical pipeline currently does.

**To re-run.** Needs `simplemma` installed and four pre-fetched
definition JSON files (`--wk`, `--wn`, `--mw`, `--w1828`) plus a
frequency list (`--freq`, e.g. `bnc_top2000.json`). Self-contained;
no changes needed to run as long as those inputs exist.

**Status.** Legitimate, well-isolated experiment for the FRAME/nuclear-list
question. Worth keeping as a test artifact. Not authoritative for
anything beyond that question.

---

## make_appendix_graphs.py

**Purpose.** Generates one small star-graph PNG per Potocki-passage
lemma: the lemma in a black node, its top-8 IDF-weighted W1828 semes
radiating out as gray nodes, edge labels showing IDF scores. Intended
as supplementary per-lemma appendix figures, distinct from the
aggregate bipartite graphs already used in the paper.

**⚠ Import mismatch — will likely fail as-is.** Line 21 imports
`LEMMA_MAP`, `NUCLEAR_BASE`, `W1828` directly from `isotopy`:

```python
from isotopy import LEMMA_MAP, NUCLEAR_BASE, W1828
```

The current `isotopy.py` does not expose these as module-level
constants. `NUCLEAR_BASE` was renamed to `FRAME` at some point in the
project's history; `W1828` is not pre-loaded at module scope at all —
it's loaded from a JSON file path and passed as a parameter into
`build_rings()` / `build_rings_from_dicts()` at call time. **Re-check
and fix these imports against whatever `isotopy.py` actually exposes
before running.**

**Third independent lemmatizer.** Has its own hardcoded `IRREGULAR`
dict and suffix-stripping rules, separate from both `isotopy.py`'s
lemmatizer and `test_freq_nuclear.py`'s `simplemma`-based one. May
diverge in edge cases (e.g. irregular plurals not in `IRREGULAR`).

**W1828-only by design.** Uses only `W1828.get(lemma, '')` as the
seme source — not the merged four-resource profile. This appears to
be intentional (the goal is to show W1828's individual contribution
lemma-by-lemma), not a bug. Cannot be used as-is to generate the
equivalent "full pipeline" per-lemma figures.

**Status.** Good idea, currently broken against the canonical module.
Five-minute fix once `isotopy.py` is stabilized post-reconciliation:
repoint the import line at whatever the real constant/loading pattern
is, and decide whether to keep the local lemmatizer or import the
canonical one instead.

---

## make_figures.py

**Purpose.** Generates the full figure set for the original "Computational
Lexicon-Based Isotopy Detection for Dummies" tutorial document — twelve
figures covering the isotopy concept (Fig 1), pipeline overview (Fig 2),
passage annotation (Fig 3), seme extraction walkthrough (Fig 4), clustering
illustration (Fig 9), tier structure (Fig 10), resource comparison heatmaps
(Fig 11a/11b), and the NUCLEAR stop-set taxonomy (Fig 12).

**Confirms the NUCLEAR → FRAME rename.** Fig 12's own title is "Three-category
taxonomy of the **NUCLEAR** stop set," with the same three categories
(semantic universals, domain junk, corpus-lemma semes) that the paper now
documents under the name **FRAME**. Useful corroborating evidence for the
project history: NUCLEAR_BASE was the original name, later renamed.

**⚠ Fig 11's data is illustrative mockup, not computed results.** Lines
526–530: `data_full` is a hand-typed `np.array` of small integers (0/1/2)
used only to drive heatmap colors/symbols (✓/~/–). It is **not** loaded from
any results JSON. Its `isotopies` list (line 521) also doesn't match the
ten pairs used in the paper's actual §4.2/§4.3 matrices — e.g. it includes
`argument–thesis` and `escape–prison`, which aren't in the paper's pair
list, and omits `gallows–hang` and `demon–innocent`, which are. **Do not
treat Fig 11a/11b's numbers as real pipeline output or substitute them for
the figures already built from `potocki_ablation.json`.** This script
predates the actual ablation run and was only ever a mockup of what the
comparison figure should look like.

**Genuinely reusable parts.** Fig 1 (the `ghost`/`demon` shared-seme
illustration) is the same worked example that now opens §2.1 of the paper
via the Paolucci discussion — good candidate to regenerate properly once
the pipeline is stabilized. Fig 4 (definition → seme extraction walkthrough
for `ghost`) and Fig 12 (NUCLEAR/FRAME taxonomy) are similarly good
pedagogical figures worth keeping in some form, once their illustrative
example data is checked against real pipeline output rather than the
hand-typed values currently baked into the script (e.g. Fig 4's W1828
definition text for `ghost` at line 161 is typed directly into the script,
not loaded from `potocki_definitions_w1828.json`).

**Tooling.** Uses `style.py`'s `PlotStyle.book_grayscale()`, consistent
with the paper's actual figure-generation scripts. No dependency on
`isotopy.py` — entirely self-contained illustrative/mockup figures, so it
will run without import errors, unlike the other two scripts in this
folder. The risk here is not breakage but **mistaking placeholder numbers
for verified results**.

**Status.** Source of several useful pedagogical figure *designs*
(Fig 1, Fig 4, Fig 12 especially). Not a source of verified data for
anything quantitative. If any of these figures are revived for the paper
or its supplementary material, replace all hand-typed example data with
values pulled from the stabilized pipeline's actual output first.

---

## Before reusing any file in this folder

1. Confirm the canonical, GitHub-reconciled `isotopy.py` and its actual
   exposed names/constants.
2. Decide, for the paper, whether W1828 is meant to bypass Lesk
   (as `test_freq_nuclear.py` and `make_appendix_graphs.py` both
   separately assume/imply) or be treated uniformly with the other three
   resources (as the current `isotopy.py` `auto_select_def` actually
   does). These files and the main module currently disagree on this
   point — resolve before citing any numbers from any of them in the paper.
3. Re-point imports and lemmatizers to the single canonical source
   rather than letting forks drift further.
4. Treat `make_figures.py`'s Fig 11 data, and any other hand-typed
   illustrative numbers in that script, as mockup only — never as a
   substitute for figures generated from real `*_results.json` /
   `*_ablation.json` output.
