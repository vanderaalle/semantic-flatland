# Isotopiser

Interactive Greimasian isotopy detection for English text.

## Files

- `isotopiser.html` — browser frontend (open directly, no web server needed)
- `isotopiser_server.py` — local Flask backend
- `isotopy_patched.py` — `isotopy.py` extended with `build_rings_from_dicts()`; **replace your `isotopy.py` with this file**

## Setup

```bash
pip install flask simplemma requests nltk
python isotopiser_server.py [--mw-key YOUR_KEY] [--port 5000]
```

Open `isotopiser.html` in a browser. The server must be running on `localhost:5000`.

## Merriam-Webster API key

A free key is required for good results. Without it the tool falls back to Wiktionary + NLTK WordNet, which produces significant homonymy noise (wrong word senses dominating clusters).

Get a free key at **https://dictionaryapi.com/** — request access to the **Collegiate Dictionary** (not Thesaurus or Medical). The free tier allows 1000 requests/day, which is sufficient for interactive use.

Paste the key into the field in the UI. It is stored in `localStorage` and persists across sessions. It is only ever sent to `dictionaryapi.com`.

## Pipeline

The pipeline is a simplified version of `isotopy.py` from the BSM project, adapted for arbitrary English input:

1. **Tokenisation and POS tagging** (NLTK) — keep nouns, verbs, adjectives only
2. **Lemmatisation** (simplemma)
3. **Definition fetching** — Wiktionary REST API + NLTK WordNet + Merriam-Webster (if key present)
4. **Seme extraction** — `extract_words()` from `isotopy.py`, filtered through `NUCLEAR_BASE`
5. **Two-pass Lesk sense selection** — `build_rings_from_dicts()`, identical logic to `build_rings()`
6. **IDF weighting and L1+L2 profile expansion**
7. **Pairwise edge scoring** (min-IDF overlap)
8. **Complete-linkage clustering** at three tiers, thresholds auto-scaled from edge distribution
9. **Lemma-uniqueness pass** — each lemma assigned to its strongest cluster only
10. **Percentile tier reassignment** — strong/medium/weak relative to the passage score distribution

## Differences from the Potocki pipeline

The method is identical in both cases: two-pass Lesk sense selection, IDF weighting,
L1+L2 profile expansion, complete-linkage clustering, NUCLEAR_BASE filtering.
The differences are purely in resources and calibration:

| Feature | `isotopy.py` (Potocki) | Isotopiser (general) |
|---|---|---|
| Lexical resources | Wiktionary + WN 3.1 + MW + W1828 | Wiktionary + WN (NLTK) + MW (optional) |
| MW POS hints | Hardcoded per Potocki corpus | NLTK POS tagger (correct generalisation) |
| Thresholds | Calibrated on Potocki corpus | Auto-scaled per passage |

The critical absence is **Webster 1828**. W1828 does two things: it adds semes
from a period-appropriate register (theological/gothic), and — more importantly —
it enriches the Lesk context used for sense disambiguation across all resources.
Without it, the Lesk context is thinner and wrong senses are more likely to survive
for words with strong modern vs. archaic sense splits (`living`, `flesh`, `hang`, `body`).

## Known limitations

**Homonymy** is the main quality constraint. Words with multiple senses (`lead`, `sound`, `break`, `prompt`) may cluster on the wrong sense despite POS-guided MW lookup and Lesk disambiguation. This is an unsolved problem in computational lexicography; MW + W1828 together resolve most cases for the Potocki corpus but general text will always have residual noise.

**WordNet taxonomy noise**: NLTK WordNet glosses contain biology/geography meta-vocabulary (`genus`, `tropical`, `american`, etc.) that can produce spurious seme bridges. The extended `NUCLEAR_BASE` in `isotopy_patched.py` suppresses the most common cases.

**simplemma artifacts**: `thinking` → `thinke`, `swinging` → `swinge`. Both are blocked in `NUCLEAR_BASE`.

**Input limit**: 250 words. Longer texts can be split into passages and analysed separately.

## Part of

*Basic Semiotic Modelling* (Valle, forthcoming)
