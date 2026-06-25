#!/usr/bin/env python3
"""
consolidate.py
Fetch all definition files and generate results + ablation JSONs
from code/isotopy.py (the stabilised pipeline).

All definitions are fetched fresh — no copying from external sources.

Run from projects/isotopy/code/:
    python3 consolidate.py
"""

import sys, os, json

# ── paths ──────────────────────────────────────────────────────────────────────
HERE   = os.path.dirname(os.path.abspath(__file__))   # .../code/
PROJ   = os.path.dirname(HERE)                         # .../isotopy/
DATA   = os.path.join(PROJ, 'data')
WN_DIR = os.path.join(DATA, 'wn3.1.dict', 'dict')
CORPUS = os.path.join(DATA, 'corpus')

MW_API_KEY = 'e403caca-77ca-47cc-a577-c9a2f198e1e2'

sys.path.insert(0, HERE)
from isotopy import (
    LEMMA_MAP,
    build_lemma_map, fetch_wiktionary, fetch_wordnet, fetch_w1828, fetch_mw,
    run_pipeline, run_ablation,
)

# Corpus-specific lemma maps: use the canonical LEMMA_MAP for Potocki (81 entries),
# build dynamically for other corpora.
_LEMMA_MAP_OVERRIDE: dict[str, dict | None] = {
    'potocki': LEMMA_MAP,   # canonical 81-entry map, not passage-derived
}


def load_passage(filename: str, meta_trim: bool = True) -> str:
    path = os.path.join(CORPUS, filename)
    text = open(path, encoding='utf-8').read().strip()
    if meta_trim:
        text = text.split('\n\n')[0].strip()
    return text


def _skip(path: str, label: str) -> bool:
    """Return True (and print) if file already exists with content."""
    if os.path.exists(path) and os.path.getsize(path) > 500:
        print(f'  skip {label} (already fetched)')
        return True
    return False


def fetch_all_defs(prefix: str, lemma_map: dict) -> tuple[str, str, str, str]:
    """Fetch all 4 resources for a corpus prefix; return (wikt, wn, mw, w1828) paths.
    Skips files that already exist and have content (idempotent)."""

    # WordNet (local, fast)
    wn_out = os.path.join(DATA, f'{prefix}_definitions_wn.json')
    if not _skip(wn_out, f'{prefix} WordNet'):
        print(f'  fetching {prefix} WordNet (local)...')
        fetch_wordnet(lemma_map=lemma_map, dict_dir=WN_DIR, out=wn_out)

    # Wiktionary (REST, no key — 3s delay to avoid 429)
    wikt_out = os.path.join(DATA, f'{prefix}_definitions_wikt.json')
    if not _skip(wikt_out, f'{prefix} Wiktionary'):
        print(f'  fetching {prefix} Wiktionary (REST, 3s/lemma)...')
        fetch_wiktionary(lemma_map=lemma_map, out=wikt_out, delay=3.0)

    # Webster 1828 (HTTP scraping)
    w1828_out = os.path.join(DATA, f'{prefix}_definitions_w1828.json')
    if not _skip(w1828_out, f'{prefix} Webster 1828'):
        print(f'  fetching {prefix} Webster 1828 (~1s/lemma)...')
        fetch_w1828(lemma_map=lemma_map, out=w1828_out, delay=1.0)

    # Merriam-Webster (REST, key required)
    mw_out = os.path.join(DATA, f'{prefix}_definitions_mw.json')
    if not _skip(mw_out, f'{prefix} Merriam-Webster'):
        print(f'  fetching {prefix} Merriam-Webster...')
        fetch_mw(lemma_map=lemma_map, out=mw_out, api_key=MW_API_KEY, delay=0.3)

    return wikt_out, wn_out, mw_out, w1828_out


# ==============================================================================
# MAIN
# ==============================================================================

CORPORA = [
    ('potocki', 'manuscript.txt'),
    ('poe',     'the_fall.txt'),
]

def main():
    for prefix, passage_file in CORPORA:
        print('\n' + '='*60)
        print(prefix.upper())
        print('='*60)

        print(f'\n[1] Building lemma map for {prefix}...')
        if prefix in _LEMMA_MAP_OVERRIDE:
            lemma_map = _LEMMA_MAP_OVERRIDE[prefix]
            print(f'  {len(lemma_map)} lemmas (canonical LEMMA_MAP)')
        else:
            text = load_passage(passage_file, meta_trim=True)
            lemma_map = build_lemma_map(text)
            print(f'  {len(lemma_map)} lemmas (from build_lemma_map)')

        print('\n[2] Fetching definitions...')
        wikt, wn, mw, w1828 = fetch_all_defs(prefix, lemma_map)

        results_out  = os.path.join(DATA, f'{prefix}_results.json')
        ablation_out = os.path.join(DATA, f'{prefix}_ablation.json')

        print(f'\n[3] Running {prefix} pipeline...')
        run_pipeline(
            path_wk    = wikt,
            path_wn    = wn,
            path_mw    = mw,
            path_w1828 = w1828,
            out        = results_out,
            verbose    = True,
        )

        print(f'\n[4] Running {prefix} ablation...')
        run_ablation(
            path_wk     = wikt,
            path_wn     = wn,
            path_mw     = mw,
            path_w1828  = w1828,
            output_path = ablation_out,
            verbose     = True,
        )

    print('\n' + '='*60)
    print('DONE')
    print('='*60)
    for fname in [
        'potocki_definitions_wikt.json', 'potocki_definitions_wn.json',
        'potocki_definitions_mw.json',   'potocki_definitions_w1828.json',
        'poe_definitions_wikt.json',     'poe_definitions_wn.json',
        'poe_definitions_mw.json',       'poe_definitions_w1828.json',
        'potocki_results.json',          'potocki_ablation.json',
        'poe_results.json',              'poe_ablation.json',
    ]:
        p = os.path.join(DATA, fname)
        status = f'{os.path.getsize(p):>10,} bytes' if os.path.exists(p) else '  MISSING'
        print(f'  {"✓" if os.path.exists(p) else "✗"}  data/{fname:<45}  {status}')


if __name__ == '__main__':
    main()
