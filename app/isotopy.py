# =============================================================================
# isotopy.py
# Lexicon-based Greimasian isotopy detection
# =============================================================================
# Part of: Basic Semiotic Modelling (Valle, Logos Verlag)
# Corpus:  Jan Potocki, The Manuscript Found in Saragossa, Day 1 (81 lemmas)
#
# USAGE
#   from modules.isotopy import run_pipeline
#   run_pipeline('potocki_definitions.json',
#                'potocki_definitions_wn.json',
#                'potocki_definitions_mw.json')
#
# FETCHING DEFINITIONS (one-time, outputs saved as JSON)
#   fetch_wiktionary()  →  potocki_definitions.json
#   fetch_wordnet()     →  potocki_definitions_wn.json     (needs local wn3.1.dict/dict)
#   fetch_mw()          →  potocki_definitions_mw.json     (needs MW_API_KEY)
#   W1828 is embedded inline — no network call required
#
# =============================================================================
# MANUAL OVERRIDES — POTOCKI DAY 1
# ---------------------------------
# The final pipeline uses zero manual overrides.  All sense-selection is
# automatic via three successive stages:
#
#   Stage 1 — Tautology detection (stem[:5] match):
#     gyration   MW gives "an act of gyrating" → circular, rejected
#
#   Stage 2 — Lesk ranking (passage-context overlap, df ≤ 10 threshold):
#     corpse     MW sense 0 was metaphorical  → Lesk recovers "dead body"
#     revolting  MW sense 0 was verbal (revolt) → Lesk recovers "inspiring disgust"
#     rumour     MW sense 0 was archaic        → Lesk recovers "unverified report"
#     sceptical  MW sense 0 was philosophical  → Lesk recovers "doubting"
#     torment    tautological AND corrected by Lesk
#
#   Stage 3 — Webster 1828 appended (period-appropriate primary senses):
#     body     W1828 primary: "distinguished from the soul or spirit"
#              Modern MW primary: anatomical / "material object" sense
#     flesh    W1828 primary: "body as opposed to spirit; carnal nature"
#              Modern MW buries the body/spirit opposition
#     hang     W1828 primary: "to put to death by suspending by the neck"
#              Modern MW primary: intransitive motion sense
#     living   W1828 primary: "having life; opposed to dead"
#              Modern MW buries the living/dead opposition
#
# RESULT: supernatural isotopy (ghost–living–vampire) promoted from WEAK
# to STRONG tier once W1828 is included.  The choice of lexical resource
# is a hermeneutic decision: it operationalises a claim about which register
# was primary for a reader of the 1804 text.
#
# CROSS-RESOURCE CONSISTENCY GATE (Wiktionary as amplifier)
# ----------------------------------------------------------
# Wiktionary is used as an *amplifier* of semes already established by
# WordNet and Merriam-Webster, not as an independent vocabulary source.
# The gate is implemented in two layers:
#   1. auto_select_def() ranks Wiktionary senses by Lesk overlap with the
#      passage context.  Wiktionary senses with zero passage relevance are
#      ranked last and fall outside the top_n=2 cut.
#   2. The IDF cutoff (df ≤ 0.45 × N) discards any seme — including
#      Wiktionary-unique ones — that is too widespread across definitions
#      to be discriminating.
# Together these ensure that Wiktionary can only *strengthen* semes
# that already appear in WN/MW, not introduce noise from irrelevant senses.
# =============================================================================

import json
import math
import os
import re
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Optional

import simplemma    # pip install simplemma
import requests     # pip install requests  (Wiktionary fetcher only)

# ── API key ───────────────────────────────────────────────────────────────────
MW_API_KEY = ""   # get a free key at https://dictionaryapi.com/

# ── pipeline parameters ───────────────────────────────────────────────────────
IDF_CUTOFF  = 0.45   # semes in > 45 % of definitions are discarded
LESK_DF_MAX = 10     # Lesk context: semes with df > 10 are excluded
LESK_TOP_N  = 2      # top-N senses per resource kept by auto_select_def

T_STRONG = 10.0      # clustering tiers (absolute IDF-unit scores)
T_MEDIUM  =  8.0
T_WEAK    =  5.0

# =============================================================================
# SECTION 1 — LEMMA MAP  (81 content words, Potocki Day 1)
# =============================================================================
# lemma → list of surface forms found in the passage
# Used by all four fetchers as the canonical vocabulary list.

LEMMA_MAP: dict[str, list[str]] = {
    'agree':         ['agree'],
    'approach':      ['approach'],
    'argument':      ['argument'],
    'attest':        ['attested'],
    'avert':         ['averted'],
    'body':          ['bodies'],
    'break':         ['break'],
    'brother':       ['brothers'],
    'catch':         ['caught'],
    'claim':         ['claimed'],
    'consent':       ['consent'],
    'corpse':        ['corpses'],
    'curiosity':     ['curiosity'],
    'demon':         ['demons'],
    'eerie':         ['eerie'],
    'entrance':      ['entrance'],
    'escape':        ['escaped'],
    'execute':       ['executed'],
    'eye':           ['eyes'],
    'fact':          ['fact'],
    'flesh':         ['flesh'],
    'force':         ['forced'],
    'free':          ['free'],
    'gallows':       ['gallows'],
    'gaze':          ['gaze'],
    'ghastly':       ['ghastly'],
    'ghost':         ['ghosts'],
    'gyration':      ['gyrations'],
    'hang':          ['hanging', 'hanged'],
    'hear':          ['heard'],
    'heaven':        ['heaven'],
    'hideous':       ['hideous'],
    'horrified':     ['horrified'],
    'hurry':         ['hurried'],
    'implausible':   ['implausible'],
    'innocent':      ['innocent'],
    'lead':          ['leading'],
    'living':        ['living'],
    'make':          ['made'],
    'meet':          ['met'],
    'mountain':      ['mountains'],
    'nameless':      ['nameless'],
    'night':         ['night'],
    'old':           ['eldest'],
    'possess':       ['possess'],
    'prison':        ['prison'],
    'prompt':        ['prompted'],
    'prove':         ['proving'],
    'refuge':        ['refuge'],
    'revolting':     ['revolting'],
    'rumour':        ['rumour'],
    'say':           ['said'],
    'sceptical':     ['sceptical'],
    'see':           ['seen'],
    'set':           ['set'],
    'sound':         ['sound'],
    'species':       ['species'],
    'spectacle':     ['spectacle'],
    'story':         ['stories'],
    'strange':       ['strange'],
    'supposition':   ['supposition'],
    'swing':         ['swung'],
    'take':          ['taken', 'took'],
    'tale':          ['tales'],
    'tear':          ['tore'],
    'tell':          ['told'],
    'theologian':    ['theologian'],
    'thesis':        ['thesis'],
    'think':         ['thought'],
    'torment':       ['torment'],
    'track':         ['track'],
    'traveller':     ['travellers'],
    'unjust':        ['unjustly'],
    'valley':        ['valley'],
    'vampire':       ['vampire'],
    'vengeance':     ['vengeance'],
    'vulture':       ['vultures'],
    'wayfarer':      ['wayfarers'],
    'widespread':    ['widespread'],
    'wind':          ['wind'],
    'write':         ['written'],
}

