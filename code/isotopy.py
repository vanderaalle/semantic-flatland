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
#   Stage 1 — Redirect filter + length filter (only hard pre-filters):
#     Tautology gate was tested and removed (77 % false-positive rate).
#     gyration   MW "an act of gyrating" → Lesk score 0, falls outside top-2 cut
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

import copy
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
    # Participial/gerundive adjectives simplemma converts to verb
    'horrified', 'unnerved', 'unredeemed', 'unrelieved',
    'revolting', 'nauseating', 'terrifying', 'disturbing',
}

# Known simplemma failures: wrong stem produced → correct lemma
_LEMMA_CORRECTIONS: dict[str, str] = {
    'claime':   'claim',    # claimed → claime  (should be claim)
    'unjustly': 'unjust',   # adverb stripping not handled by simplemma
    'proving':  'prove',    # proving → proving  (should be prove)
    'thought':  'think',    # irregular past tense
    'hanging':  'hang',     # gerund/participial noun
    'hanged':   'hang',
}


def lemmatize(word: str) -> str:
    """Lemmatize a single word via simplemma, protecting known over-stripped forms."""
    w = word.lower()
    if w in KEEP_AS_IS:
        return w
    stem = simplemma.lemmatize(w, lang='en')
    return _LEMMA_CORRECTIONS.get(stem, stem)


# ── passage function-word filter ──────────────────────────────────────────────
_PASSAGE_STOPS: set[str] = {
    # articles
    'the', 'a', 'an',
    # prepositions
    'of', 'in', 'on', 'at', 'to', 'for', 'by', 'with', 'from', 'into',
    'upon', 'onto', 'over', 'under', 'through', 'along', 'about', 'around',
    'before', 'after', 'since', 'until', 'within', 'without', 'between',
    'among', 'beyond', 'beside', 'against', 'toward', 'towards',
    # conjunctions
    'and', 'but', 'or', 'nor', 'yet', 'so', 'as', 'than', 'if', 'unless',
    'although', 'though', 'while', 'because', 'when', 'where',
    'which', 'who', 'whom', 'whose', 'what', 'that',
    # pronouns
    'i', 'me', 'my', 'he', 'him', 'his', 'she', 'her', 'they', 'them',
    'their', 'we', 'us', 'our', 'you', 'your', 'it', 'its', 'this',
    'these', 'those', 'one',
    # auxiliaries (including inflected forms that lemmatize to auxiliaries)
    'be', 'is', 'are', 'was', 'were', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'having', 'doing',
    'will', 'would', 'shall', 'should', 'can', 'could', 'may', 'might', 'must',
    # high-frequency function adverbs / determiners
    'not', 'no', 'so', 'too', 'very', 'just', 'only', 'even', 'also',
    'still', 'then', 'here', 'there', 'now', 'how', 'why', 'already',
    'never', 'ever', 'more', 'most', 'less', 'least', 'such', 'both',
    'each', 'every', 'all', 'any', 'some', 'few', 'many', 'much', 'other',
    'another', 'own', 'same',
    # numerals and vague quantifiers
    'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
    # common function adverbs that often slip through
    'out', 'off', 'well', 'half', 'during', 'whole', 'usually', 'merely',
    # reflexive pronouns
    'myself', 'himself', 'herself', 'themselves', 'itself', 'yourself',
}


def build_lemma_map(text: str) -> dict[str, list[str]]:
    """
    Extract a lemma → surface-forms map from a passage.

    Tokenizes the text, removes function words and short tokens (< 3 chars),
    lemmatizes each token, and groups all surface forms by lemma.

    Parameters
    ----------
    text : passage text (plain, no metadata)

    Returns
    -------
    dict mapping each lemma to its list of distinct surface forms
    (in order of first occurrence, sorted by lemma key)

    Example::

        from isotopy import build_lemma_map
        lm = build_lemma_map(open('data/corpus/manuscript.txt').read())
    """
    # unique surface tokens in order of first appearance
    seen_order: list[str] = list(dict.fromkeys(
        tok for tok in re.findall(r'[a-z]+', text.lower())
        if len(tok) >= 3 and tok not in _PASSAGE_STOPS
    ))
    result: dict[str, list[str]] = defaultdict(list)
    for tok in seen_order:
        lemma = lemmatize(tok)
        if tok not in result[lemma]:
            result[lemma].append(tok)
    return dict(sorted(result.items()))


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
    # W1828 OCR concatenation artifacts (not caught by '; as,' strip)
    # 'to gaze' run-on in Format C gaze entry
    'togaze',
    # 'racking torture' and 'torture may' run-ons in Format B torture entry
    'rackingtorture', 'torturemay',
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


