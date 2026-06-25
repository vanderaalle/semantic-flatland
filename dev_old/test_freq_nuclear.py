"""
test_freq_nuclear.py
====================
Tests replacing NUCLEAR Category 1 with a data-driven frequency criterion.

Criterion: exclude a word if it is BOTH
  (a) in the top-2000 English lemmas by frequency  (wordfreq / BNC)
  (b) df >= DF_MIN across the 81 first-pass definitions

Compares results against the manual Cat1 baseline.

Run locally:
    pip install simplemma
    python test_freq_nuclear.py \
        --wk  potocki_definitions.json \
        --wn  potocki_definitions_wn.json \
        --mw  potocki_definitions_mw.json \
        --freq bnc_top2000.json

Outputs:
    freq_nuclear_results.json   — for upload back to Claude
"""

import argparse, json, math, re
from collections import Counter, defaultdict
import simplemma

# ── pipeline constants ────────────────────────────────────────────────────────
DF_MIN      = 2      # minimum df for a freq-list word to be excluded
IDF_CUTOFF  = 0.45
T_STRONG    = 10.0
T_MEDIUM    =  8.0
T_WEAK      =  5.0

KEEP_AS_IS = {
    'disembodied','deceased','elevated','alleged','supposed','wicked','sacred',
    'naked','beloved','learned','aged','wretched','blessed','cursed','dead',
    'noted','related','excited','extended','pointed','twisted','granted',
    'printed','matter',
}

def lemmatize(word):
    w = word.lower()
    return w if w in KEEP_AS_IS else simplemma.lemmatize(w, lang='en')

REDIRECT = {'spelling of','plural of','past tense','third-person','simple past',
    'present participle','alternative form','iso 639'}
LESK_STOP = {'the','and','for','not','but','with','from','into','onto','upon',
    'that','this','which','who','what','how','when','where','why','also','such',
    'any','all','more','most','much','many','very','well','even','just','one',
    'two','its','his','her','our','nor','yet','both','each','few','own','off',
    'out','over','can','may','will','shall','must','would','could','should',
    'per','via','those','some','through','within','another','especially'}

DOMAIN_JUNK = {
    'egg','fowl','hatch','incubator','sit','seat','character','mark','symbol',
    'spell','gyrate','advance','follow','order','ship','travel','outside',
    'area','low','pressure','mass','necessity','moral','intellectual','swinge',
    'cinema','radio','television','drama','fish','game','salesman','room',
    'floor','fictional','latin','along','than','dimension','quantity','velocity',
    'produce','provide','fixe','turn','ability','influence','appear','distant',
    'display','group','individual','rank','mind','judge','program','like','new',
    'etc','about','movement','via','through','some','within','support','after',
    'below','above','free','intention','before','sky','rock','stone','earth',
    'ground','surface','structure','frame','widely','diffuse','charge','ahead',
    'six','point','without','those','land','extent',
}

CAT1_MANUAL = {
    'person','human','animal','creature','being','thing','object','state',
    'condition','act','action','cause','place','time','way','part','use','form',
    'type','kind','manner','relate','associate','particular','general','certain',
    'have','characterize','involve','something','someone','people','able',
    'capable','likely','possible','impossible','result','especially','typically',
    'usually','often','various','another','make','take','come','get','put','go',
    'know','give','refer','become','remain','keep','seem','see','say','physical',
    'mental','natural','original','exist','single','find','call','large','small',
    'great','long','high','deep','wide','broad','amount','number','distance',
    'specific','common','similar','true','false','real','actual','apparent',
    'organism','near','move',
}

def extract_words(text, lemma, nuclear):
    return [lw for w in re.findall(r'[a-z]+', text.lower())
            for lw in [lemmatize(w)]
            if lw not in nuclear and len(lw) > 2 and lw != lemma]

def _lt(text):
    return [lemmatize(w) for w in re.findall(r'[a-z]+', text.lower())
            if lemmatize(w) not in LESK_STOP and len(w) > 2]

def is_taut(d, l): return any(t[:5] == l[:5] for t in _lt(d))