# =============================================================================
# SECTION 2 — LEMMATIZER
# =============================================================================

KEEP_AS_IS: set[str] = {
    # Adjectives simplemma over-strips (e.g. disembodied → disembody)
    'disembodied', 'deceased', 'elevated', 'alleged', 'supposed', 'wicked',
    'sacred', 'naked', 'beloved', 'learned', 'aged', 'wretched', 'blessed',
    'cursed', 'dead', 'noted', 'related', 'excited', 'extended', 'pointed',
    'twisted', 'granted', 'printed', 'matter',
}


def lemmatize(word: str) -> str:
    """Lemmatize a single word via simplemma, protecting known over-stripped forms."""
    w = word.lower()
    return w if w in KEEP_AS_IS else simplemma.lemmatize(w, lang='en')


# =============================================================================
# SECTION 3 — FRAME  (definitional frame vocabulary; see BSM §5)
# =============================================================================
# Words unconditionally excluded from seme status.
# Three principled categories:
#   1. Semantic universals — too general for any corpus whatsoever
#   2. Domain junk         — wrong-sense artifacts from specific resources
#   3. Corpus lemmas       — added at runtime as nuclear = FRAME | lemma_set
#                            (passage vocabulary cannot bridge its own definitions)

FRAME: set[str] = {
    # ── 1. Semantic universals ────────────────────────────────────────────────
    'person', 'human', 'animal', 'creature', 'being', 'thing', 'object',
    'state', 'condition', 'act', 'action', 'cause', 'place', 'time',
    'way', 'part', 'use', 'form', 'type', 'kind', 'manner',
    'relate', 'associate', 'particular', 'general', 'certain', 'have',
    'characterize', 'involve', 'something', 'someone', 'people',
    'able', 'capable', 'likely', 'possible', 'impossible', 'result',
    'especially', 'typically', 'usually', 'often', 'various', 'another',
    'make', 'take', 'come', 'get', 'put', 'go', 'know', 'give',
    'use', 'refer', 'cause', 'become', 'remain', 'keep', 'seem',
    'the', 'and', 'for', 'not', 'but', 'with', 'from', 'into', 'onto', 'upon',
    'that', 'this', 'which', 'who', 'what', 'how', 'when', 'where', 'why',
    'also', 'such', 'other', 'any', 'all', 'more', 'most', 'much', 'many',
    'very', 'well', 'even', 'just', 'already', 'still', 'often', 'usually',
    'one', 'two', 'its', 'his', 'her', 'our', 'their', 'your',
    'nor', 'yet', 'both', 'each', 'few', 'own', 'off', 'out', 'over',
    'can', 'may', 'will', 'shall', 'must', 'would', 'could', 'should',
    'see', 'say', 'physical', 'mental', 'natural', 'original', 'exist', 'single',
    'sky', 'rock', 'stone', 'earth', 'ground', 'surface', 'structure', 'frame',
    'find', 'call', 'large', 'small', 'great', 'long',
    'high', 'deep', 'wide', 'broad', 'amount', 'number', 'distance', 'specific',
    'common', 'similar', 'true', 'false', 'real', 'actual', 'apparent',
    'organism', 'near', 'move', 'those', 'per', 'land', 'extent',
    'widely', 'diffuse', 'charge', 'ahead', 'six', 'point', 'without',
    # ── 2. Domain junk ────────────────────────────────────────────────────────
    # MW brooding-hen sense of 'set'
    'egg', 'fowl', 'hatch', 'incubator', 'sit', 'seat',
    # MW 'make'/'write' bridge
    'character', 'mark', 'symbol', 'spell',
    # miscellaneous leaked function/generic words
    'through', 'some', 'within', 'support',
    'free', 'intention', 'after', 'below', 'above',
    'gyrate', 'advance', 'follow', 'order', 'ship', 'travel',
    'before', 'outside', 'area', 'low', 'pressure', 'mass',
    # abstract force-definition words (MW leakage)
    'necessity', 'moral', 'intellectual',
    # simplemma maps 'swinging' → 'swinge', 'thinking' → 'thinke' (archaic Middle English)
    'swinge', 'thinke',
    # MW media context (story/tale)
    'cinema', 'radio', 'television', 'drama',
    # MW wrong senses
    'fish', 'game', 'salesman', 'room', 'floor', 'fictional',
    # language reference artifact (lead, theologian)
    'latin',
    # function words that slipped through
    'along', 'than',
    # abstract magnitude / physics leaks
    'dimension', 'quantity', 'velocity', 'produce',
    # generic verb bridging prove–refuge
    'provide',
    # simplemma maps 'fixed' → 'fixe'
    'fixe',
    # generic verbs that bridge unrelated lemmas
    'turn',
    # abstract capability words (force/wind MW definitions)
    'ability', 'influence',
    # generic verbs/adjectives that bridge unrelated definitions
    'appear', 'distant', 'display',
    # taxonomy/social terms leaking from species/gaze MW definitions
    'group', 'individual', 'rank',
    # cognitive generics bridging force/think/sound
    'mind', 'judge',
    # WN story/tale TV-program sense
    'program',
    # function words / meta-words that slipped through tokenization
    'like', 'new', 'etc', 'about', 'movement',
    # general preposition artifact
    'via',
    # epistemic hedges appearing in definitions (not semes)
    'perhaps', 'possibly', 'sometimes', 'generally', 'usually', 'typically',
    'often', 'mainly', 'especially', 'particularly', 'especially', 'largely',
    # simplemma over-stemming artifacts
    'thinke', 'regarde', 'determin', 'unknow', 'comparativ', 'comparative',
    'fixe', 'swinge',
    # WordNet synset-label leakage (appear in gloss preambles)
    'proposition', 'computer', 'institution', 'performer',
    # definition meta-words
    'whose', 'whereby', 'wherein', 'thereof', 'hereby',
    # generic intensifiers / degree words
    'considerably', 'extremely', 'shockingly', 'conspicuous', 'abruptly',
    # generic body/entity words that over-bridge definitions
    'corporeal', 'fleshly', 'entity',
    # definition filler verbs
    'personify', 'constitute', 'represent', 'designate',
}

# =============================================================================
# SECTION 4 — FILTER HELPERS
# =============================================================================