def tokenize(text: str) -> list[str]:
    """
    Canonical tokenizer: lowercase, [a-z]+ split, lemmatize, discard ≤ 2 chars.

    Returns a raw token list.  Callers apply their own stop filter:
      - is_tautological() uses the full list (stem-prefix test only)
      - lesk_score()      filters LESK_STOP + FRAME cat 1+2 internally
      - extract_semes()   filters nuclear (FRAME + corpus lemmas) internally
    """
    return [t for w in re.findall(r'[a-z]+', text.lower())
            for t in [lemmatize(w)] if len(t) > 2]


def is_tautological(tokens: list[str], lexeme: str) -> bool:
    """
    True if any token shares the first 5 characters of ``lexeme`` (stem-prefix
    match).  Catches circular definitions:

      gyration  / "an act of gyrating"
      torment   / "to torment emotionally"
      living    / "condition of living"

    Takes a pre-tokenized list produced by tokenize().

    NOTE — dead code in the main pipeline path.
    The tautology gate was removed after evaluation: 77 % false-positive rate
    (legitimate senses sharing a stem prefix were being discarded).  ``gyration``
    is now handled correctly without it — the circular MW sense scores 0 under
    Lesk and falls outside the top-2 cut naturally.
    This function survives for reference and is still reachable via the
    ``tautology_in_context=True`` flag in pass 1, but that flag is not set by
    any current caller.
    """
    stem = lexeme[:5]
    return any(t[:5] == stem for t in tokens)


def extract_semes(tokens: list[str], lexeme: str, nuclear: set[str]) -> list[str]:
    """
    Filter a token list to seme candidates.
    Removes tokens in ``nuclear`` (FRAME + corpus lemmas) and the lexeme itself.

    Takes a pre-tokenized list produced by tokenize().
    """
    return [t for t in tokens if t not in nuclear and t != lexeme]


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

    raws: list[str] = []
    for lang, entries in data.items():
        if lang != 'en':
            continue
        for entry in entries:
            for defn in entry.get('definitions', []):
                text = _wk_clean_html(defn.get('definition', ''))
                if text.strip():
                    raws.append(text.strip())
    raws = raws[:6]
    words: set[str] = set(
        t for text in raws
        for t in re.findall(r'[a-z]+', text.lower())
        if t not in _WK_STOPS and len(t) > 3 and t != lemma
    )
    return {"definition_words": sorted(words), "raw_definitions": raws}


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


# ── 5d. Webster 1828 (webstersdictionary1828.com) ────────────────────────────
# Source: webstersdictionary1828.com (American Dictionary of the English
# Language, Noah Webster, 1828).  Definitions fetched per-lemma via HTTP;
# results saved to JSON and loaded at runtime via the path_w1828 parameter
# of build_rings().
#
# Why this resource: theological and Gothic senses are PRIMARY in 1828,
# contemporaneous with Potocki (first pub. 1804) and Poe (1839).  Modern
# resources rank these senses lower in frequency-ordered entry lists.

_W1828_BASE = 'https://webstersdictionary1828.com/Dictionary/{}'


