# Isotopy Detection Pipeline

Part of: *Basic Semiotic Modelling* — Andrea Valle (Logos Verlag, forthcoming)
Module: `isotopy.py`

---

## Overview

The pipeline detects Greimasian **isotopies** in a prose passage by treating
each content word (lemma) as a bundle of **semes** — minimal semantic units
drawn from four lexical resources — and measuring how much those bundles
overlap across pairs of lemmas.  Pairs with strong overlap share semic
content; clusters of mutually overlapping pairs constitute an isotopy.

The result is a three-tier weighted similarity graph (STRONG / MEDIUM / WEAK)
that can be compared across corpora or across different choices of lexical
resource.

---

## Theoretical Grounding

Greimas defines **isotopy** as the redundant iteration of the same seme (or
semic category) across a stretch of text.  A text is isotopic when its
lexemes keep returning to the same semantic ground — even without sharing
surface forms.

This pipeline operationalises that idea computationally:

- Each lemma is replaced by a **seme profile**: a set of semes weighted by
  their discriminating power (IDF) across the passage.
- Two lemmas are isotopically related to the degree their profiles **overlap**.
- Transitive overlap — via L2 expansion — captures indirect but structurally
  motivated connections.

No parsing, no dependency trees, no neural embeddings.  The approach is
deliberately surface-based and dictionary-driven, consistent with Greimas's
own understanding of the lexicon as the primary site of semantic organisation.

---

## Files and Layout

```
projects/isotopy/
├── isotopy.py                  # full pipeline module
├── pipeline.md                 # this document
├── data/
│   ├── corpus/
│   │   ├── manuscript.txt      # Potocki, Day 1 gallows passage
│   │   └── the_fall.txt        # Poe, opening of The Fall of the House of Usher
│   ├── wn3.1.dict/             # WordNet 3.1 dict files (local)
│   ├── potocki_definitions_wikt.json
│   ├── potocki_definitions_wn.json
│   ├── potocki_definitions_mw.json
│   ├── potocki_definitions_w1828.json
│   ├── potocki_results.json    # saved pipeline output
│   ├── poe_definitions_*.json
│   └── poe_results.json
└── notebooks/
    ├── fetch_mw.ipynb
    ├── fetch_wordnet.ipynb
    ├── fetch_wiktionary.ipynb
    ├── fetch_w1828.ipynb
    └── pipeline_walkthrough.ipynb
```

---

## Stage 0 — Lemma Extraction

```python
lemma_map = build_lemma_map(passage_text)
```

1. Tokenise the passage with `re.findall(r'[a-z]+', text.lower())`.
2. Drop tokens shorter than 3 characters and members of `_PASSAGE_STOPS`
   (articles, prepositions, auxiliaries, numerals, common adverbs).
3. Lemmatise each token with `simplemma` (English), then apply
   `_LEMMA_CORRECTIONS` to fix known simplemma failures
   (`hanging→hang`, `thought→think`, `unjustly→unjust`, etc.).
4. Group surface forms under their lemma; preserve first-occurrence order.

**Output:** `dict[lemma → list[surface_forms]]`
Both corpus files have a metadata block after the first blank line;
trim with `.split('\n\n')[0]` before calling `build_lemma_map`.

---

## Stage 1 — Definition Fetching

Four lexical resources are fetched independently and stored as JSON:

| Resource | File suffix | Notes |
|---|---|---|
| Merriam-Webster Collegiate | `_mw.json` | REST API; key required |
| WordNet 3.1 | `_wn.json` | Local dict files; no network |
| Webster 1828 | `_w1828.json` | Scraped from webstersdictionary1828.com |
| Wiktionary (English) | `_wikt.json` | REST API; no key required |

Each JSON has the structure:
```json
{
  "lemma_map": { "lemma": ["surface1", "surface2"] },
  "definitions": {
    "lemma": {
      "raw_definitions": ["Def text 1.", "Def text 2."],
      "definition_words": ["word1", "word2"]
    }
  }
}
```