REDIRECT: set[str] = {
    'spelling of', 'plural of', 'past tense', 'third-person',
    'simple past', 'present participle', 'alternative form', 'iso 639',
}

# Lesk stop set: function words only, deliberately narrower than FRAME
# to preserve discriminating power during sense ranking.
LESK_STOP: set[str] = {
    'the', 'and', 'for', 'not', 'but', 'with', 'from', 'into', 'onto', 'upon',
    'that', 'this', 'which', 'who', 'what', 'how', 'when', 'where', 'why',
    'also', 'such', 'other', 'any', 'all', 'more', 'most', 'much', 'many',
    'very', 'well', 'even', 'just', 'one', 'two', 'its', 'his', 'her', 'our',
    'nor', 'yet', 'both', 'each', 'few', 'own', 'off', 'out', 'over', 'can',
    'may', 'will', 'shall', 'must', 'would', 'could', 'should', 'per', 'via',
    'those', 'some', 'through', 'within', 'another', 'especially',
}


def _lesk_toks(text: str) -> list[str]:
    """Tokenize and lemmatize text for Lesk scoring, using LESK_STOP only."""
    return [t for w in re.findall(r'[a-z]+', text.lower())
            for t in [lemmatize(w)] if t not in LESK_STOP and len(t) > 2]


def is_tautological(definition: str, lemma: str) -> bool:
    """
    True if the definition is circular — any token shares the first 5
    characters of the lemma (stem[:5] match).

    Catches: gyration / "an act of gyrating"
             torment  / "to torment emotionally"
             living   / "condition of living"
    """
    stem = lemma[:5]
    return any(t[:5] == stem for t in _lesk_toks(definition))


def extract_words(text: str, lemma: str, nuclear: set[str]) -> list[str]:
    """
    Tokenize, lemmatize, and filter definition text to seme candidates.
    Removes: words in ``nuclear``, tokens ≤ 2 chars, the lemma itself.
    """
    return [lw for w in re.findall(r'[a-z]+', text.lower())
            for lw in [lemmatize(w)]
            if lw not in nuclear and len(lw) > 2 and lw != lemma]


def clean_wk(raws: list[str]) -> str:
    """Filter Wiktionary redirect/meta entries; join up to 3 real definitions."""
    return ' ; '.join(
        r for r in raws[:3]
        if not any(m in r.lower() for m in REDIRECT) and len(r.split()) > 4
    )


# =============================================================================
# SECTION 5 — RESOURCE FETCHERS
# =============================================================================

# ── 5a. Wiktionary ────────────────────────────────────────────────────────────

_WK_BASE    = "https://en.wiktionary.org/api/rest_v1/page/definition/{}"
_WK_HEADERS = {"User-Agent": "isotopy-research/1.0 (academic)"}

# Wiktionary-specific stop set (includes grammatical meta-words in definitions)
_WK_STOPS: set[str] = {
    'a','an','the','of','to','in','or','and','is','are','be','been','was',
    'were','that','which','by','from','for','as','its','it','with','on',
    'at','into','also','not','no','any','one','two','used','especially',
    'often','usually','when','where','while','their','they','them','this',
    'those','these','have','has','had','do','does','did','will','would',
    'can','could','may','might','shall','should','about','such','more',
    'most','very','so','than','but','if','up','out','over','under','being',
    'make','made','take','taken','give','given','come','goes',
    'another','other','each','some','all','both','either','after','before',
    'now','then','here','there','how','what','when','where','who',
    'simple','plural','singular','present','past','third','tense',
    'indicative','participle','person','verb','noun','adjective','adverb',
    'defdate','font','parser','output','smaller','mwparser',
}


def _wk_clean_html(text: str) -> str:
    text = re.sub(r'\.mw-parser-output[^}]*}', '', text)
    text = re.sub(r'\{[^}]*\}', '', text)
    return re.sub(r'<[^>]+>', '', text)


