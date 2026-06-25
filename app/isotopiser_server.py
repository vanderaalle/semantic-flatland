"""
isotopiser_server.py
====================
Local Flask backend for the Isotopiser HTML tool.

Usage:
    pip install flask simplemma requests nltk
    python isotopiser_server.py [--mw-key YOUR_KEY]

    isotopy.py (patched with build_rings_from_dicts) must be in the same directory.
"""

import os, re, sys, json, time, argparse, threading
from collections import defaultdict
from flask import Flask, request, jsonify, send_from_directory

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from isotopy import (
    _wk_fetch_single,
    _mw_extract_senses, _MW_BASE, _MW_SPELLING,
    build_rings_from_dicts, cluster_isotopies,
    RingResult, ClusterResult,
    FRAME,
    T_STRONG, T_MEDIUM, T_WEAK,
)

import requests as _requests
import simplemma
import nltk

for _res in ('wordnet', 'omw-1.4'):
    try:
        nltk.data.find(f'corpora/{_res}')
    except LookupError:
        print(f"Downloading NLTK resource: {_res} ...")
        nltk.download(_res, quiet=True)
from nltk.corpus import wordnet as _wn

MW_API_KEY = os.environ.get("MW_API_KEY", "")
MAX_WORDS  = 250
PORT       = 5000

# Penn Treebank tag -> Merriam-Webster POS string
_TB_TO_MW = {
    'NN': 'noun', 'NNS': 'noun', 'NNP': 'noun', 'NNPS': 'noun',
    'VB': 'verb', 'VBD': 'verb', 'VBG': 'verb',
    'VBN': 'verb', 'VBP': 'verb', 'VBZ': 'verb',
    'JJ': 'adjective', 'JJR': 'adjective', 'JJS': 'adjective',
}

# POS tags to keep — nouns, verbs, adjectives only (no adverbs: too noisy)
_CONTENT_TAGS = {'NN','NNS','NNP','NNPS','VB','VBD','VBG','VBN','VBP','VBZ','JJ','JJR','JJS'}

import nltk as _nltk_pos
_nltk_pos.download('averaged_perceptron_tagger_eng', quiet=True)
_nltk_pos.download('punkt_tab', quiet=True)
from nltk import pos_tag as _pos_tag

# ---------------------------------------------------------------------------
# Lemmatiser
# ---------------------------------------------------------------------------

def _lem(w):
    return simplemma.lemmatize(w.lower(), lang='en')

# ---------------------------------------------------------------------------
# WordNet fetcher via NLTK — produces same JSON envelope as fetch_wordnet()
# ---------------------------------------------------------------------------

def _fetch_wn_nltk(lemmas):
    defs = {}
    for lemma in lemmas:
        syns = _wn.synsets(lemma) or _wn.synsets(_lem(lemma))
        glosses = [re.sub(r'"[^"]*"', '', s.definition()).strip()
                   for s in syns[:4] if s.definition()]
        if glosses:
            defs[lemma] = {
                'raw_definitions':  glosses,
                'definition_words': [w for w in re.findall(r'[a-z]+', ' '.join(glosses).lower())
                                     if len(w) > 2],
            }
    return {'definitions': defs}

# ---------------------------------------------------------------------------
# Wiktionary fetcher — wraps isotopy._wk_fetch_single with caching
# ---------------------------------------------------------------------------

_wk_cache = {}
_wk_lock  = threading.Lock()

def _fetch_wk(lemmas):
    defs = {}
    for lemma in lemmas:
        with _wk_lock:
            if lemma in _wk_cache:
                defs[lemma] = _wk_cache[lemma]
                continue
        time.sleep(0.2)
        result = _wk_fetch_single(lemma)
        with _wk_lock:
            _wk_cache[lemma] = result
        if result.get('raw_definitions'):
            defs[lemma] = result
    return {'definitions': defs}

# ---------------------------------------------------------------------------
# MW fetcher — wraps isotopy._mw_extract_senses with caching
# ---------------------------------------------------------------------------

_mw_cache = {}

def _fetch_mw(lemmas, api_key, pos_map=None):
    """pos_map: {lemma: preferred_pos_string} e.g. {'lead': 'verb', 'sound': 'adjective'}"""
    defs = {}
    if not api_key:
        return {'definitions': {}}
    for lemma in lemmas:
        cache_key = (lemma, (pos_map or {}).get(lemma))
        if cache_key in _mw_cache:
            if _mw_cache[cache_key]:
                defs[lemma] = _mw_cache[cache_key]
            continue
        try:
            lookup = _MW_SPELLING.get(lemma, lemma)
            r = _requests.get(f"{_MW_BASE}{lookup}?key={api_key}", timeout=6)
            r.raise_for_status()
            preferred = (pos_map or {}).get(lemma)
            senses = _mw_extract_senses(r.json(), lemma, preferred_pos=preferred)
            if senses:
                entry = {
                    'raw_definitions':  senses,
                    'definition_words': [w for w in re.findall(r'[a-z]+', ' '.join(senses).lower())
                                         if len(w) > 2],
                }
                _mw_cache[cache_key] = entry
                defs[lemma] = entry
            else:
                _mw_cache[cache_key] = None
        except Exception as e:
            print(f"  MW [{lemma}]: {e}")
            _mw_cache[cache_key] = None
    return {'definitions': defs}

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

# Stopwords that survive len>3 but must not become lemmas
_STOPWORDS = {
    'they','them','their','there','these','those','then','than','that','this',
    'when','where','what','which','whom','whose','while','with','from','into',
    'have','been','were','will','would','could','should','shall','might','must',
    'also','even','just','very','well','much','more','most','some','each','both',
    'only','such','over','under','upon','after','before','above','below',
    'about','around','through','between','because','however','therefore',
    'although','though','whether','another','every','other','same',
}