**Fetch notebooks** in `notebooks/` handle one resource each; configure
`CORPUS_PREFIX`, `PASSAGE_FILE`, and `META_TRIM` at the top then run all
cells.  Rate-limiting is handled inside the fetchers.

**Wiktionary** stores at most 6 `raw_definitions` per lemma (any beyond the
sixth are later technical or mathematical senses best ignored).

**Webster 1828** is period-appropriate for Potocki (ca. 1797–1815) and is
used as a *primary* resource alongside WN and MW — not as a supplement.  Its
inclusion promotes the supernatural isotopy (ghost–living–vampire) from WEAK
to STRONG tier because 1828 foregrounds the body/soul opposition that modern
dictionaries bury.

---

## Stage 2 — Build Rings (`build_rings`)

```python
rings = build_rings(path_wk, path_wn, path_mw, path_w1828)
```

"Rings" = concentric IDF-weighted seme profiles around each lemma,
analogous to the rings of context that radiate outward from a word's core
meaning.

### 2a. Nuclear set

```
nuclear = FRAME ∪ lemma_set
```

`FRAME` is a hand-curated set of semantic universals and definitional
meta-words that are too general to carry semic weight in any corpus
(`person`, `state`, `act`, `thing`, …).  The passage lemmas themselves
are added at runtime so that a lemma cannot bridge its own definitions
(circularity prevention).

### 2b. Pass 1 — Lesk context construction

For each lemma, merge the first 3 raw definitions from each of the four
resources (without Lesk filtering).  Count how many lemmas each token
appears in (`df`).  The **Lesk context** is:

```
C_lesk = lemma_set ∪ { w : df(w) ≤ LESK_DF_MAX }
```

This gives a passage-specific vocabulary of both the corpus lemmas and the
rarer definitional words that are likely to be precise and discriminating.
`LESK_DF_MAX = 10` by default.

### 2c. Pass 2 — Lesk-ranked sense selection

For each lemma and each resource, `auto_select_def` computes the Lesk
overlap score of every available definition against `C_lesk`:

```
lesk_score(def) = |tokens(def) \ {lemma}  ∩  C_lesk|
```

Definitions that are redirects, too short (<3 tokens), or tautological
(any token shares the first 5 characters of the lemma) are discarded.
The remaining definitions are ranked by score; the top `LESK_TOP_N = 2`
per resource are concatenated.  The four resources are then merged into a
single definition string per lemma.

**Cross-resource consistency gate for Wiktionary:**
Wiktionary senses with Lesk score 0 are ranked last and fall outside the
top-2 cut.  Because Wiktionary's vocabulary only appears in the Lesk
context if it was first established by WN, MW, or W1828 (in pass 1),
Wiktionary can *strengthen* semes already present but cannot introduce
new ones.  W1828 is treated as a primary resource; its vocabulary
participates in the gate on an equal footing with WN and MW.

### 2d. Seme extraction and IDF filtering

Each merged definition string is tokenised and lemmatised.  Tokens in
`nuclear` are removed.  The surviving tokens are the **seme candidates**.

IDF weights:

```
idf(w) = log( N / df(w) )
```

Semes appearing in more than `IDF_CUTOFF = 0.45` of all definitions
(i.e., `df > 0.45 × N`) are discarded as too widespread to be
discriminating.

### 2e. Profile expansion (L1 + L2)

Each lemma receives an **expanded seme profile**:

```
profile(l) = Σ_{w ∈ L1(l)} idf(w)  +  0.5 × Σ_{w ∈ L2(l)} idf(w)
```

- **L1**: semes appearing directly in lemma `l`'s merged definition.
- **L2**: semes appearing in the definitions of *non-corpus* words that
  appear in `l`'s L1 definition.  Corpus lemmas are excluded from L2
  intermediates (circularity fix: if *tear*'s definition mentions *force*,
  *force*'s semes are not imported into *tear*'s profile).

L2 expansion adds one degree of definitional depth at half weight,
capturing structurally motivated indirect connections.

### 2f. Edge scoring