def _wk_fetch_single(lemma: str) -> dict:
    """Fetch one lemma from the Wiktionary REST API."""
    try:
        r = requests.get(_WK_BASE.format(lemma), headers=_WK_HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  WK error [{lemma}]: {e}")
        return {"definition_words": [], "raw_definitions": []}

    words: set[str] = set()
    raws: list[str] = []
    for lang, entries in data.items():
        if lang != 'en':
            continue
        for entry in entries:
            for defn in entry.get('definitions', []):
                text = _wk_clean_html(defn.get('definition', ''))
                if not text.strip():
                    continue
                raws.append(text.strip())
                words.update(
                    t for t in re.findall(r'[a-z]+', text.lower())
                    if t not in _WK_STOPS and len(t) > 3 and t != lemma
                )
    return {"definition_words": sorted(words), "raw_definitions": raws[:6]}


def fetch_wiktionary(
    lemma_map: dict[str, list[str]] = LEMMA_MAP,
    out: str = 'potocki_definitions.json',
    delay: float = 0.5,
) -> dict:
    """
    Fetch Wiktionary definitions for all lemmas and write to JSON.

    JSON format::

        {"lemma_map": {...},
         "definitions": {lemma: {"raw_definitions": [...], "definition_words": [...]}}}
    """
    output: dict = {"lemma_map": lemma_map, "definitions": {}}
    for i, lemma in enumerate(sorted(lemma_map)):
        print(f"[{i+1}/{len(lemma_map)}] {lemma}...", end=' ', flush=True)
        result = _wk_fetch_single(lemma)
        output["definitions"][lemma] = result
        n = len(result['definition_words'])
        print(f"{n} words" + (" ← empty!" if n == 0 else ""))
        time.sleep(delay)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    empty = [l for l, v in output['definitions'].items() if not v['definition_words']]
    print(f"\nSaved {out}  ({len(output['definitions'])} lemmas, empty: {empty or 'none'})")
    return output


# ── 5b. WordNet 3.1 (offline, from local wn3.1.dict/dict folder) ─────────────

# WordNet uses American spelling throughout
_WN_SPELLING: dict[str, str] = {
    'rumour': 'rumor', 'sceptical': 'skeptical', 'traveller': 'traveler',
}

# POS priority per lemma  (n, v, s=satellite adj, a=adj, r=adv)
_WN_POS: dict[str, str] = {
    'body':'n', 'corpse':'n', 'flesh':'n', 'ghost':'n', 'demon':'n',
    'gallows':'n', 'vampire':'n', 'torment':'n', 'rumour':'n',
    'story':'n', 'tale':'n', 'argument':'n', 'thesis':'n',
    'supposition':'n', 'fact':'n', 'species':'n', 'entrance':'n',
    'valley':'n', 'mountain':'n', 'night':'n', 'heaven':'n',
    'prison':'n', 'refuge':'n', 'vengeance':'n', 'consent':'n',
    'eye':'n', 'gaze':'n', 'spectacle':'n', 'gyration':'n',
    'track':'n', 'wind':'n', 'brother':'n', 'theologian':'n',
    'traveller':'n', 'wayfarer':'n', 'curiosity':'n', 'living':'n',
    'hang':'v', 'escape':'v', 'possess':'v', 'execute':'v',
    'claim':'v', 'hear':'v', 'see':'v', 'say':'v', 'tell':'v',
    'think':'v', 'agree':'v', 'approach':'v', 'break':'v',
    'catch':'v', 'force':'v', 'free':'v', 'lead':'v', 'make':'v',
    'meet':'v', 'prove':'v', 'set':'v', 'swing':'v', 'take':'v',
    'tear':'v', 'write':'v', 'hurry':'v', 'prompt':'v',
    'avert':'v', 'attest':'v', 'torment':'v',
    'ghastly':'s', 'eerie':'s', 'hideous':'s', 'strange':'s',
    'innocent':'s', 'nameless':'s', 'horrified':'s', 'implausible':'s',
    'revolting':'s', 'widespread':'s', 'sceptical':'s', 'unjust':'s',
    'old':'s', 'sound':'s',
}
_WN_POS_FILE: dict[str, str] = {'n':'noun', 'v':'verb', 'a':'adj', 's':'adj', 'r':'adv'}


def _wn_load_index(dict_dir: str, pos_file: str) -> dict[str, list[str]]:
    """
    Parse a WordNet index.{pos} file.

    Index line format:
        lemma  pos  synset_cnt  p_cnt  [ptr_symbol × p_cnt]  sense_cnt  tagsense_cnt  [offset × synset_cnt]

    offset_start = 4 + p_cnt + 2  (skip synset_cnt column, p_cnt pointers,
                                    then sense_cnt and tagsense_cnt)
    """
    index: dict[str, list[str]] = {}
    with open(os.path.join(dict_dir, f'index.{pos_file}'), encoding='utf-8') as f:
        for line in f:
            if line.startswith('  '):
                continue
            parts = line.split()
            if len(parts) < 7:
                continue
            lemma        = parts[0]
            synset_cnt   = int(parts[2])
            p_cnt        = int(parts[3])
            offset_start = 4 + p_cnt + 2
            offsets      = parts[offset_start: offset_start + synset_cnt]
            if offsets:
                index[lemma] = offsets
    return index


def _wn_load_glosses(dict_dir: str, pos_file: str) -> dict[str, str]:
    """Parse a WordNet data.{pos} file, returning {offset: gloss}."""
    glosses: dict[str, str] = {}
    with open(os.path.join(dict_dir, f'data.{pos_file}'), encoding='utf-8') as f:
        for line in f:
            if line.startswith('  ') or '|' not in line:
                continue
            offset = line.split()[0]
            gloss  = line.split('|', 1)[1].strip()
            gloss  = re.sub(r'"[^"]*"', '', gloss).strip().rstrip(';').strip()
            glosses[offset] = gloss
    return glosses


def fetch_wordnet(
    lemma_map: dict[str, list[str]] = LEMMA_MAP,
    dict_dir: str = 'wn3.1.dict/dict',
    out: str = 'potocki_definitions_wn.json',
) -> dict:
    """
    Build WordNet 3.1 definitions from a local dict folder.

    Download WordNet 3.1 dict files from https://wordnet.princeton.edu/
    and point ``dict_dir`` at the extracted dict/ subfolder.
    """
    indexes: dict[str, dict] = {}
    glosses_map: dict[str, dict] = {}
    for pf in ['noun', 'verb', 'adj', 'adv']:
        indexes[pf]     = _wn_load_index(dict_dir, pf)
        glosses_map[pf] = _wn_load_glosses(dict_dir, pf)

    def lookup(lemma: str) -> list[str]:
        wn_lemma  = _WN_SPELLING.get(lemma, lemma).replace(' ', '_')
        priority  = _WN_POS.get(lemma, 'n')
        pos_order = [priority] + [p for p in ['n', 'v', 's', 'a', 'r'] if p != priority]
        seen: set[str] = set()
        for pos in pos_order:
            pf = _WN_POS_FILE[pos]
            if pf in seen:
                continue
            seen.add(pf)
            offsets = indexes[pf].get(wn_lemma, [])
            glosses = [glosses_map[pf][o] for o in offsets[:3] if o in glosses_map[pf]]
            if glosses:
                return glosses
        return []

    definitions: dict = {}
    missing: list[str] = []
    for lemma in sorted(lemma_map):
        glosses = lookup(lemma)
        if not glosses:
            missing.append(lemma)
        else:
            definitions[lemma] = {
                'raw_definitions':  glosses,
                'definition_words': [w for w in re.findall(r'[a-z]+', ' '.join(glosses).lower())
                                     if len(w) > 2],
            }
    if missing:
        print(f"WN missing: {missing}")
    output = {'lemma_map': lemma_map, 'definitions': definitions}
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Saved {out}  ({len(definitions)} lemmas)")
    return output


# ── 5c. Merriam-Webster Collegiate API ───────────────────────────────────────

_MW_BASE     = 'https://www.dictionaryapi.com/api/v3/references/collegiate/json/'
_MW_SPELLING: dict[str, str] = {
    'rumour': 'rumor', 'sceptical': 'skeptical', 'traveller': 'traveler',
}

_MW_NOUN_LEMMAS: set[str] = {
    'body','corpse','flesh','ghost','demon','gallows','vampire','torment',
    'rumour','story','tale','argument','thesis','supposition','fact',
    'species','entrance','valley','mountain','night','heaven','prison',
    'refuge','vengeance','consent','eye','gaze','spectacle','gyration',
    'track','wind','brother','theologian','traveller','wayfarer','curiosity','living',
}
_MW_VERB_LEMMAS: set[str] = {
    'hang','escape','possess','execute','claim','hear','see','say','tell',
    'think','agree','approach','break','catch','force','free','lead','make',
    'meet','prove','set','swing','take','tear','write','hurry','prompt',
    'avert','attest','torment',
}
_MW_ADJ_LEMMAS: set[str] = {
    'ghastly','eerie','hideous','strange','innocent','nameless','horrified',
    'implausible','revolting','widespread','sceptical','unjust','old','sound',
}


def _mw_strip_markup(text: str) -> str:
    """
    Remove all MW inline tokens ({bc}, {it}, {sx|word||}, etc.),
    leaving plain prose.
    """
    # cross-reference tokens: keep display text
    text = re.sub(r'\{[a-z_]+\|([^|}]+)\|?[^}]*\}', r'\1', text)
    # remaining tokens: {bc}, {it}, {b}, {ldquo}, {rdquo}, {dx_def}…
    text = re.sub(r'\{[^}]+\}', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _mw_extract_senses(response: list, lemma: str, preferred_pos: str | None = None) -> list[str]:
    """
    Extract up to 3 clean definition strings from a MW API response.
    Applies POS preference to select the grammatically appropriate entry.
    Returns [] if the response contains only spelling suggestions.

    preferred_pos : 'noun' | 'verb' | 'adjective' | None
        If supplied, overrides the hardcoded Potocki lemma sets.
        Pass the Penn Treebank POS tag mapped to MW POS for general text use.
    """
    if not response or isinstance(response[0], str):
        return []

    if preferred_pos is not None:
        preferred = preferred_pos
    else:
        preferred = (
            'noun'      if lemma in _MW_NOUN_LEMMAS else
            'verb'      if lemma in _MW_VERB_LEMMAS else
            'adjective' if lemma in _MW_ADJ_LEMMAS else None
        )

    def get_senses(entry: dict) -> list[str]:
        senses: list[str] = []
        for defblock in entry.get('def', []):
            for sseq in defblock.get('sseq', []):
                for sense in sseq:
                    if isinstance(sense, list) and len(sense) == 2:
                        sd = sense[1]
                        if isinstance(sd, dict):
                            for token in sd.get('dt', []):
                                if isinstance(token, list) and token[0] == 'text':
                                    clean = _mw_strip_markup(token[1])
                                    if clean and len(clean) > 10:
                                        senses.append(clean)
                                    break
        return senses

    all_entries = [e for e in response if isinstance(e, dict)]
    if preferred:
        pref = [e for e in all_entries if preferred in e.get('fl', '').lower()]
        if pref:
            all_entries = pref

    senses: list[str] = []
    for entry in all_entries[:2]:
        senses.extend(get_senses(entry))
        if len(senses) >= 3:
            break
    return senses[:3]


def fetch_mw(
    lemma_map: dict[str, list[str]] = LEMMA_MAP,
    out: str = 'potocki_definitions_mw.json',
    api_key: str = MW_API_KEY,
    delay: float = 0.3,
) -> dict:
    """
    Fetch Merriam-Webster Collegiate definitions via the official API.

    Requires a free key from https://dictionaryapi.com/
    Set MW_API_KEY at the top of this file, or pass ``api_key`` directly.
    """
    if not api_key:
        raise ValueError("MW_API_KEY is empty — set it at the top of isotopy.py")

    definitions: dict = {}
    missing: list[str] = []
    for lemma in sorted(lemma_map):
        mw_word = _MW_SPELLING.get(lemma, lemma)
        url = _MW_BASE + urllib.parse.quote(mw_word) + '?key=' + api_key
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'IsotopyBot/1.0'})
            with urllib.request.urlopen(req, timeout=10) as r:
                response = json.loads(r.read())
            senses = _mw_extract_senses(response, lemma)
            if senses:
                definitions[lemma] = {
                    'raw_definitions':  senses,
                    'definition_words': [w for w in re.findall(r'[a-z]+', ' '.join(senses).lower())
                                         if len(w) > 2],
                }
            else:
                missing.append(lemma)
        except Exception as e:
            missing.append(lemma)
            print(f"  MW error [{lemma}]: {e}")
        time.sleep(delay)

    if missing:
        print(f"MW missing/error: {missing}")
    output = {'lemma_map': lemma_map, 'definitions': definitions}
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Saved {out}  ({len(definitions)} lemmas)")
    return output