def build_merged(nuclear, wk, wn, mw, W1828, lemmas, lemma_set):
    def fp(lemma):
        parts = []
        for data in [wk, wn, mw]:
            for d in data['definitions'].get(lemma, {}).get('raw_definitions', [])[:3]:
                if not (any(m in d.lower() for m in REDIRECT) or len(d.split()) <= 2):
                    parts.append(d)
        return ' | '.join(parts)
    lw0 = {l: extract_words(fp(l), l, nuclear) for l in lemmas}
    wc0 = Counter(w for ws in lw0.values() for w in set(ws))
    lctx = lemma_set | {w for w, c in wc0.items() if c <= 10}
    def ls(d, l): return len(set(t for t in _lt(d) if t != l) & lctx)
    merged = {}
    for lemma in lemmas:
        parts = []
        for data in [wk, wn, mw]:
            defs = data['definitions'].get(lemma, {}).get('raw_definitions', [])
            cands = [(d, ls(d, lemma)) for d in defs
                     if not (any(m in d.lower() for m in REDIRECT) or len(d.split()) <= 2)
                     and not is_taut(d, lemma)]
            cands.sort(key=lambda x: x[1], reverse=True)
            parts.extend(d for d, _ in cands[:2])
        w28 = W1828.get(lemma, '')
        if w28: parts.append(w28)
        merged[lemma] = ' | '.join(parts)
    return merged

def run_pipeline(nuclear, wk, wn, mw, W1828, lemmas, lemma_set):
    N = len(lemmas)
    merged = build_merged(nuclear, wk, wn, mw, W1828, lemmas, lemma_set)
    lw = {l: extract_words(merged[l], l, nuclear) for l in lemmas}
    wc = Counter(w for ws in lw.values() for w in set(ws))
    idf = {w: math.log(N/c) for w, c in wc.items() if c <= N * IDF_CUTOFF}
    def expand(l):
        p = defaultdict(float)
        for w in lw.get(l, []):
            if w in idf: p[w] += idf[w]
        for w in lw.get(l, []):
            if w in lw and w not in lemma_set:
                for w2 in lw[w]:
                    if w2 in idf and w2 != l: p[w2] += 0.5 * idf[w2]
        return dict(p)
    exp = {l: expand(l) for l in lemmas}
    edges = {}
    for i, l1 in enumerate(lemmas):
        for l2 in lemmas[i+1:]:
            sh = set(exp[l1]) & set(exp[l2])
            if sh: edges[f"{l1}|{l2}"] = sum(min(exp[l1][w], exp[l2][w]) for w in sh)
    return edges, lw, idf

def complete_linkage(edges, lemmas, t):
    adj = defaultdict(set)
    for key, s in edges.items():
        l1, l2 = key.split('|')
        if s >= t: adj[l1].add(l2); adj[l2].add(l1)
    visited = set(); clusters = []
    for seed in sorted(lemmas):
        if seed in visited or not adj[seed]: continue
        c = {seed}; cands = set(adj[seed]); changed = True
        while changed:
            changed = False
            for x in list(cands):
                if all(x in adj[m] for m in c):
                    c.add(x); cands = cands & adj[x]; changed = True; break
        if len(c) > 1: clusters.append(sorted(c)); visited.update(c)
    for l in [l for l in lemmas if l not in visited]:
        for n in adj[l]:
            if n not in visited: clusters.append(sorted([l,n])); visited.update([l,n]); break
    isolates = sorted(l for l in lemmas if not adj[l])
    return [c for c in clusters if len(c) > 1], isolates

def cluster_summary(edges, lemmas):
    result = {}
    for t, lab in [(T_STRONG,'strong'),(T_MEDIUM,'medium'),(T_WEAK,'weak')]:
        cl, iso = complete_linkage(edges, lemmas, t)
        result[lab] = {'clusters': cl, 'n_clusters': len(cl), 'n_isolates': len(iso)}
    return result