def fetch_w1828(
    lemma_map: dict[str, list[str]],
    out: str = 'definitions_w1828.json',
    delay: float = 1.0,
) -> dict:
    """
    Fetch Webster 1828 definitions from webstersdictionary1828.com.

    Retrieves numbered definition paragraphs (those beginning with a digit
    followed by a period, e.g. "1.Spirit; the soul of man.") from the
    HTML page for each lemma.

    Requires beautifulsoup4::

        pip install beautifulsoup4

    Parameters
    ----------
    lemma_map : lemma → surface-forms dict (from build_lemma_map or custom)
    out       : output JSON path
    delay     : seconds between requests

    Returns
    -------
    dict in the same format as fetch_wiktionary / fetch_wordnet / fetch_mw
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError("beautifulsoup4 required: pip install beautifulsoup4")

    def _extract_defs(lemma: str, paras: list[str]) -> list[str]:
        """
        Extract definition strings from a list of paragraph texts.

        Handles three 1828 entry formats:
          A. Numbered   — '1.Spirit; the soul of man.'
          B. Embedded   — 'GHOST,noun[See Ghastly.] Spirit; ...' (def after last ']')
          C. Unnumbered — header paragraph followed by plain prose paragraphs
                          (only collected when Format A is absent; otherwise those
                          plain paragraphs are usage-example quotations, not defs)
        """
        # Pre-scan: Format C is skipped when numbered definitions exist,
        # because unnumbered paragraphs in a numbered entry are usage examples
        # (Bible verses, illustrative quotations) rather than definitions.
        has_numbered = any(
            len(p) > 2 and p[0].isdigit() and p[1] == '.'
            for p in paras
        )

        word_upper = lemma.upper()
        defs: list[str] = []
        header_seen = False

        for p in paras:
            if not p:
                continue

            # Format A: numbered definition
            if len(p) > 2 and p[0].isdigit() and p[1] == '.':
                text = p[2:].strip()
                text = re.split(r'[;,]\s+as,', text)[0].strip()
                if text:
                    defs.append(text)
                header_seen = True
                continue

            # Detect header paragraph: starts with WORD, or WORD'VARIANT,
            is_header = (
                p.upper().startswith(word_upper + ',') or
                re.match(r"[A-Z']+,", p) is not None
            )

            if is_header:
                header_seen = True
                # Format B: definition embedded after last ']'
                bracket_end = p.rfind(']')
                if bracket_end != -1 and bracket_end < len(p) - 10:
                    after = p[bracket_end + 1:].strip()
                    if after:
                        defs.append(after)
                else:
                    # No brackets: text after the POS abbreviation
                    # e.g. 'WAYFARER,noun A traveler; a passenger.'
                    # e.g. 'DEMON,nounA spirit...' (no space between pos and def)
                    m = re.match(
                        r"[A-Z']+,\s*(?:noun|verb|adjective|adverb|interjection)"
                        r"[a-z .,;'()]*(.+)",
                        p,
                    )
                    if m and m.group(1):
                        candidate = m.group(1).strip()
                        # skip pure cross-reference / etymology notes like [See Ghastly.]
                        if not (candidate.startswith('[') and candidate.endswith(']')):
                            defs.append(candidate)
                continue

            # Format C: plain paragraph after header (unnumbered continuation).
            # Only collect when no numbered definitions exist; otherwise these are
            # usage-example quotations that follow numbered senses.
            if header_seen and not has_numbered and len(p) > 15 and not re.match(r"[A-Z']+,", p):
                defs.append(p)

        return defs[:6]

    def _fetch_one(lemma: str) -> dict:
        url = _W1828_BASE.format(urllib.parse.quote(lemma))
        try:
            r = requests.get(url, headers={'User-Agent': 'IsotopyBot/1.0'}, timeout=10)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')
            col  = soup.find('div', class_='col-md-6')
            if col is None:
                return {'definition_words': [], 'raw_definitions': []}
            paras = [p.get_text(strip=True) for p in col.find_all('p')]
            raws  = _extract_defs(lemma, paras)
            words = sorted({
                w for raw in raws
                for w in re.findall(r'[a-z]+', raw.lower())
                if len(w) > 2 and w != lemma
            })
            return {'definition_words': words, 'raw_definitions': raws}
        except Exception as e:
            print(f"  W1828 error [{lemma}]: {e}")
            return {'definition_words': [], 'raw_definitions': []}

    output: dict = {'lemma_map': lemma_map, 'definitions': {}}
    for i, lemma in enumerate(sorted(lemma_map)):
        print(f"[{i+1}/{len(lemma_map)}] {lemma}...", end=' ', flush=True)
        result = _fetch_one(lemma)
        output['definitions'][lemma] = result
        n = len(result['definition_words'])
        print(f"{n} words" + (" ← empty!" if n == 0 else ""))
        time.sleep(delay)

    with open(out, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Saved {out}  ({len(output['definitions'])} lemmas)")
    return output


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
#   expand() builds IDF-weighted seme profiles (single-hop).
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
    tautology_in_context: bool = False,
    redirect_filter: bool = True,
    length_filter: bool   = True,
) -> RingResult:
    """
    Full two-pass pipeline from JSON definition files to weighted similarity graph.

    Loads the four resource files and delegates to build_rings_from_dicts().

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
    with open(path_wk)    as f: wk    = json.load(f)
    with open(path_wn)    as f: wn    = json.load(f)
    with open(path_mw)    as f: mw    = json.load(f)
    with open(path_w1828) as f: w1828 = json.load(f)

    return build_rings_from_dicts(
        wk=wk, wn=wn, mw=mw, w1828=w1828,
        idf_cutoff=idf_cutoff, lesk_df_max=lesk_df_max, lesk_top_n=lesk_top_n,
        verbose=verbose,
        tautology_in_context=tautology_in_context,
        redirect_filter=redirect_filter,
        length_filter=length_filter,
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
    tautology_in_context: bool = False,
    redirect_filter: bool = True,
    length_filter: bool   = True,
) -> RingResult:
    """
    Identical to build_rings() but accepts pre-loaded dicts instead of file paths.
    W1828 defaults to an empty resource when not supplied (general-text use case).

    Parameters
    ----------
    wk, wn, mw : dicts in the format produced by fetch_wiktionary / fetch_wordnet / fetch_mw
                 i.e. {'definitions': {lemma: {'raw_definitions': [...], ...}}}
    w1828      : same format; pass None to skip (no period-specific lexicon)
    redirect_filter : if True (default), discard senses matching any REDIRECT string
    length_filter   : if True (default), discard senses with ≤ 2 words
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
    def _pass1_semes(lemma: str) -> list[str]:
        """
        Collect semes from the first 3 senses per resource without Lesk
        filtering.  Used only to build the Lesk context.

        Redirect and length filters are always applied.  When
        ``tautology_in_context=True`` the tautology gate is also applied so
        that self-referential definitions are excluded from the context.
        Default (False) matches the original behaviour.
        """
        semes: list[str] = []
        for data in [wk, wn, mw, w1828]:
            for d in data['definitions'].get(lemma, {}).get('raw_definitions', [])[:3]:
                if redirect_filter and any(m in d.lower() for m in REDIRECT):
                    continue
                if length_filter and len(d.split()) <= 2:
                    continue
                toks = tokenize(d)
                if tautology_in_context and is_tautological(toks, lemma):
                    continue
                semes.extend(extract_semes(toks, lemma, nuclear))
        return semes

    lw0 = {l: _pass1_semes(l) for l in lemmas}
    wc0 = Counter(w for ws in lw0.values() for w in set(ws))

    # Lesk context: passage lemmas + low-df semes (passage-specific terms)
    lesk_context: set[str] = lemma_set | {w for w, c in wc0.items() if c <= lesk_df_max}

    # FRAME category 1+2: semantic universals and domain junk that are NOT corpus
    # lemmas.  Excluded from Lesk scoring so they cannot influence sense ranking.
    # Category 3 (FRAME ∩ lemma_set) is kept: those words are passage lemmas and
    # carry genuine disambiguation signal.
    frame_cat12: set[str] = FRAME - lemma_set

    # ── Lesk scorer (closure over lesk_context, frame_cat12) ──────────────────
    def lesk_score(tokens: list[str], lexeme: str) -> int:
        """
        Overlap between pre-tokenized definition tokens and the passage-derived
        Lesk context.  LESK_STOP and FRAME cat 1+2 are filtered here; category 3
        (FRAME ∩ lemma_set, i.e. passage lemmas) contributes disambiguation signal.

        Takes a pre-tokenized list produced by tokenize().
        """
        return len(set(t for t in tokens
                       if t not in LESK_STOP and t != lexeme and t not in frame_cat12)
                   & lesk_context)

    def auto_select_def(lemma: str) -> str:
        """
        PASS 2 — sense selection: for each resource rank non-redirect senses
        by Lesk score; keep top ``lesk_top_n``.

        Each definition is tokenized once via tokenize(); the token list is
        passed directly to lesk_score(), eliminating redundant lemmatization.

        Only the redirect filter (short definitions, REDIRECT strings) is
        applied as a hard pre-filter.  The tautology gate has been removed:
        empirical analysis on the Potocki corpus showed a 77 % false-positive
        rate (definitions rejected because they contain a morphological
        relative of the definiendum but are otherwise informative).  Lesk
        scoring naturally ranks genuinely circular senses low — they have
        almost no content words to overlap with the context.

        Cross-resource consistency gate for Wiktionary:
        Wiktionary senses with zero passage relevance (Lesk score 0) are ranked
        last and fall outside the top_n cut.  W1828 is treated as a primary
        resource; its vocabulary is part of the Lesk context, so WK semes not
        echoed by WN, MW, or W1828 are naturally suppressed.
        """
        parts: list[str] = []
        for data in [wk, wn, mw, w1828]:
            defs = data['definitions'].get(lemma, {}).get('raw_definitions', [])
            candidates = []
            for d in defs:
                if redirect_filter and any(m in d.lower() for m in REDIRECT):
                    continue
                if length_filter and len(d.split()) <= 2:
                    continue
                toks = tokenize(d)
                candidates.append((d, lesk_score(toks, lemma)))
            if not candidates:
                continue
            candidates.sort(key=lambda x: x[1], reverse=True)
            parts.extend(d for d, _ in candidates[:lesk_top_n])
        return ' | '.join(parts)

    # ── PASS 2: merged definitions → semes → IDF → profiles → edges ───────
    merged_text: dict[str, str]        = {l: auto_select_def(l) for l in lemmas}
    lemma_words: dict[str, list[str]]  = {l: extract_semes(tokenize(merged_text[l]), l, nuclear)
                                           for l in lemmas}

    word_count = Counter(w for ws in lemma_words.values() for w in set(ws))
    idf: dict[str, float] = {
        w: math.log(N / c)
        for w, c in word_count.items()
        if c <= N * idf_cutoff
    }

    def expand(lemma: str) -> dict[str, float]:
        """
        IDF-weighted seme profile.

        Seme weights are IDF scores of the lemma's direct definition words
        (single-hop).
        """
        profile: dict[str, float] = defaultdict(float)
        for w in lemma_words.get(lemma, []):
            if w in idf:
                profile[w] += idf[w]
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
# SECTION 8 — SAVE / LOAD RESULTS
# =============================================================================

def save_results(rings: RingResult, tiers: list[ClusterResult], out: str) -> None:
    """
    Serialise pipeline results to JSON.

    Saves the weighted edge graph, per-lemma seme profiles, IDF weights,
    and the three clustering tiers (with top semes per cluster).

    Parameters
    ----------
    rings : RingResult from build_rings()
    tiers : list[ClusterResult] from cluster_isotopies()
    out   : output file path
    """
    tiers_out = []
    for tier in tiers:
        clusters_out = []
        for cl in tier.clusters:
            agg: dict[str, float] = defaultdict(float)
            for lemma in cl:
                for w, s in rings.expanded[lemma].items():
                    agg[w] += s
            top_semes = sorted(agg, key=agg.__getitem__, reverse=True)[:8]
            clusters_out.append({'lemmas': cl, 'semes': top_semes})
        tiers_out.append({
            'label':     tier.label,
            'threshold': tier.threshold,
            'clusters':  clusters_out,
            'isolates':  tier.isolates,
        })

    data = {
        'lemmas':      rings.lemmas,
        'lemma_words': rings.lemma_words,
        'idf':         rings.idf,
        'expanded':    rings.expanded,
        'raw_edges':   [[l1, l2, s] for (l1, l2), s in rings.raw_edges.items()],
        'tiers':       tiers_out,
    }
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f'Results saved → {out}')


def load_results(path: str) -> tuple[dict, list[dict]]:
    """
    Load previously saved pipeline results from JSON.

    Returns
    -------
    (data_dict, tiers)  where data_dict has keys: lemmas, lemma_words, idf,
    expanded, raw_edges (as list of [l1, l2, score] triples).
    tiers is a list of dicts with keys: label, threshold, clusters, isolates.

    Example::

        data, tiers = load_results('data/potocki_results.json')
        for tier in tiers:
            print(tier['label'], len(tier['clusters']), 'clusters')
    """
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return data, data['tiers']


# =============================================================================
# SECTION 9 — CONVENIENCE ENTRY POINT:  run_pipeline()
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
    out:      str | None = None,
    tautology_in_context: bool = False,
    redirect_filter: bool = True,
    length_filter: bool   = True,
) -> tuple[RingResult, list[ClusterResult]]:
    """
    Run the complete isotopy detection pipeline end-to-end.

    Stages:
      1. build_rings()        — load JSON, two-pass Lesk (WK+WN+MW+W1828), IDF, single-hop expansion
      2. cluster_isotopies()  — complete-linkage at three tiers

    Parameters
    ----------
    path_wk, path_wn, path_mw, path_w1828 : paths to pre-fetched definition JSON files
    t_strong, t_medium, t_weak : clustering tier thresholds (absolute IDF units)
    verbose  : print progress and results to stdout
    out      : if given, save results to this JSON path via save_results()

    Returns
    -------
    (RingResult, list[ClusterResult])  — all intermediate data available for inspection

    Example::

        from modules.isotopy import run_pipeline
        rings, tiers = run_pipeline(out='data/potocki_results.json')
        # inspect top edges:
        for (l1, l2), s in sorted(rings.raw_edges.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f'{s:.2f}  {l1}–{l2}')
    """
    rings  = build_rings(path_wk, path_wn, path_mw, path_w1828, verbose=verbose,
                         tautology_in_context=tautology_in_context,
                         redirect_filter=redirect_filter, length_filter=length_filter)
    tiers  = cluster_isotopies(rings, t_strong, t_medium, t_weak, verbose=verbose)
    if out:
        save_results(rings, tiers, out)
    return rings, tiers


# =============================================================================
# SECTION 10 — ABLATION STUDY:  run_ablation()
# =============================================================================

def run_ablation(
    path_wk:     str,
    path_wn:     str,
    path_mw:     str,
    path_w1828:  str,
    output_path: str,
    verbose:     bool = False,
) -> None:
    """
    Run the pipeline six times with different resource configurations and save
    all results to a single JSON file.

    Configurations
    --------------
    1. WK              — Wiktionary only
    2. WN              — WordNet 3.1 only
    3. MW              — Merriam-Webster only
    4. W1828           — Webster 1828 only
    5. WK+WN+MW        — three modern resources, no period lexicon
    6. WK+WN+MW+W1828  — full pipeline

    "Zeroing out" a resource means replacing it with an empty-definition dict
    covering the same lemma set, so the pipeline sees the correct vocabulary
    but gets no content from that resource.

    Because build_rings_from_dicts() derives the lemma list from
    wk['definitions'].keys(), configs where WK is zeroed out pre-seed the
    WK skeleton with the active resource's lemma keys (empty definitions).
    All input dicts are deep-copied so repeated calls cannot interfere.

    Output format
    -------------
    A JSON list of six objects::

        [{"config": "WK", "resources": ["wk"], "tiers": [...]}, ...]

    Each ``tiers`` entry has the same structure as produced by save_results().
    """
    with open(path_wk)    as f: real_wk    = json.load(f)
    with open(path_wn)    as f: real_wn    = json.load(f)
    with open(path_mw)    as f: real_mw    = json.load(f)
    with open(path_w1828) as f: real_w1828 = json.load(f)

    def _empty(source: dict) -> dict:
        """Empty-definition dict seeded with all lemma keys from source."""
        return {'definitions': {
            l: {'raw_definitions': [], 'definition_words': []}
            for l in source['definitions']
        }}

    e_wk    = _empty(real_wk)
    e_wn    = _empty(real_wn)
    e_mw    = _empty(real_mw)
    e_w1828 = _empty(real_w1828)

    # (config_name, resource_labels, wk, wn, mw, w1828)
    # w1828=None signals build_rings_from_dicts to build its own empty envelope.
    configs: list[tuple] = [
        ('WK',             ['wk'],               real_wk,  e_wn,     e_mw,     None       ),
        ('WN',             ['wn'],               e_wn,     real_wn,  e_mw,     None       ),
        ('MW',             ['mw'],               e_mw,     e_mw,     real_mw,  None       ),
        ('W1828',          ['w1828'],            e_w1828,  e_w1828,  e_w1828,  real_w1828 ),
        ('WK+WN+MW',       ['wk','wn','mw'],     real_wk,  real_wn,  real_mw,  None       ),
        ('WK+WN+MW+W1828', ['wk','wn','mw','w1828'], real_wk, real_wn, real_mw, real_w1828),
    ]

    results = []
    for config_name, resource_labels, wk, wn, mw, w1828 in configs:
        if verbose:
            print(f'\n{"─"*60}\n  {config_name}\n{"─"*60}')
        rings = build_rings_from_dicts(
            copy.deepcopy(wk),
            copy.deepcopy(wn),
            copy.deepcopy(mw),
            copy.deepcopy(w1828) if w1828 is not None else None,
            verbose=verbose,
        )
        tiers = cluster_isotopies(rings, verbose=False)

        tiers_out = []
        for tier in tiers:
            clusters_out = []
            for cl in tier.clusters:
                agg: dict[str, float] = defaultdict(float)
                for lemma in cl:
                    for w, s in rings.expanded[lemma].items():
                        agg[w] += s
                top_semes = sorted(agg, key=agg.__getitem__, reverse=True)[:8]
                clusters_out.append({'lemmas': cl, 'semes': top_semes})
            tiers_out.append({
                'label':     tier.label,
                'threshold': tier.threshold,
                'clusters':  clusters_out,
                'isolates':  tier.isolates,
            })

        n_edges = len(rings.raw_edges)
        summary = '  '.join(
            f'{t.label}: {len(t.clusters)} clusters'
            for t in tiers
        )
        print(f'[{config_name:20s}]  {n_edges} edges  |  {summary}')

        results.append({
            'config':    config_name,
            'resources': resource_labels,
            'tiers':     tiers_out,
        })

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f'\nAblation saved → {output_path}')


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
    parser.add_argument('--fetch-wk',    action='store_true', help='Fetch Wiktionary definitions')
    parser.add_argument('--fetch-wn',    action='store_true', help='Build WordNet definitions (needs --wn-dir)')
    parser.add_argument('--fetch-mw',    action='store_true', help='Fetch MW definitions (needs MW_API_KEY)')
    parser.add_argument('--wn-dir',      default='wn3.1.dict/dict', help='WordNet dict folder')
    parser.add_argument('--ablation',    action='store_true', help='Run six-config ablation study')
    parser.add_argument('--ablation-out', default='ablation.json', help='Output path for ablation JSON')
    parser.add_argument('--out',         default=None, help='Output path for pipeline results JSON')
    args = parser.parse_args()

    if args.fetch_wk:
        fetch_wiktionary()
    if args.fetch_wn:
        fetch_wordnet(dict_dir=args.wn_dir)
    if args.fetch_mw:
        fetch_mw()
    if not (args.fetch_wk or args.fetch_wn or args.fetch_mw):
        if args.ablation:
            run_ablation(args.path_wk, args.path_wn, args.path_mw, args.path_w1828,
                         output_path=args.ablation_out)
        else:
            run_pipeline(args.path_wk, args.path_wn, args.path_mw, args.path_w1828,
                         out=args.out)