# ── 5d. Webster 1828 ─────────────────────────────────────────────────────────
# Source: Project Gutenberg #673, American Dictionary of the English Language,
# Noah Webster, 1828.  Loaded at runtime from data/lexical/potocki_definitions_w1828.json
# via the path_w1828 parameter of build_rings().
#
# Why this resource: theological and Gothic senses are PRIMARY in 1828,
# contemporaneous with Potocki (first pub. 1804).  Modern resources rank
# these senses lower in frequency-ordered entry lists.


# =============================================================================
# SECTION 6 — CORE PIPELINE:  build_rings()
# =============================================================================
# "Rings" = the concentric IDF-weighted seme profiles around each lemma.
#
# Two-pass architecture
# ---------------------
# Pass 1  (Lesk-context construction)
#   Load all four JSON resources (WK, WN, MW, W1828).  Build a first-pass
#   definition for every lemma using raw un-filtered senses across all four.
#   Compute word-frequency across all definitions.  The Lesk context is:
#       C_lesk = corpus_lemmas  ∪  {w : df(w) ≤ LESK_DF_MAX}
#   This gives passage-specific vocabulary for ranking senses.
#
# Pass 2  (full sense selection + IDF + graph)
#   For each lemma, auto_select_def() picks the top-N Lesk-ranked senses
#   per resource across all four resources, rejecting redirects and
#   tautological definitions.  W1828 is treated as a primary resource
#   alongside WN and MW; its vocabulary therefore contributes to the
#   cross-resource consistency gate for Wiktionary semes.
#   The merged text is tokenized → lemma_words.
#   IDF weights are computed (semes in >IDF_CUTOFF fraction discarded).
#   expand() builds L1+L2 IDF-weighted profiles.
#   Pairwise min-IDF overlap scores populate raw_edges.


@dataclass
class RingResult:
    """All intermediate products of build_rings(), available for inspection."""
    lemmas:      list[str]
    lemma_set:   set[str]
    nuclear:     set[str]
    lesk_context: set[str]
    merged_text: dict[str, str]
    lemma_words: dict[str, list[str]]
    idf:         dict[str, float]
    expanded:    dict[str, dict[str, float]]
    raw_edges:   dict[tuple[str, str], float]