def top_edges(edges, n=10):
    return [[k.replace('|','—'), round(v,2)]
            for k,v in sorted(edges.items(), key=lambda x:x[1], reverse=True)[:n]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wk',    default='potocki_definitions.json')
    parser.add_argument('--wn',    default='potocki_definitions_wn.json')
    parser.add_argument('--mw',    default='potocki_definitions_mw.json')
    parser.add_argument('--w1828', default='potocki_definitions_w1828.json')
    parser.add_argument('--freq',  default='bnc_top2000.json')
    parser.add_argument('--out',   default='freq_nuclear_results.json')
    args = parser.parse_args()

    with open(args.wk) as f: wk = json.load(f)
    with open(args.wn) as f: wn = json.load(f)
    with open(args.mw) as f: mw = json.load(f)
    with open(args.freq) as f: raw_freq = json.load(f)

    # Build W1828 as {lemma: first_raw_definition} from JSON file
    with open(args.w1828) as f: _w28_data = json.load(f)
    W1828 = {
        lemma: defs['raw_definitions'][0]
        for lemma, defs in _w28_data['definitions'].items()
        if defs.get('raw_definitions')
    }

    lemmas    = sorted(wk['definitions'].keys())
    lemma_set = set(lemmas)
    N         = len(lemmas)

    # ── lemmatize frequency list ──────────────────────────────────────────────
    freq_lemmas = []
    seen = set()
    for w in raw_freq:
        if not re.match(r'^[a-z]+$', w.lower()): continue
        lw = lemmatize(w)
        if lw not in seen and len(lw) > 1:
            freq_lemmas.append(lw)
            seen.add(lw)
    freq_set = set(freq_lemmas)
    print(f"Freq list: {len(raw_freq)} raw → {len(freq_lemmas)} lemmatized")

    # ── compute df counts ─────────────────────────────────────────────────────
    word_lemmas = defaultdict(set)
    for lemma in lemmas:
        parts = []
        for data in [wk, wn, mw]:
            for d in data['definitions'].get(lemma, {}).get('raw_definitions', [])[:3]:
                if not (any(m in d.lower() for m in REDIRECT) or len(d.split()) <= 2):
                    parts.append(d)
        w28 = W1828.get(lemma, '')
        if w28: parts.append(w28)
        for w in re.findall(r'[a-z]+', ' '.join(parts).lower()):
            lw = lemmatize(w)
            if len(lw) > 2 and lw not in lemma_set:
                word_lemmas[lw].add(lemma)
    df_counts = {w: len(lms) for w, lms in word_lemmas.items()}

    # ── build nuclear: freq criterion + domain junk ───────────────────────────
    freq_excluded = {w for w in freq_set if df_counts.get(w, 0) >= DF_MIN}
    nuclear_freq  = freq_excluded | DOMAIN_JUNK | lemma_set

    # coverage stats
    cat1_covered = CAT1_MANUAL & freq_excluded
    cat1_missed  = CAT1_MANUAL - freq_excluded
    cat1_extra   = freq_excluded - CAT1_MANUAL

    print(f"\nFrequency criterion (DF_MIN={DF_MIN}):")
    print(f"  Excluded: {len(freq_excluded)} words")
    print(f"  Cat1 covered: {len(cat1_covered)}/{len(CAT1_MANUAL)}")
    print(f"  Cat1 missed:  {sorted(cat1_missed)}")
    print(f"  Extra beyond Cat1 (first 20): {sorted(cat1_extra)[:20]}")

    # ── baseline: manual Cat1 ─────────────────────────────────────────────────
    nuclear_cat1 = CAT1_MANUAL | DOMAIN_JUNK | lemma_set
    print("\nRunning BASELINE (manual Cat1)...")
    e_base, lw_base, idf_base = run_pipeline(nuclear_cat1, wk, wn, mw, W1828, lemmas, lemma_set)
    print("Running FREQ criterion...")
    e_freq, lw_freq, idf_freq = run_pipeline(nuclear_freq, wk, wn, mw, W1828, lemmas, lemma_set)

    results = {
        'df_min':   DF_MIN,
        'n_lemmas': N,
        'freq_excluded_count': len(freq_excluded),
        'cat1_covered': len(cat1_covered),
        'cat1_total':   len(CAT1_MANUAL),
        'cat1_missed':  sorted(cat1_missed),
        'cat1_extra_sample': sorted(cat1_extra)[:30],
        'baseline': {
            'nuclear_size': len(nuclear_cat1),
            'idf_vocab':    len(idf_base),
            'top_edges':    top_edges(e_base),
            'clusters':     cluster_summary(e_base, lemmas),
        },
        'freq_criterion': {
            'nuclear_size': len(nuclear_freq),
            'idf_vocab':    len(idf_freq),
            'top_edges':    top_edges(e_freq),
            'clusters':     cluster_summary(e_freq, lemmas),
        },
    }

    # edge comparison
    top_base = {k for k,_ in sorted(e_base.items(),key=lambda x:x[1],reverse=True)[:20]}
    top_freq = {k for k,_ in sorted(e_freq.items(),key=lambda x:x[1],reverse=True)[:20]}
    results['edge_diff'] = {
        'in_base_not_freq': [k.replace('|','—') for k in top_base - top_freq],
        'in_freq_not_base': [k.replace('|','—') for k in top_freq - top_base],
    }

    with open(args.out, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {args.out}")

    # print summary
    print("\n=== BASELINE ===")
    for e in results['baseline']['top_edges'][:8]:
        print(f"  {e[1]:6.2f}  {e[0]}")
    for lab in ['strong','medium','weak']:
        c = results['baseline']['clusters'][lab]
        print(f"  {lab.upper()}: {c['n_clusters']} clusters  {c['n_isolates']} isolates")

    print("\n=== FREQ CRITERION ===")
    for e in results['freq_criterion']['top_edges'][:8]:
        print(f"  {e[1]:6.2f}  {e[0]}")
    for lab in ['strong','medium','weak']:
        c = results['freq_criterion']['clusters'][lab]
        print(f"  {lab.upper()}: {c['n_clusters']} clusters  {c['n_isolates']} isolates")


if __name__ == '__main__':
    main()