For each pair of lemmas `(l1, l2)`:

```
score(l1, l2) = Σ_{w ∈ profile(l1) ∩ profile(l2)}  min(profile(l1)[w], profile(l2)[w])
```

The **min** over shared semes penalises pairs where one side has a weak
semic commitment: both lemmas must strongly exhibit the shared seme for
it to contribute to the edge.  This gives a conservative similarity
measure grounded in the weakest-link principle.

---

## Stage 3 — Clustering (`cluster_isotopies`)

```python
tiers = cluster_isotopies(rings)
```

Complete-linkage clustering on the `raw_edges` graph at three absolute
IDF-unit thresholds:

| Tier | Threshold | Typical content |
|---|---|---|
| STRONG | ≥ 10.0 | Lexically overdetermined isotopies (narrative, argumentation, body) |
| MEDIUM | ≥ 8.0  | Secondary isotopies (motion, institutional frames) |
| WEAK   | ≥ 5.0  | Obliquely evoked isotopies (supernatural, horror) |

Thresholds are absolute (raw IDF-unit scores), not normalised, so that
the multi-scale structure of isotopic evidence is preserved across
corpora.  Lemmas that fall below all thresholds are **isolates** — content
words with no shared semic ground within the passage vocabulary.

For each cluster the top-8 semes (by summed profile weight across cluster
members) are computed and stored.

---

## Stage 4 — Save / Load

```python
# Save
run_pipeline(..., out='data/potocki_results.json')

# Load (no recomputation)
data, tiers = load_results('data/potocki_results.json')
```

The saved JSON contains: `lemmas`, `lemma_words`, `idf`, `expanded`,
`raw_edges` (as `[l1, l2, score]` triples), and `tiers` (clusters with
semes, isolates, label, threshold).

---

## Key Parameters

| Name | Default | Effect |
|---|---|---|
| `IDF_CUTOFF` | 0.45 | Drop semes present in >45% of definitions |
| `LESK_DF_MAX` | 10 | Lesk context ceiling: semes with df > 10 excluded |
| `LESK_TOP_N` | 2 | Senses kept per resource per lemma after Lesk ranking |
| `T_STRONG` | 10.0 | STRONG tier threshold (IDF units) |
| `T_MEDIUM` | 8.0 | MEDIUM tier threshold |
| `T_WEAK` | 5.0 | WEAK tier threshold |

---

## Hermeneutic Notes

**Resource choice is a hermeneutic decision.**  Running the same pipeline
on the same passage with different lexical resources produces different
isotopic structures.  Webster 1828 is period-appropriate for Potocki
(written ca. 1797–1815) and foregrounds semantic oppositions (body/soul,
living/dead) that were primary for readers of the original text but have
been marginalised in modern dictionaries.

**No dependency parsing.**  All stages are surface-based.  This is a
principled choice: Greimas's isotopy is defined at the lexeme level, and
introducing syntactic structure would introduce assumptions about
compositional semantics that the theory does not require.

**Wiktionary as amplifier.**  Wiktionary is included for its coverage of
rare and specialised vocabulary, but its tendency to include technical,
mathematical, and encyclopedic senses makes it unsuitable as an
independent source.  The two-layer consistency gate ensures it amplifies
without introducing noise.

---

## Quick Start

```python
import sys
sys.path.insert(0, '/path/to/projects/isotopy')
from isotopy import build_lemma_map, run_pipeline, load_results

# First time: fetch definitions (run notebooks/fetch_*.ipynb)

# Run pipeline and save
rings, tiers = run_pipeline(
    path_wk   = 'data/potocki_definitions_wikt.json',
    path_wn   = 'data/potocki_definitions_wn.json',
    path_mw   = 'data/potocki_definitions_mw.json',
    path_w1828= 'data/potocki_definitions_w1828.json',
    out       = 'data/potocki_results.json',
)

# Subsequent sessions: load without recomputing
data, tiers = load_results('data/potocki_results.json')
for tier in tiers:
    print(tier['label'], len(tier['clusters']), 'clusters')
```