def build_rings(
    path_wk: str,
    path_wn: str,
    path_mw: str,
    path_w1828: str,
    idf_cutoff: float = IDF_CUTOFF,
    lesk_df_max: int  = LESK_DF_MAX,
    lesk_top_n: int   = LESK_TOP_N,
    verbose: bool     = True,
) -> RingResult:
    """
    Full two-pass pipeline from JSON definition files to weighted similarity graph.

    Parameters
    ----------
    path_wk    : path to pre-fetched Wiktionary definition JSON
    path_wn    : path to pre-fetched WordNet definition JSON
    path_mw    : path to pre-fetched Merriam-Webster definition JSON
    path_w1828 : path to pre-fetched Webster 1828 definition JSON; treated as a
                 primary resource alongside WN and MW — its vocabulary contributes
                 to the cross-resource consistency gate for Wiktionary semes
    idf_cutoff    : fraction threshold; semes in > idf_cutoff*N definitions discarded
    lesk_df_max   : Lesk context includes only semes with df ≤ this value
    lesk_top_n    : number of top-Lesk senses per resource kept per lemma
    verbose       : print coverage/edge statistics

    Returns
    -------
    RingResult dataclass with .lemmas, .idf, .expanded, .raw_edges, etc.
    """
    # ── load resources ────────────────────────────────────────────────────────
    with open(path_wk)    as f: wk    = json.load(f)
    with open(path_wn)    as f: wn    = json.load(f)
    with open(path_mw)    as f: mw    = json.load(f)
    with open(path_w1828) as f: w1828 = json.load(f)

    lemmas:    list[str] = sorted(wk['definitions'].keys())
    lemma_set: set[str]  = set(lemmas)
    N:         int       = len(lemmas)

    # corpus lemmas are automatically nuclear (circularity argument)
    nuclear: set[str] = FRAME | lemma_set

    # ── PASS 1: build Lesk context ────────────────────────────────────────────
    def _first_pass_def(lemma: str) -> str:
        """Merge first 3 senses per resource without tautology/Lesk filtering."""
        parts: list[str] = []
        for data in [wk, wn, mw, w1828]:
            for d in data['definitions'][lemma].get('raw_definitions', [])[:3]:
                if not (any(m in d.lower() for m in REDIRECT) or len(d.split()) <= 2):
                    parts.append(d)
        return ' | '.join(parts)

    lw0 = {l: extract_words(_first_pass_def(l), l, nuclear) for l in lemmas}
    wc0 = Counter(w for ws in lw0.values() for w in set(ws))

    # Lesk context: passage lemmas + low-df semes (passage-specific terms)
    lesk_context: set[str] = lemma_set | {w for w, c in wc0.items() if c <= lesk_df_max}

    # ── Lesk helpers (closures over lesk_context) ─────────────────────────────
    def lesk_score(definition: str, lemma: str) -> int:
        """Overlap between definition tokens and the passage-derived Lesk context."""
        return len(set(t for t in _lesk_toks(definition) if t != lemma) & lesk_context)

    def auto_select_def(lemma: str) -> str:
        """
        For each of WK, WN, MW, W1828: rank all non-redirect, non-tautological
        senses by Lesk score and keep the top ``lesk_top_n``.  Concatenate across
        resources.

        Cross-resource consistency gate for Wiktionary:
        Wiktionary senses with zero passage relevance (Lesk score 0) are ranked
        last and fall outside the top_n cut, preventing noise from irrelevant
        senses.  W1828 is treated as a primary resource; its vocabulary is part
        of the Lesk context, so WK semes not echoed by WN, MW, or W1828 are
        naturally suppressed.
        """
        parts: list[str] = []
        for data in [wk, wn, mw, w1828]:
            defs = data['definitions'][lemma].get('raw_definitions', [])
            candidates = [
                (d, lesk_score(d, lemma)) for d in defs
                if not (any(m in d.lower() for m in REDIRECT) or len(d.split()) <= 2)
                and not is_tautological(d, lemma)
            ]
            if not candidates:
                continue
            candidates.sort(key=lambda x: x[1], reverse=True)
            parts.extend(d for d, _ in candidates[:lesk_top_n])
        return ' | '.join(parts)

    def get_definition(lemma: str) -> str:
        """
        Final definition: Lesk-ranked senses from all four resources (WK, WN,
        MW, W1828) via auto_select_def.
        """
        return auto_select_def(lemma)

    # ── PASS 2: merged definitions → semes → IDF → profiles → edges ───────
    merged_text: dict[str, str]        = {l: get_definition(l) for l in lemmas}
    lemma_words: dict[str, list[str]]  = {l: extract_words(merged_text[l], l, nuclear)
                                           for l in lemmas}

    word_count = Counter(w for ws in lemma_words.values() for w in set(ws))
    idf: dict[str, float] = {
        w: math.log(N / c)
        for w, c in word_count.items()
        if c <= N * idf_cutoff
    }

    def expand(lemma: str) -> dict[str, float]:
        """
        IDF-weighted seme profile: L1 (direct) + L2 (one step further, ×0.5).

        L2 skips any intermediate that is a corpus lemma — the circularity fix:
        if tear's definition mentions force, we must not import force's semes
        into tear's profile just because tear uses force as a means of action.
        """
        profile: dict[str, float] = defaultdict(float)
        # L1
        for w in lemma_words.get(lemma, []):
            if w in idf:
                profile[w] += idf[w]
        # L2 — skip corpus-lemma intermediates
        for w in lemma_words.get(lemma, []):
            if w in lemma_words and w not in lemma_set:
                for w2 in lemma_words[w]:
                    if w2 in idf and w2 != lemma:
                        profile[w2] += 0.5 * idf[w2]
        return dict(profile)

    expanded: dict[str, dict[str, float]] = {l: expand(l) for l in lemmas}

    # pairwise min-IDF overlap score
    raw_edges: dict[tuple[str, str], float] = {}
    for i, l1 in enumerate(lemmas):
        for l2 in lemmas[i + 1:]:
            shared = set(expanded[l1]) & set(expanded[l2])
            if shared:
                score = sum(min(expanded[l1][w], expanded[l2][w]) for w in shared)
                raw_edges[(l1, l2)] = score

    if verbose:
        print(f"N={N} lemmas  |  IDF vocabulary: {len(idf)} seme types  "
              f"|  {len(raw_edges)} edges computed")
        print("Top 10 edges:")
        for (l1, l2), s in sorted(raw_edges.items(), key=lambda x: x[1], reverse=True)[:10]:
            shared = set(expanded[l1]) & set(expanded[l2])
            top3 = sorted(shared,
                          key=lambda w: min(expanded[l1][w], expanded[l2][w]),
                          reverse=True)[:3]
            print(f"  {s:6.2f}  {l1} — {l2}  via {top3}")

    return RingResult(
        lemmas=lemmas, lemma_set=lemma_set, nuclear=nuclear,
        lesk_context=lesk_context, merged_text=merged_text,
        lemma_words=lemma_words, idf=idf, expanded=expanded,
        raw_edges=raw_edges,
    )