def analyse(text, mw_key=''):
    tokens = re.findall(r'[a-z]+', text.lower())
    # POS-filter: keep only nouns, verbs, adjectives
    tagged = _pos_tag(tokens)
    lemmas = list(dict.fromkeys(
        _lem(t) for t, pos in tagged
        if pos in _CONTENT_TAGS
        and len(t) > 3
        and t       not in FRAME
        and _lem(t) not in FRAME
        and len(_lem(t)) > 3
    ))

    if not lemmas:
        return _empty(0)

    print(f"  {len(lemmas)} lemmas — fetching definitions ...")
    # Build POS map for MW sense selection: lemma -> MW POS string
    pos_map = {_lem(t): _TB_TO_MW[pos]
               for t, pos in tagged
               if _lem(t) in lemmas and pos in _TB_TO_MW}
    wk = _fetch_wk(lemmas)
    wn = _fetch_wn_nltk(lemmas)
    mw = _fetch_mw(lemmas, mw_key, pos_map=pos_map)

    covered = {l for l in lemmas
               if wk['definitions'].get(l) or wn['definitions'].get(l) or mw['definitions'].get(l)}
    missing = [l for l in lemmas if l not in covered]

    if len(covered) < 2:
        return _empty(len(lemmas), missing)

    rings = build_rings_from_dicts(wk, wn, mw, verbose=False)

    # Auto-scale thresholds from actual edge score distribution.
    # Use percentiles of raw_edges so clustering adapts to any resource config.
    if rings.raw_edges:
        scores = sorted(rings.raw_edges.values(), reverse=True)
        n = len(scores)
        # strong: top 20th percentile, medium: 40th, weak: 65th
        t_strong = scores[min(int(n * 0.20), n-1)]
        t_medium = scores[min(int(n * 0.40), n-1)]
        t_weak   = scores[min(int(n * 0.65), n-1)]
    else:
        t_strong, t_medium, t_weak = T_STRONG, T_MEDIUM, T_WEAK
    tiers = cluster_isotopies(rings, t_strong, t_medium, t_weak, verbose=False)

    # Collect clusters — deduplicate across tiers, then enforce lemma uniqueness
    seen, clusters_out = set(), []
    for tier in tiers:                          # strong → medium → weak
        for cl in tier.clusters:
            key = frozenset(cl)
            if key in seen:
                continue
            seen.add(key)
            agg = defaultdict(float)
            for l in cl:
                for w, s in rings.expanded.get(l, {}).items():
                    agg[w] += s
            top = sorted(agg, key=agg.__getitem__, reverse=True)[:8]
            clusters_out.append({
                'members':   sorted(cl),
                'score':     round(sum(agg.values()), 2),
                'semes': top,
                'tier':      tier.label.lower(),
            })

    clusters_out.sort(key=lambda c: -c['score'])

    # Lemma uniqueness: assign each lemma to its strongest cluster only
    assigned, unique = set(), []
    for cl in clusters_out:
        members = [m for m in cl['members'] if m not in assigned]
        if len(members) >= 2:
            assigned.update(members)
            cl['members'] = members
            unique.append(cl)
    clusters_out = unique

    # Percentile tiers
    if clusters_out:
        scores = sorted([c['score'] for c in clusters_out], reverse=True)
        n = len(scores)
        s_cut = scores[max(0, int(n * 0.25) - 1)]
        m_cut = scores[max(0, int(n * 0.60) - 1)]
        for cl in clusters_out:
            cl['tier'] = 'strong' if cl['score'] >= s_cut else 'medium' if cl['score'] >= m_cut else 'weak'

    return {
        'total_lemmas':  len(lemmas),
        'in_dictionary': len(covered),
        'clusters':      clusters_out,
        'missing':       missing[:40],
        'resources':     {'wordnet': True, 'wiktionary': True, 'mw': bool(mw_key)},
    }

def _empty(total, missing=None):
    return {'total_lemmas': total, 'in_dictionary': 0, 'clusters': [],
            'missing': missing or [], 'resources': {'wordnet': True, 'wiktionary': True, 'mw': False}}

# ---------------------------------------------------------------------------
# Flask
# ---------------------------------------------------------------------------

app = Flask(__name__, static_folder='.')

@app.route('/')
def index():
    return send_from_directory('.', 'isotopiser.html')

@app.route('/analyse', methods=['POST'])
def analyse_endpoint():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'Missing text'}), 400
    text = data['text'].strip()
    if len(text.split()) > MAX_WORDS:
        return jsonify({'error': f'Text too long (max {MAX_WORDS} words)'}), 400
    mw_key = data.get('mw_key', '') or MW_API_KEY
    try:
        return jsonify(analyse(text, mw_key=mw_key))
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.after_request
def cors(r):
    r.headers['Access-Control-Allow-Origin']  = '*'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    r.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    return r

@app.route('/analyse', methods=['OPTIONS'])
def options():
    return '', 204

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mw-key', default='')
    parser.add_argument('--port', type=int, default=PORT)
    args = parser.parse_args()
    if args.mw_key:
        MW_API_KEY = args.mw_key
    print(f"\nIsotopiser  →  http://localhost:{args.port}")
    print(f"Resources: Wiktionary + NLTK WordNet" + (" + MW" if MW_API_KEY else ""))
    print(f"isotopy.py: {os.path.abspath('isotopy.py')}\n")
    app.run(port=args.port, debug=False)