def build_rings_from_dicts(
    wk:    dict,
    wn:    dict,
    mw:    dict,
    w1828: dict | None = None,
    idf_cutoff: float = IDF_CUTOFF,
    lesk_df_max: int  = LESK_DF_MAX,
    lesk_top_n: int   = LESK_TOP_N,
    verbose: bool     = False,
) -> RingResult:
    """
    Identical to build_rings() but accepts pre-loaded dicts instead of file paths.
    W1828 defaults to an empty resource when not supplied (general-text use case).

    Parameters
    ----------
    wk, wn, mw : dicts in the format produced by fetch_wiktionary / fetch_wordnet / fetch_mw
                 i.e. {'definitions': {lemma: {'raw_definitions': [...], ...}}}
    w1828      : same format; pass None to skip (no period-specific lexicon)
    """
    if w1828 is None:
        # Build an empty W1828 envelope covering all lemmas
        all_lemmas = set(wk.get('definitions', {})) | set(wn.get('definitions', {})) | set(mw.get('definitions', {}))
        w1828 = {'definitions': {l: {'raw_definitions': [], 'definition_words': []} for l in all_lemmas}}
    # Ensure all resources cover the same lemma set (fill missing with empty)
    all_lemmas = set(wk.get('definitions', {})) | set(wn.get('definitions', {})) | set(mw.get('definitions', {}))
    empty = {'raw_definitions': [], 'definition_words': []}
    for data in [wk, wn, mw, w1828]:
        for l in all_lemmas:
            data['definitions'].setdefault(l, empty)

    lemmas:    list[str] = sorted(wk['definitions'].keys())
    lemma_set: set[str]  = set(lemmas)
    N:         int       = len(lemmas)

    # corpus lemmas are automatically nuclear (circularity argument)
    nuclear: set[str] = FRAME | lemma_set

    # ── PASS 1: build Lesk context ────────────────────────────────────────────
    def _first_pass_def(lemma: str) -> str:
        """Merge first 3 senses per resource without tautology/Lesk filtering."""
        parts: list[str] = []
        for data in [wk, wn, mw, w1828]:
            for d in data['definitions'][lemma].get('raw_definitions', [])[:3]:
                if not (any(m in d.lower() for m in REDIRECT) or len(d.split()) <= 2):
                    parts.append(d)
        return ' | '.join(parts)

    lw0 = {l: extract_words(_first_pass_def(l), l, nuclear) for l in lemmas}
    wc0 = Counter(w for ws in lw0.values() for w in set(ws))

    # Lesk context: passage lemmas + low-df semes (passage-specific terms)
    lesk_context: set[str] = lemma_set | {w for w, c in wc0.items() if c <= lesk_df_max}

    # ── Lesk helpers (closures over lesk_context) ─────────────────────────────
    def lesk_score(definition: str, lemma: str) -> int:
        """Overlap between definition tokens and the passage-derived Lesk context."""
        return len(set(t for t in _lesk_toks(definition) if t != lemma) & lesk_context)

    def auto_select_def(lemma: str) -> str:
        """
        For each of WK, WN, MW, W1828: rank all non-redirect, non-tautological
        senses by Lesk score and keep the top ``lesk_top_n``.  Concatenate across
        resources.

        Cross-resource consistency gate for Wiktionary:
        Wiktionary senses with zero passage relevance (Lesk score 0) are ranked
        last and fall outside the top_n cut, preventing noise from irrelevant
        senses.  W1828 is treated as a primary resource; its vocabulary is part
        of the Lesk context, so WK semes not echoed by WN, MW, or W1828 are
        naturally suppressed.
        """
        parts: list[str] = []
        for data in [wk, wn, mw, w1828]:
            defs = data['definitions'][lemma].get('raw_definitions', [])
            candidates = [
                (d, lesk_score(d, lemma)) for d in defs
                if not (any(m in d.lower() for m in REDIRECT) or len(d.split()) <= 2)
                and not is_tautological(d, lemma)
            ]
            if not candidates:
                continue
            candidates.sort(key=lambda x: x[1], reverse=True)
            parts.extend(d for d, _ in candidates[:lesk_top_n])
        return ' | '.join(parts)

    def get_definition(lemma: str) -> str:
        """
        Final definition: Lesk-ranked senses from all four resources (WK, WN,
        MW, W1828) via auto_select_def.
        """
        return auto_select_def(lemma)

    # ── PASS 2: merged definitions → semes → IDF → profiles → edges ───────
    merged_text: dict[str, str]        = {l: get_definition(l) for l in lemmas}
    lemma_words: dict[str, list[str]]  = {l: extract_words(merged_text[l], l, nuclear)
                                           for l in lemmas}

    word_count = Counter(w for ws in lemma_words.values() for w in set(ws))
    idf: dict[str, float] = {
        w: math.log(N / c)
        for w, c in word_count.items()
        if c <= N * idf_cutoff
    }

    def expand(lemma: str) -> dict[str, float]:
        """
        IDF-weighted seme profile: L1 (direct) + L2 (one step further, ×0.5).

        L2 skips any intermediate that is a corpus lemma — the circularity fix:
        if tear's definition mentions force, we must not import force's semes
        into tear's profile just because tear uses force as a means of action.
        """
        profile: dict[str, float] = defaultdict(float)
        # L1
        for w in lemma_words.get(lemma, []):
            if w in idf:
                profile[w] += idf[w]
        # L2 — skip corpus-lemma intermediates
        for w in lemma_words.get(lemma, []):
            if w in lemma_words and w not in lemma_set:
                for w2 in lemma_words[w]:
                    if w2 in idf and w2 != lemma:
                        profile[w2] += 0.5 * idf[w2]
        return dict(profile)

    expanded: dict[str, dict[str, float]] = {l: expand(l) for l in lemmas}

    # pairwise min-IDF overlap score
    raw_edges: dict[tuple[str, str], float] = {}
    for i, l1 in enumerate(lemmas):
        for l2 in lemmas[i + 1:]:
            shared = set(expanded[l1]) & set(expanded[l2])
            if shared:
                score = sum(min(expanded[l1][w], expanded[l2][w]) for w in shared)
                raw_edges[(l1, l2)] = score

    if verbose:
        print(f"N={N} lemmas  |  IDF vocabulary: {len(idf)} seme types  "
              f"|  {len(raw_edges)} edges computed")
        print("Top 10 edges:")
        for (l1, l2), s in sorted(raw_edges.items(), key=lambda x: x[1], reverse=True)[:10]:
            shared = set(expanded[l1]) & set(expanded[l2])
            top3 = sorted(shared,
                          key=lambda w: min(expanded[l1][w], expanded[l2][w]),
                          reverse=True)[:3]
            print(f"  {s:6.2f}  {l1} — {l2}  via {top3}")

    return RingResult(
        lemmas=lemmas, lemma_set=lemma_set, nuclear=nuclear,
        lesk_context=lesk_context, merged_text=merged_text,
        lemma_words=lemma_words, idf=idf, expanded=expanded,
        raw_edges=raw_edges,
    )

# =============================================================================
# SECTION 7 — CLUSTERING:  cluster_isotopies()
# =============================================================================

@dataclass
class ClusterResult:
    threshold: float
    label:     str
    clusters:  list[list[str]]   # multi-member only, sorted by size desc
    isolates:  list[str]


def _complete_linkage(
    edges: dict[tuple[str, str], float],
    all_lemmas: list[str],
    threshold: float,
) -> tuple[list[list[str]], list[str]]:
    """
    Complete-linkage clustering: a node joins a cluster only when it exceeds
    ``threshold`` against *every* existing member.

    Motivation: Greimas's isotopy requires redundancy of semes — direct
    co-occurrence, not transitive chains.  Single-linkage would allow A–B–C
    clusters where A and C share no evidence; complete-linkage prevents this.
    """
    adj: dict[str, set[str]] = defaultdict(set)
    for (l1, l2), s in edges.items():
        if s >= threshold:
            adj[l1].add(l2)
            adj[l2].add(l1)

    visited: set[str] = set()
    clusters: list[list[str]] = []

    for seed in sorted(all_lemmas):
        if seed in visited or not adj[seed]:
            continue
        cluster: set[str] = {seed}
        candidates: set[str] = set(adj[seed])
        changed = True
        while changed:
            changed = False
            for c in list(candidates):
                if all(c in adj[m] for m in cluster):
                    cluster.add(c)
                    candidates = candidates & adj[c]
                    changed = True
                    break
        if len(cluster) > 1:
            clusters.append(sorted(cluster))
            visited.update(cluster)

    # collect direct pairs not yet absorbed into a larger cluster
    for l in [l for l in all_lemmas if l not in visited]:
        for n in adj[l]:
            if n not in visited:
                clusters.append(sorted([l, n]))
                visited.update([l, n])
                break

    isolates = sorted(l for l in all_lemmas if not adj[l])
    return clusters, isolates


def cluster_isotopies(
    result: RingResult,
    t_strong: float = T_STRONG,
    t_medium: float = T_MEDIUM,
    t_weak:   float = T_WEAK,
    verbose:  bool  = True,
) -> list[ClusterResult]:
    """
    Run complete-linkage clustering at three absolute IDF-unit thresholds.

    Thresholds are absolute (raw IDF-unit scores), not normalised, in order to
    preserve the multi-scale structure of isotopic evidence:
      STRONG (t ≥ 10) — lexically overdetermined isotopies (narrative, argumentation)
      MEDIUM (t ≥  8) — motion and institutional violence (swing, execution)
      WEAK   (t ≥  5) — obliquely evoked isotopies (supernatural, horror)

    Parameters
    ----------
    result   : RingResult from build_rings()
    t_strong, t_medium, t_weak : tier thresholds
    verbose  : print formatted cluster tables

    Returns
    -------
    List of three ClusterResult objects [strong, medium, weak].
    """
    tier_results: list[ClusterResult] = []

    for threshold, label in [
        (t_strong, 'STRONG'),
        (t_medium, 'MEDIUM'),
        (t_weak,   'WEAK'),
    ]:
        clusters, isolates = _complete_linkage(result.raw_edges, result.lemmas, threshold)
        multi = sorted([c for c in clusters if len(c) > 1], key=len, reverse=True)
        tier_results.append(ClusterResult(threshold, label, multi, isolates))

        if verbose:
            sep = '━' * 62
            print(f'\n{sep}')
            print(f'  {label} (t ≥ {threshold})  —  {len(multi)} clusters,  {len(isolates)} isolates')
            print(sep)
            for i, cl in enumerate(multi):
                # aggregate seme weights across all cluster members
                agg: dict[str, float] = defaultdict(float)
                for l in cl:
                    for w, s in result.expanded[l].items():
                        agg[w] += s
                top4 = sorted(agg, key=agg.__getitem__, reverse=True)[:4]
                print(f'  C{i+1:02d} ({len(cl)}): {", ".join(cl)}')
                print(f'        semes: {top4}')
            if isolates:
                print(f'  isolates: {isolates}')

    return tier_results


# =============================================================================
# SECTION 8 — CONVENIENCE ENTRY POINT:  run_pipeline()
# =============================================================================

def run_pipeline(
    path_wk:    str = 'potocki_definitions.json',
    path_wn:    str = 'potocki_definitions_wn.json',
    path_mw:    str = 'potocki_definitions_mw.json',
    path_w1828: str = 'potocki_definitions_w1828.json',
    t_strong: float = T_STRONG,
    t_medium: float = T_MEDIUM,
    t_weak:   float = T_WEAK,
    verbose:  bool  = True,
) -> tuple[RingResult, list[ClusterResult]]:
    """
    Run the complete isotopy detection pipeline end-to-end.

    Stages:
      1. build_rings()        — load JSON, two-pass Lesk (WK+WN+MW+W1828), IDF, L1+L2 expansion
      2. cluster_isotopies()  — complete-linkage at three tiers

    Parameters
    ----------
    path_wk, path_wn, path_mw, path_w1828 : paths to pre-fetched definition JSON files
    t_strong, t_medium, t_weak : clustering tier thresholds (absolute IDF units)
    verbose  : print progress and results to stdout

    Returns
    -------
    (RingResult, list[ClusterResult])  — all intermediate data available for inspection

    Example::

        from modules.isotopy import run_pipeline
        rings, tiers = run_pipeline()
        # inspect top edges:
        for (l1, l2), s in sorted(rings.raw_edges.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f'{s:.2f}  {l1}–{l2}')
    """
    rings  = build_rings(path_wk, path_wn, path_mw, path_w1828, verbose=verbose)
    tiers  = cluster_isotopies(rings, t_strong, t_medium, t_weak, verbose=verbose)
    return rings, tiers


# =============================================================================
# CLI
# =============================================================================

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Lexicon-based isotopy detection — Valle, Basic Semiotic Modelling'
    )
    parser.add_argument('path_wk',    nargs='?', default='potocki_definitions.json')
    parser.add_argument('path_wn',    nargs='?', default='potocki_definitions_wn.json')
    parser.add_argument('path_mw',    nargs='?', default='potocki_definitions_mw.json')
    parser.add_argument('path_w1828', nargs='?', default='potocki_definitions_w1828.json')
    parser.add_argument('--fetch-wk',  action='store_true', help='Fetch Wiktionary definitions')
    parser.add_argument('--fetch-wn',  action='store_true', help='Build WordNet definitions (needs --wn-dir)')
    parser.add_argument('--fetch-mw',  action='store_true', help='Fetch MW definitions (needs MW_API_KEY)')
    parser.add_argument('--wn-dir',    default='wn3.1.dict/dict', help='WordNet dict folder')
    args = parser.parse_args()

    if args.fetch_wk:
        fetch_wiktionary()
    if args.fetch_wn:
        fetch_wordnet(dict_dir=args.wn_dir)
    if args.fetch_mw:
        fetch_mw()
    if not (args.fetch_wk or args.fetch_wn or args.fetch_mw):
        run_pipeline(args.path_wk, args.path_wn, args.path_mw, args.path_w1828)
