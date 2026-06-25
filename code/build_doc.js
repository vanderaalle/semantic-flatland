const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType, PageBreak,
} = require('docx');
const fs   = require('fs');
const path = require('path');

const FIGS  = '/home/claude/figs';
const AGRAPHS = '/home/claude/appendix_graphs';

// ── helpers ──────────────────────────────────────────────────────────────────
const FONT = 'Arial';
const BLACK = '1A1A1A', DARK = '444444', MID = '888888', PALE = 'F5F5F5';

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 320, after: 160 },
    children: [new TextRun({ text, bold: true, size: 28, font: FONT, color: BLACK })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 240, after: 120 },
    children: [new TextRun({ text, bold: true, size: 24, font: FONT, color: BLACK })],
  });
}
function body(text) {
  return new Paragraph({
    spacing: { before: 100, after: 100 },
    children: [new TextRun({ text, size: 22, font: FONT, color: BLACK })],
  });
}
function bullet(text) {
  return new Paragraph({
    bullet: { level: 0 },
    spacing: { before: 80, after: 80 },
    children: [new TextRun({ text, size: 22, font: FONT, color: BLACK })],
  });
}
function mono(text) {
  return new Paragraph({
    spacing: { before: 80, after: 80 },
    indent: { left: 720 },
    children: [new TextRun({ text, size: 20, font: 'Courier New', color: BLACK })],
  });
}
function callout(label, text) {
  const bg = label === 'KEY' ? '1A1A1A' : label === 'WHY' ? '444444' : label === 'FIX' ? '333333' : '444444';
  return new Paragraph({
    spacing: { before: 160, after: 160 },
    border: { left: { style: BorderStyle.THICK, size: 8, color: bg, space: 10 } },
    shading: { type: ShadingType.CLEAR, fill: 'F8F8F8' },
    children: [
      new TextRun({ text: label + '  ', bold: true, size: 20, font: FONT, color: bg }),
      new TextRun({ text, size: 20, font: FONT, color: DARK, italics: true }),
    ],
  });
}
function imgPara(fname, widthIn, aspectRatio, caption) {
  const p = path.join(FIGS, fname);
  if (!fs.existsSync(p)) return [body(`[Figure: ${fname}]`)];
  const buf = fs.readFileSync(p);
  const w = Math.round(widthIn * 914400);
  const h = Math.round(w * aspectRatio);
  const results = [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 160, after: 80 },
      children: [new ImageRun({ data: buf, transformation: { width: Math.round(widthIn*96), height: Math.round(widthIn*96*aspectRatio) } })],
    }),
  ];
  if (caption) results.push(new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 40, after: 160 },
    children: [new TextRun({ text: caption, size: 18, font: FONT, color: MID, italics: true })],
  }));
  return results;
}
function numbered(items) {
  return items.map(t => new Paragraph({
    spacing: { before: 80, after: 80 },
    indent: { left: 360 },
    children: [new TextRun({ text: t, size: 22, font: FONT, color: BLACK })],
  }));
}
function noBorder() {
  const b = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
  return { top: b, bottom: b, left: b, right: b };
}

// ── Cat1 organized list ───────────────────────────────────────────────────────
const CAT1_GROUPS = [
  {
    label: 'Closed-class function words',
    desc: 'Grammatically functional words with no semantic content of their own: articles, prepositions, conjunctions, auxiliaries, pronouns, determiners.',
    words: ['the','and','but','for','not','with','from','into','onto','upon','or',
            'that','this','which','who','what','how','when','where','why',
            'also','such','any','all','more','most','much','many','very','well',
            'even','just','already','still','often','usually','typically','especially',
            'another','various','yet','nor','both','each','few','own','off','out',
            'over','those','some','through','within','without','per',
            'can','may','will','shall','must','would','could','should',
            'its','his','her','our','their','your','one','two','six',
    ],
  },
  {
    label: 'Semantically bleached verbs',
    desc: 'Verbs that appear in definitions as structural connectives rather than as content markers. Their presence signals what a concept does, not what it means.',
    words: ['make','take','come','give','get','go','see','know','say','find',
            'keep','seem','remain','become','move','call','refer','relate',
            'involve','characterize','associate','use','put','exist',
            'come','give','get','go','know','give',
    ].filter((v,i,a)=>a.indexOf(v)===i),
  },
  {
    label: 'Generic frame nouns and adjectives',
    desc: 'Nouns and adjectives that appear as definitional scaffolding: they describe the logical category of the definiendum rather than its specific semantic content.',
    words: ['person','people','someone','something','animal','human','creature','organism','being',
            'thing','object','kind','type','form','manner','way','part',
            'state','condition','act','action','cause','result',
            'place','time','amount','number','distance','extent',
            'general','common','particular','specific','single','certain',
            'possible','impossible','likely','capable','able',
            'similar','true','false','real','actual','original','apparent',
            'physical','mental','natural',
            'large','small','great','long','high','deep','wide','broad','near',
            'sky','rock','stone','earth','ground','surface','structure','frame','land',
            'widely','diffuse','charge','ahead','point',
    ],
  },
];


// ── document ──────────────────────────────────────────────────────────────────
const LEMMAS = [
  'agree','approach','argument','attest','avert','body','break','brother',
  'catch','claim','consent','corpse','curiosity','demon','eerie','entrance',
  'escape','execute','eye','fact','flesh','force','free','gallows','gaze',
  'ghastly','ghost','gyration','hang','hear','heaven','hideous','horrified',
  'hurry','implausible','innocent','lead','living','make','meet','mountain',
  'nameless','night','old','possess','prison','prompt','prove','refuge',
  'revolting','rumour','say','sceptical','see','set','sound','species',
  'spectacle','story','strange','supposition','swing','take','tale','tear',
  'tell','theologian','thesis','think','torment','track','traveller','unjust',
  'valley','vampire','vengeance','vulture','wayfarer','widespread','wind','write',
];

const doc = new Document({ sections: [

// ── MAIN DOCUMENT ─────────────────────────────────────────────────────────────
{
  properties: {},
  children: [

    // title
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 1440, after: 400 },
      children: [new TextRun({ text: 'Computational Lexicon-Based\nIsotopy Detection\nfor Dummies', bold: true, size: 52, font: FONT, color: BLACK, break: 1 })]}),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: 'A step-by-step guide with worked examples', size: 26, font: FONT, color: DARK, italics: true })]}),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: 'Andrea Valle · Basic Semiotic Modelling · Logos Verlag', size: 22, font: FONT, color: MID })]}),
    new Paragraph({ children: [new PageBreak()] }),

    // ── THE PASSAGE ────────────────────────────────────────────────────────────
    h1('The passage'),
    body('The analysis in this document is grounded in a single passage from Jan Potocki\'s The Manuscript Found in Saragossa (first published 1804–1810). The passage is from the First Day — the description of the Valle de los Hermanos (Valley of the Brothers), narrated by Alphonse van Worden as he approaches the gallows where the brothers Zoto were executed. This is the passage:'),
    new Paragraph({
      spacing: { before: 200, after: 200 },
      indent: { left: 720, right: 720 },
      border: { left: { style: BorderStyle.THICK, size: 6, color: '444444', space: 12 } },
      children: [new TextRun({ italics: true, size: 22, font: FONT, color: BLACK,
        text: 'Two of the three brothers had been caught and their bodies could be seen hanging from the gallows at the entrance to the valley; Zoto, the eldest, had escaped from prison in Córdoba and was thought to have taken refuge in the Alpujarras mountains. Very strange tales were told about the two brothers who had been hanged; they were not said to be ghosts, but it was claimed that at night nameless demons would possess their bodies, which would break free from the gallows and set out to torment the living. This was taken to be so well attested that a theologian from Salamanca had written a thesis proving that the two hanged brothers were species of vampire, and that the supposition that one of them should be a vampire was no less implausible than that the other should be so: an argument that even the most sceptical were forced to agree was sound. There was also a widespread rumour that the two brothers were innocent and that, having been unjustly executed, they took vengeance on travellers and other wayfarers with the consent of heaven. As I had heard these stories in Córdoba, curiosity prompted me to approach the gallows. The spectacle that met my eyes was made all the more revolting by the fact that the ghastly corpses were swung in eerie gyrations in the wind, while hideous vultures tore at their flesh. Horrified, I averted my gaze and hurried along the track leading to the mountains.',
      })],
    }),
    body('Jan Potocki, The Manuscript Found in Saragossa, trans. Ian Maclean (London: Penguin, 2008), First Day.'),
    new Paragraph({ spacing: { before: 120 }, children: [new TextRun({ text: 'The passage yields 81 content-word lemmas. These are the input vocabulary for the entire pipeline that follows.', size: 22, font: FONT, color: DARK, italics: true })]}),
    new Paragraph({ children: [new PageBreak()] }),

    // ── §1 WHAT IS ISOTOPY ─────────────────────────────────────────────────────
    h1('§1  What is isotopy?'),
    body('Greimas introduced the concept of isotopy in 1966 to describe the semantic coherence of a text. When we read a passage and it feels like it is "about" something — death, horror, legal process — that feeling has a structural basis: certain semantic features repeat across different words. These repeated features are semes. A set of lexemes that share one or more semes constitutes an isotopy.'),
    body('Isotopy is properly a common semantic plane shared by multiple lexemes by means of a common subset of semes. Figure 1 shows a possible configuration: ghost and demon share soul and spirit, constituting a semantic plane that is their isotopy. Despite the widespread use of the term in semiotics and narratology, there is currently no operational pipeline that allows constructing such a structure automatically from a text. This document describes one.'),
    ...imgPara('fig1_isotopy_concept.png', 6.5, 3.2/7, 'Figure 1. Ghost and demon share the semes soul and spirit, forming the supernatural–death isotopy.'),
    callout('KEY', 'Isotopy = a set of lexemes sharing repeated semantic features (semes). The more semes they share, and the rarer those semes are, the stronger the isotopy.'),
    new Paragraph({ spacing: { before: 120 }, children: [new TextRun('')] }),

    h2('A note on terminology'),
    body('Greimas\'s semanalysis distinguishes two types of seme: nuclear semes, which individuate a lexeme and constitute its specific semantic identity, and classemes, which operate at the textual level and create isotopic coherence by repeating across multiple lexemes. In principle, a classeme is a seme that functions paradigmatically across a text; a nuclear seme is what remains when classemes are subtracted.'),
    body('BSM does not implement this distinction. Every definition word that survives the FRAME filter is treated as a potential seme contributing to isotopy evidence. We use the term seme throughout — not classeme — because we make no analytic classification of individual features into nuclear or classematic roles. IDF weighting functions as a continuous substitute for that distinction: high-IDF semes (low df, specific to few lemmas) behave empirically like nuclear semes; low-IDF semes (high df, shared across many lemmas) behave like classemes. But we do not classify — we weight. This is the minimalist choice: one mechanism does the work of a two-level analytic framework.'),
    body('The FRAME filter — described in §5 — also departs from Greimasian terminology. In Greimas, nuclear semes are central to the lexeme\'s semantic identity. Our FRAME set contains the opposite: words that are definitionally ubiquitous precisely because they are semantically empty in context — the metalanguage of lexicography, not the content of lexemes. The name FRAME is explained in §5.'),
    new Paragraph({ spacing: { before: 120 }, children: [new TextRun('')] }),
    h2('Isotopy and memory'),
    body('Isotopy is not a property of the text alone — it is a property of the text relative to a reader holding a portion of it in memory. A reader who has just encountered the word ghost has no isotopy yet. A reader who has encountered ghost, demon, vampire, and corpse in succession begins to recognise a pattern. Isotopy is the stabilisation of that pattern over a reading horizon.'),
    body('This means isotopy is parameterised by memory size. At window size zero there is no isotopy — each word is isolated. At window size equal to the full text, the maximal isotopy structure is available. In between, isotopies emerge, consolidate, and sometimes dissolve as the window expands.'),
    body('Greimas and Eco are not opposed on this point — they work at different memory windows. Greimas\'s own analyses (Maupassant, 1976; Du Sens, 1970) operate at maximum window: the text is treated as a synchronic object and its isotopy structure is read off the full inventory of lexemes. This is the classical move of totalization — all senses are in principle available, and the analyst consults the dictionary (classically the Petit Robert) to establish seme membership. Eco\'s Model Reader (Lector in Fabula, 1979) works at a progressive, bounded window: the reader accumulates context as they read, activates senses compatible with what has been encountered so far, and may revise or forget earlier assignments. The two accounts are complementary descriptions of the same phenomenon at different temporal scales.'),
    body('The pipeline in this document operates at maximum window — the classical Greimasian reading. It takes the Day 1 passage as a single pre-delimited unit and recovers the isotopy structure available to a reader who holds the entire passage in memory.'),

    h2('The Model Reader and the encyclopedia'),
    body('Eco\'s Model Reader (Lector in Fabula, 1979) is the reader inscribed in the text as a set of interpretive competences — the reader the text presupposes in order to be understood. Central among those competences is encyclopedic knowledge: the reader must know which semantic fields the vocabulary belongs to in order to recognise isotopies.'),
    body('The pipeline operationalises this encyclopedic competence as a set of lexical resources. The isotopy structure the pipeline recovers is the one available to a Model Reader equipped with those resources. A different encyclopedia produces a different isotopy structure — which is precisely what the resource comparisons in §8 and §10 demonstrate.'),
    callout('KEY', 'The pipeline models the retrospective Model Reader at window size = full chunk — the classical Greimasian analysis — equipped with a specific encyclopedia. Both parameters are explicit and replaceable.'),
    new Paragraph({ spacing: { before: 120 }, children: [new TextRun('')] }),
    body('The computational challenge is to operationalize this: how do we automatically detect which lexemes share semes, across a literary passage, without reading the text ourselves? The answer is the lexicon-based pipeline described in this document.'),

    // ── §2 PIPELINE ────────────────────────────────────────────────────────────
    h1('§2  The pipeline at a glance'),
    body('The pipeline has five stages, each corresponding to a theoretical decision:'),
    ...imgPara('fig2_pipeline.png', 6.5, 2.4/7, 'Figure 2. The five-stage pipeline from literary passage to isotopy clusters.'),
    ...numbered([
      '1.  Extract content words from the passage [§3]',
      '2.  Look up their definitions in lexical resources [§4]',
      '3.  Extract semes from those definitions, filtering out non-informative words [§5]',
      '4.  Build a weighted similarity graph between lemmas [§6]',
      '5.  Cluster the graph to reveal isotopy groups [§7]',
    ]),
    body('Each stage involves principled decisions. The rest of this document explains each one in detail, with concrete examples drawn from Jan Potocki\'s The Manuscript Found in Saragossa (Day 1).'),

    // ── §3 CONTENT WORDS ───────────────────────────────────────────────────────
    h1('§3  Extracting content words'),
    body('We begin by identifying the content words in the passage — nouns, verbs, adjectives, and adverbs that carry semantic weight, as opposed to function words (articles, prepositions, conjunctions) which express grammatical relations but carry no semantic content of their own.'),
    ...imgPara('fig3_passage_annotation.png', 6.5, 2.0/7, 'Figure 3. A sentence from Potocki Day 1. Highlighted words are content words; grey words are function words.'),
    body('Once identified, each content word is lemmatized — reduced to its dictionary form (corpses → corpse, gyrations → gyration, hung → hang). This gives us our working vocabulary of N = 81 lemmas for the Day 1 passage.'),
    callout('WHY', 'We lemmatize before looking up definitions because dictionaries index by base form. corpses would not be found, but corpse will be.'),
    new Paragraph({ spacing: { before: 120 }, children: [new TextRun('')] }),

    // ── §4 DICTIONARY DEFINITIONS ──────────────────────────────────────────────
    h1('§4  Dictionary definitions'),
    body('For each lemma we look up its definition in one or more lexical resources. Each resource is fetched once and saved as a JSON file. The pipeline reads these files at run time and concatenates definitions per lemma before the filtering described in §5. The JSON format, fetch scripts, and available resources are documented in Appendix B.'),
    ...imgPara('fig4_seme_extraction.png', 6.5, 3.0/7, 'Figure 4. From lemma to semes: dictionary lookup → raw definition → filter → seme list.'),

    h2('Sense selection'),
    body('Dictionaries give multiple senses per lemma, ordered by 21st-century corpus frequency. This is the wrong criterion for a passage from 1804. The pipeline applies two numbered steps to select the appropriate senses.'),
    body('Step 1 — Tautology gate. Every sense from every resource is tested: if any token in the definition shares the first five characters of the lemma, the sense is rejected as circular. This is a structural criterion, resource-independent and always applied. A definition of gyration that uses gyrating tells us nothing about gyration\'s semantic neighbourhood.'),
    body('Step 2 — Lesk selection. After the gate, surviving senses are ranked by Lesk score: the overlap between the sense\'s tokens and the passage-derived context. The context has two components: the 81 corpus lemmas themselves, plus all seme words that appear in ten or fewer of the 81 first-pass definitions. The first component is direct: a definition of hang that mentions gallows scores high immediately because gallows is a corpus lemma. The second component captures rare, passage-specific vocabulary — words like supernatural (appearing in only 2 of the 81 definitions: demon and eerie), haunt (appearing in only 1, from ghost), anguish (appearing in only 1, from torment) that are not corpus lemmas themselves but are characteristic of this text\'s semantic world. A sense of ghost that uses supernatural scores high from this component. A sense of ghost about ghostwriting or ghost towns scores low. The top two senses per resource are appended to the merged definition.'),
    callout('KEY', 'Step 1 (tautology gate) is universal. Step 2 (Lesk) corrects for frequency bias in resources whose sense ordering reflects modern corpus frequency. Both steps produce the same output: definition text appended per lemma.'),

    // ── §5 CLASSEMES ───────────────────────────────────────────────────────────
    h1('§5  Extracting and weighting semes'),

    h2('The FRAME stop set'),
    body('The name FRAME requires explanation. Several candidates describe this set:'),
    bullet('STOP — the standard NLP term, following van Rijsbergen (1979) and Salton & McGill (1983). Stopword lists remove high-frequency function words before indexing. Our set overlaps with stopwords but is assembled differently: by inspection of definitional metalanguage, not by corpus frequency alone. The BNC top-2000 frequency test (see Appendix C) confirmed that frequency alone is insufficient — many definitionally ubiquitous words do not appear in frequency lists, and many frequent English words are legitimate semes in this passage.'),
    bullet('SCAFFOLD — describes what the words do structurally. A definition "a person who performs X" uses person and performs as scaffold; X is the content. Vivid, but not a standard term.'),
    bullet('META — these are metasemiotic words: words about the act of defining rather than about the definiendum. "A term used to describe..." — term, used, describe are metasemiotic. Theoretically precise but opaque to non-specialists.'),
    bullet('FRAME — chosen. Definitional frame vocabulary is the fixed phraseological structure that lexicographic writing deploys to situate a definiendum in a logical category before specifying its content. The concept connects loosely to Fillmore\'s frame semantics: these words activate the frame of lexicographic discourse, not the frame of the definiendum. FRAME also connects to our Appendix C heading, already written as "definitional frame vocabulary", and carries no conflict with any Greimasian term.'),
    body('The FRAME set is organized into three categories with distinct rationales, described below and documented fully in Appendix C.'),
    body('Not all words in a definition carry isotopy evidence. The word "person" appears in dozens of definitions but tells us nothing about the specific semantic content of a lemma. Such words must be filtered out before building the similarity graph.'),
    body('We maintain a FRAME set of excluded words, organized into three principled categories:'),
    ...imgPara('fig12_nuclear.png', 6.5, 3.2/7, 'Figure 5. The three-category taxonomy of the FRAME stop set. Each category has a distinct theoretical rationale.'),
    body('Category 1 — Definitional frame vocabulary: words that appear in dictionary entries as structural scaffolding rather than as semantic content markers. This includes closed-class function words, semantically bleached verbs (make, take, come, give), and generic frame nouns and adjectives (person, thing, state, kind). These words describe the logical category of the definiendum, not its specific semantic content. The full list is documented in Appendix C.'),
    body('Category 2 — Domain junk: words that enter via wrong senses in a specific dictionary. Examples: eggs, fowl, hatching from Merriam-Webster\'s brooding-hen sense of set; ISO 639 language codes from Wiktionary (the code "say" is ISO 639-3 for the Saya language). These are resource-specific artifacts, documented per resource.'),
    body('Category 3 — Corpus-lemma semes: words that are simultaneously definition words and corpus lemmas. Using the passage\'s own vocabulary to bridge definitions creates circular evidence (see §5.3).'),

    h2('IDF weighting'),
    callout('DEF', 'df(w) — document frequency: the number of lemma definitions, out of 81, that contain word w after FRAME filtering and lemmatization. A word with df=2 appears in 2 definitions; a word with df=40 appears in 40.'),
    body('IDF serves three distinct roles in the pipeline:'),
    body('Role 1 — Filter (binary). Words with df(w) > 0.45 × N = 36 are discarded entirely. They appear in too many of the 81 definitions to discriminate between lemmas. This is a hard cutoff: the word is removed before any scoring.'),
    body('Role 2 — L1 weight (continuous). For words that survive the filter, if w appears in a lemma\'s direct (L1) definition profile, it contributes IDF(w) to that lemma\'s seme profile.'),
    body('Role 3 — L2 weight (continuous, discounted). If w is reached via L2 expansion — following an intermediate word one step further — it contributes 0.5 × IDF(w). The discount reflects the indirection: the connection is less direct and should carry less weight.'),
    body('The formula for IDF(w) is:'),
    mono('IDF(w) = log( N / df(w) )'),
    body('N = 81 — the number of lemma definitions, not the number of unique seme types. The seme vocabulary is much larger (several hundred words), but N counts the reference population for discrimination: how many of the 81 lemma profiles contain w. This is a deliberate departure from standard information-retrieval IDF where N is the document count. Here our \'documents\' are exactly the 81 lemma profiles. IDF therefore measures inter-lemma discrimination within this passage.'),
    body('The logarithm is essential. Without it, a word with df=1 would get weight N/1 = 81, completely dominating every edge it touches. The log compresses the scale: log(81/1)=4.39, log(81/2)=3.70, log(81/3)=3.30. Differences between rare words remain meaningful, but no single word explodes the score. The log also has an information-theoretic motivation: log(N/df) = −log(df/N) is the information content of an event with base rate df/N. Rare words are more surprising; surprise is isotopy evidence.'),
    body('The three roles interact in the score formula. IDF(w) is a property of the word w; the edge score between two lemmas is a relational property computed from pairs of per-lemma IDF values:'),
    mono('score(l₁, l₂) = Σ_w  min( profile_l₁(w),  profile_l₂(w) )'),
    body('where profile_l(w) = IDF(w) if w is in l\'s L1 profile, 0.5 × IDF(w) if in L2, and 0 otherwise. The minimum captures the weaker signal when the two lemmas have the seme at different expansion levels: if l₁ has w at L1 (weight IDF(w)) and l₂ has it at L2 (weight 0.5 × IDF(w)), the contribution to their edge score is min(IDF(w), 0.5 × IDF(w)) = 0.5 × IDF(w). The min also ensures that a globally rare word that barely features in one lemma\'s profile does not artificially inflate the score.'),
    body('Concretely: soul (df=2, IDF=3.30) appears in the definitions of ghost and demon only — almost no other lemma uses it. Finding it in both profiles is strong evidence of a shared semantic field. dead (df=12, IDF=2.45) turns up across a wide range of definitions; it is meaningful but less discriminating. Soul carries stronger isotopy signal than dead precisely because it is rarer.'),
    ...imgPara('fig6_idf.png', 6.0, 3.0/6, 'Figure 6. IDF weight as a function of df. The cutoff at df=36 removes words too common to discriminate. For words below the cutoff, IDF is a continuous weight used in the score formula — not a threshold.'),

    body('In the figures below, edge labels show IDF(w) — a property of the seme word w, not of the relation between lemma and seme. The edge TEAR→rend labelled 4.39 means: rend is a seme in tear\'s profile, and rend has rarity weight 4.39 across the 81 definitions. The weight belongs to the node rend; it is displayed on the edge for readability. This is not the same as an edge score between two lemmas — that is computed later, in §6, from pairs of these per-seme weights.'),
    h2('L2 expansion and the corpus-lemma constraint'),
    body('Single-sentence dictionary definitions are often thin — ghost: "the soul of a dead person; a spirit appearing after death." A direct seme extraction yields a handful of words. To enrich the profile, we allow the pipeline to follow each L1 seme one step further into the definitional network, adding its own definition words at half weight. This is radius-2 (L2) expansion.'),
    body('The choice of radius 2 is not arbitrary — but it is also not quite a cutoff. The pipeline applies a weight scaling at each expansion level: L1 semes contribute at weight 1.0, L2 at weight 0.5. This is the first two steps of a general decay principle: weight at depth n = (0.5)^(n−1). In principle the expansion continues indefinitely; in practice the weights collapse. At L6 the contribution per seme is (0.5)^5 ≈ 0.016 — negligible against any meaningful threshold. The lemma acts not as a node connected to a fixed neighbourhood but as a focusing point radiating into the encyclopedic graph with force that falls off exponentially with distance.'),
    body('The design space can be read as four limiting cases of this decay:'),
    bullet('L0 — semiotic monoplanarity: decay is infinite from the start. No definitions consulted, no semes extracted. The lemma is a pure opaque form with zero semantic reach.'),
    bullet('L1 — minimal semiotic act: weight 1.0 at depth 1, zero beyond. Expression mapped to content by one reading of the definition. Already two-plane, but thin where definitions are sparse.'),
    bullet('L2 (implemented): weights 1.0 at L1, 0.5 at L2, zero beyond. Bridges thin definitions and captures genuine analogical connections — ghost reaching eternal via spirit — without dissolving local semantic structure.'),
    bullet('L∞ with uniform weight: no decay. The definitional network has the small-world property — mean path length 4–6 steps. Without decay, at L3–4 a very large fraction of the lexicon is reachable from any lemma. Every pair shares semes; the clusters become semantically meaningless.'),
    body('The full decay model — (0.5)^(n−1) for all n — is therefore the theoretically coherent position: the encyclopedic graph is always present, the lemma always has some purchase on it, but that purchase diminishes exponentially. L2 is a practical implementation of this principle: beyond depth 2 the contributions fall below the noise floor of the scoring function, so the expansion need not be computed. The lemma is a point of semantic gravity; the network around it does not stop at L2 — it fades.'),
    body('This connects directly to Eco’s encyclopedia. Model Q (Eco 1984) is an n-dimensional labyrinth with no centre and no periphery — every node reachable from every other via sufficiently long paths. Unlimited semiosis (Peirce) operates on this structure: any sign can lead to any other through a chain of interpretants. The decay model does not reject this — it quantifies it. The further a seme is from the lemma in the definitional graph, the less it contributes to the lemma’s isotopy signal. The encyclopedia is fully present; the isotopy detector just has diminishing sensitivity to its remoter regions. Beyond the practical L2 cutoff, the model no longer tracks the passage — it tracks the language.'),
    body('However, the 81 corpus lemmas are drawn directly from the passage. Many ordinary English words that appear in definitions — force, free, dead, wind, tear — happen also to be corpus lemmas. When tear\'s definition says "pull apart by force", L2 expansion would look up force as an intermediate and import all of force\'s semes: compel, coercion, vigor, might, efficacy, military, army, troop. None of these belong to tear\'s isotopy. They describe force as a military and physical concept, not tear as an act of physical rupture. The connection is purely incidental — tear mentioned force in passing, as a means of action, not as a semantic neighbour.'),
    ...imgPara('fig7_l2_expansion.png', 7.0, 2.8/10.5, 'Figure 7. Left: tear\'s L1 semes. Right: L2 with corpus-lemma constraint — force skipped; L2 via rend. Edge labels show IDF(w): a property of each seme word, not of the lemma-seme relation.'),
    body('The solution is a principled constraint: L2 expansion skips any intermediate word that is itself a corpus lemma. This is not a patch — it is a theoretical decision about what counts as evidence. A corpus lemma appearing in a definition is not evidence of semantic neighbourhood; it is evidence that the defined concept stands in some relation (however peripheral) to the lemma\'s semantic field. That relation is already captured at L1 by the presence of the corpus lemma in the definition. Importing the corpus lemma\'s own semes via L2 would double-count and distort.'),
    body('Non-corpus intermediates like rend, lacerate, violence are not in the passage vocabulary and can be followed freely. They genuinely extend the semantic profile without creating circular evidence.'),
    ...imgPara('fig7b_corpus_lemma.png', 7.0, 3.8/7.5, 'Figure 8. The corpus-lemma constraint. force appears in TEAR\'s L1 ring (red) with IDF=3.70 — a property of the word force measuring its rarity across the 81 definitions, not of the TEAR–force relation. Because force is a corpus lemma, L2 expansion via force is blocked. FORCE independently has its own L1 ring on the right.'),
    // ── §6 SIMILARITY GRAPH ────────────────────────────────────────────────────
    h1('§6  Building the similarity graph'),
    body('After extracting and weighting semes for each lemma, we compute a similarity score for every pair of lemmas — all 81×80/2 = 3,240 pairs. The result is a complete weighted graph: every lemma is connected to every other lemma, with a score that is zero if they share no semes and positive otherwise. This complete graph is then sparsified by thresholding: edges below a given score are removed, leaving only the pairs with sufficient shared seme evidence. The choice of threshold — and the argument for using multiple thresholds rather than one — is discussed in §7.'),
    body('The intermediate structure that makes the scores computable is a bipartite graph: lemmas on one side, semes on the other, with weighted edges recording which semes each lemma\'s expanded profile contains.'),
    ...imgPara('fig5_bipartite.png', 6.5, 4.0/7, 'Figure 9. Bipartite graph for five supernatural/uncanny lemmas. Edge labels show IDF(w) — a property of each seme word (how rare it is across the 81 definitions), displayed on the edge for readability. Filled seme nodes are shared by two or more lemmas.'),
    body('The similarity score between two lemmas is the sum of the minimum IDF weights of their shared semes:'),
    mono('score(l₁, l₂) = Σᵤ min( IDF₁(w), IDF₂(w) )'),
    body('The minimum operator ensures that a word carrying low weight in either lemma\'s profile does not artificially inflate the score. The sum rewards multiple shared semes: two lemmas sharing three specific words are more isotopically related than two sharing one generic word.'),
    body('Applying this formula to every pair of the 81 lemmas produces a weighted lemma-to-lemma similarity graph — the projection of the bipartite graph onto the lemma side. The seme nodes disappear; what remains is a graph over lemmas in which each edge carries the score computed from their shared semes. This is the graph that gets thresholded and clustered.'),
    ...imgPara('fig_projection.png', 6.5, 2.8/8.5,
        'Figure 10. From bipartite to similarity graph. Left: the bipartite structure; edge labels show IDF(w), a property of each seme word. Right: the projected lemma-to-lemma graph; edge labels now show similarity scores — relational properties between lemma pairs, computed as Σ min(IDF₁(w), IDF₂(w)) over shared semes. ghost–demon score 6.09 = min(3.30,3.30) + min(2.79,2.79). Edge thickness reflects score.'),
    body('Thresholds are set at three absolute levels (strong t≥10, medium t≥8, weak t≥5) in raw IDF units. Absolute thresholds are preferred over normalized ones because isotopic density varies by semantic field: lexically overdetermined isotopies (dense narrative vocabulary) produce high scores, while obliquely evoked isotopies (sparse supernatural vocabulary) produce low scores. A single normalized threshold would erase this difference. The empirical score distribution confirming this multi-scale structure is shown in §8.'),

    // ── §7 CLUSTERING ──────────────────────────────────────────────────────────
    h1('§7  Clustering: from graph to isotopies'),

    h2('Why complete-linkage?'),
    body('Once we have a weighted similarity graph, we need to decide which lemma pairs belong to the same isotopy. The naive approach is to set a threshold and declare all pairs above it as connected — but how we group connected pairs into clusters matters enormously.'),
    body('The simplest clustering method — single-linkage, or union-find — works as follows: start with every lemma as its own cluster; then scan all edges above threshold from strongest to weakest; whenever an edge connects two different clusters, merge them into one. The result is that two lemmas end up in the same cluster if there exists any chain of above-threshold edges connecting them, however indirect.'),
    body('This creates the chain problem. Suppose ghost and demon share soul and spirit strongly (score 12.0). Suppose demon and night share a single seme darkness weakly (score 6.0). Suppose night and corpse share decay (score 7.0). Under single-linkage at threshold 5, all four lemmas end up in one cluster: ghost–demon–night–corpse. But ghost and night share nothing. Ghost and corpse share nothing. The cluster is held together entirely by two weak transitive bridges — demon connecting to night, night connecting to corpse — neither of which establishes any direct semantic relationship between ghost and the night/corpse pair.'),
    body('This is not a technical inconvenience. It is a theoretical error. Greimas defines isotopy as the redundancy of semes across a reading: a semantic axis is isotopic when multiple lexemes independently reinforce it. Redundancy requires direct co-occurrence — two lemmas sharing semes — not transitive chains. If ghost and night do not share semes, they do not mutually reinforce any semantic axis, and they should not be in the same isotopy.'),
    body('Complete-linkage enforces this directly: two lemmas may only be in the same cluster if every pair within the cluster exceeds the threshold. The similarity graph is undirected by construction — score(l₁,l₂) = score(l₂,l₁) because min(IDF_l₁(w), IDF_l₂(w)) is symmetric. There is therefore no notion of direction in the clustering: \'every pair directly connected\' means a single undirected edge above threshold between each pair of cluster members. No directed traversal, no asymmetric paths. A cluster under complete-linkage is a clique in the thresholded graph — every member is directly connected to every other member. This is the computational translation of Greimas\'s redundancy criterion.'),
    callout('KEY', 'Single-linkage asks: is there a path between these two lemmas? Complete-linkage asks: do these two lemmas share direct evidence? Only the second question corresponds to isotopy as redundancy of semes.'),
    new Paragraph({ spacing: { before: 120 }, children: [new TextRun('')] }),
    ...imgPara('fig9_clustering.png', 6.5, 3.2/7, 'Figure 11. Single-linkage (left) merges all six lemmas into one cluster via weak transitive bridges — night connects ghost to corpse via separate weak edges. Complete-linkage (right) produces two tight clusters; night is isolated because it has no direct strong edge to any potential cluster partner.'),

    h2('The three-tier result'),
    body('Applying complete-linkage at three absolute threshold levels gives the following isotopy structure for Potocki Day 1:'),
    ...imgPara('fig10_tiers.png', 6.5, 6.8/8.5, 'Figure 12. Isotopy clusters at three threshold levels. Each cluster is shown with its top shared semes — the words that actually hold the cluster together. Shared semes, not interpretive labels, are the algorithm\'s output.'),
    body('The strong tier (t ≥ 10) captures the most lexically overdetermined isotopies — clusters where multiple lemmas share several semes directly. These include the legal/consensual field (agree, consent: assent, concur, yield), the execution field (execute, gallows, hang: capital, punish, death), the corporeal/spiritual field (body, flesh, ghost: spirit, soul), and physical rupture (break, tear: separate, rend, wound). The medium tier (t ≥ 8) adds clusters held together by fewer or weaker shared semes: eerie, ghastly, hideous share frighten and dreadful; free and prison share liberty and confinement. The weak tier (t ≥ 5) captures the most oblique connections: ghost, demon, eerie share only supernatural and spirit.'),
    body('The absence of strong supernatural clustering is itself a finding: Potocki does not hammer the reader with redundant ghost-vocabulary. He achieves the supernatural effect through the structural position of rare terms, not through lexical accumulation. The isotopy detector quantifies this restraint.'),

    // ── §8 THREE-RESOURCE RESULTS ──────────────────────────────────────────────
    h1('§8  Results: three modern resources'),
    body('Running the pipeline with Wiktionary, WordNet 3.1, and Merriam-Webster yields a weighted similarity graph over all 81 lemma pairs. Before examining which isotopies each resource supports, we look at the global structure of the edge score distribution.'),

    ...imgPara('fig8_score_dist.png', 6.5, 2.8/7,
        'Figure 13. Raw edge scores ranked from strongest to weakest. The distribution is not flat — there are natural gaps that justify three distinct threshold levels (strong t≥10, medium t≥8, weak t≥5).'),
    body('The distribution confirms the multi-scale structure argued in §6. The strongest edge (story–tale, score 60.3) reflects lexical overdetermination: three dictionaries all say account, narrative, events, facts, incidents for both lemmas. The weakest genuine isotopy edges (ghost–demon, score 6.0) reflect oblique semantic kinship — shared through spirit alone. A single normalized threshold cannot respect both scales.'),
    callout('KEY', 'Multi-scale isotopy structure is a finding, not a problem. The narrative isotopy is lexically overdetermined in this passage; the supernatural isotopy is evoked more obliquely. Forcing a single threshold would erase this difference.'),
    new Paragraph({ spacing: { before: 120 }, children: [new TextRun('')] }),

    body('The figure below shows which of the ten representative isotopy pairs are detected by each of the three resources.'),
    ...imgPara('fig11a_three_resources.png', 5.5, 4.2/5.5, 'Figure 14. Isotopy detection across three modern lexical resources. Robust isotopies appear in multiple resources; resource-dependent findings are marked weak or absent.'),
    body('Story–tale and eerie–strange are robust across all three resources — definitionally dense pairs that any dictionary will connect. Ghost–demon is absent in WordNet (glosses too terse) but present in both Wiktionary and Merriam-Webster.'),
    body('Gyration–swing is the most resource-dependent finding: Wiktionary gives rich motion vocabulary while Merriam-Webster\'s gyration entry is circular ("an act of gyrating") — a tautological definition rejected by the pipeline gate. The pair clusters only from the Wiktionary contribution.'),
    body('Agree–consent and execute–hang are absent from both Wiktionary and WordNet but strongly present in Merriam-Webster. These are the legally and institutionally dense pairs — Merriam-Webster\'s editorial precision recovers what the other two resources miss.'),

    // ── §9 WEBSTER 1828 ────────────────────────────────────────────────────────
    h1('§9  A contemporary dictionary: Webster 1828'),
    body('The three modern resources share a structural property: they rank senses by 21st-century corpus frequency. For a passage from 1804 whose vocabulary centres on execution, the supernatural, and Gothic horror, this produces the wrong primary sense in several critical cases. The execution sense of hang is ranked below the intransitive motion sense. The theological sense of body — the body as distinguished from the soul — is ranked below the anatomical sense. The living/dead opposition in living is buried below the sense of "having a livelihood."'),
    body('Webster\'s American Dictionary of the English Language (1828) is contemporaneous with Potocki\'s novel (first published 1804–1810). It encodes the theological, Gothic, and legal senses as primary because that was their actual frequency in the Anglophone encyclopedic register of the period. Adding W1828 to the pipeline is therefore a philological decision: it operationalises the claim that the Model Reader of the 1804 text would have activated these senses as primary.'),
    body('W1828 is not ranked or selected — it is appended unconditionally after the tautology gate. This is deliberate: the Lesk selection procedure is designed to correct for frequency bias in modern resources. W1828 has no frequency bias to correct. Applying Lesk to W1828 would systematically de-prioritise the theological and supernatural senses that are W1828\'s entire contribution, replacing them with generic overlap with modern vocabulary.'),
    callout('KEY', 'W1828 is appended unconditionally because it encodes the right senses as primary by design. Lesk corrects for frequency bias; W1828 has none. The two procedures serve different purposes and should not be conflated.'),
    new Paragraph({ spacing: { before: 120 }, children: [new TextRun('')] }),

    // ── §10 FOUR-RESOURCE COMPARISON ───────────────────────────────────────────
    h1('§10  Four-resource comparison'),
    body('Adding W1828 to the three modern resources changes the isotopy structure substantially. The figure below shows the full four-resource comparison. The dashed line marks W1828 as a categorically different resource.'),
    ...imgPara('fig11b_four_resources.png', 6.5, 4.2/7.0, 'Figure 15. Isotopy detection across all four resources. The dashed line separates the three modern resources from Webster 1828. W1828 is uniformly present (✓) across all pairs.'),
    body('The W1828 column is uniformly ✓. This is not trivial. It reflects the fact that 1828 primary senses directly encode the semantic fields the passage activates: body/spirit, living/dead, execution/gallows. The most consequential recoveries are corpse–living (the living/dead opposition is central in W1828, incidental in modern MW) and execute–hang (the execution sense is primary in W1828; modern MW foregrounds intransitive motion).'),
    body('Gyration–swing, absent from MW due to the circular entry, is fully recovered by W1828, which gives "a circular or spiral motion; the act of rotating or whirling around a fixed axis" as primary.'),

    h2('What happens if we apply Lesk to W1828?'),
    body('The question is empirically testable. Applying Lesk top-2 selection to W1828 entries (splitting each entry into sentences and ranking by passage-context overlap) produces a measurably worse result:'),
    ...[
      '– story–tale drops from 58.92 to 44.92',
      '– gallows–hang drops from 33.45 to 21.40',
      '– body–flesh–ghost dissolves as a STRONG cluster',
      '– corpse–ghost–vampire dissolves as a STRONG cluster',
      '– execute–gallows–hang dissolves as a STRONG cluster',
      '– hideous–horrified–revolting dissolves as a STRONG cluster',
      '– STRONG clusters: 30 → 25;  isolates: 24 → 37',
    ].map(t => new Paragraph({ spacing:{before:60,after:60}, indent:{left:360},
      children:[new TextRun({text:t, size:22, font:FONT, color:BLACK})]})),
    body('The degradation is systematic: Lesk selects senses that overlap with the passage-derived context, which is dominated by common verbs and motion vocabulary. It de-prioritises exactly the theological and supernatural senses that W1828 contributes. The unconditional append is correct.'),
    callout('KEY', 'The choice between Lesk selection and unconditional append is not arbitrary — it depends on what problem the resource is solving. Modern resources need Lesk because their sense ordering is wrong for 1804. W1828 does not need it because its sense ordering is already right.'),
    new Paragraph({ spacing: { before: 120 }, children: [new TextRun('')] }),

    // ── §11 READING THE RESULTS ────────────────────────────────────────────────
    h1('§11  Reading the results'),
    body('The isotopy clusters are not the end of the analysis — they are structured input for interpretive work. Each cluster raises questions:'),
    bullet('Why does agree–consent cluster at strong level? What does it mean that legal/social accord is as lexically dense as narrative in this passage? (Answer: the passage turns on consent to enter the inn, given "with the consent of heaven" — the legal isotopy is structurally central.)'),
    bullet('Why does gyration–swing cluster at medium level? (Answer: the brothers Zoto are hanging on the gallows. Their rotary motion is a physical fact of the scene, and the pipeline detects it as a distinct isotopy.)'),
    bullet('Why are ghost, demon, and vampire isolated or weakly clustered? (Answer: Potocki uses these terms precisely but sparingly — one occurrence each. The isotopy is evoked through their structural position, not through lexical redundancy.)'),
    body('The pipeline operationalizes the detection of isotopy. The interpretation of what those isotopies mean — their narrative function, their ideological charge, their relation to genre — remains the work of the literary scholar. Computational detection serves analysis; it does not replace it.'),

    // ── §12 QUICK REFERENCE ────────────────────────────────────────────────────
    h1('§12  Quick reference'),

    h2('Glossary'),
    ...[
      ['Isotopy', 'A set of lexemes sharing repeated semantic features (semes). Greimas (1966).'],
      ['Seme', 'A semantic feature shared by multiple lexemes in a text. Operationalized here as: a definition word passing FRAME filter, with IDF above cutoff, shared by ≥ 2 lemma definitions.'],
      ['FRAME set', 'A documented stop list of words excluded from seme status, organized into three categories: definitional frame vocabulary, domain junk, and corpus-lemma semes. See Appendix C.'],
      ['IDF', 'Inverse Document Frequency. Weights semes by rarity across the 81-lemma set. Rare semes carry stronger isotopy evidence.'],
      ['L2 expansion', 'Radius-2 expansion of a lemma\'s definition profile via intermediate words, at half weight. Corpus lemmas are excluded as intermediates to prevent circular evidence.'],
      ['Complete-linkage', 'Clustering method requiring direct connection between every pair within a cluster. Motivated by Greimas\'s redundancy criterion.'],
      ['Absolute threshold', 'Edge score cutoff in raw IDF units. Preferred over normalized threshold because it preserves multi-scale structure.'],
    ].flatMap(([term, def]) => [
      new Paragraph({ spacing:{before:100,after:20},
        children:[new TextRun({text:term, bold:true, size:22, font:FONT, color:BLACK})]}),
      new Paragraph({ spacing:{before:0,after:100}, indent:{left:360},
        children:[new TextRun({text:def, size:22, font:FONT, color:DARK})]}),
    ]),

    h2('Pipeline parameters (Potocki Day 1)'),
    mono('N = 81 lemmas'),
    mono('Resources: Wiktionary + WordNet 3.1 + Merriam-Webster (merged) + Webster 1828'),
    mono('FRAME: ~170 stop words (three-category taxonomy; see Appendix C)'),
    mono('IDF cutoff: df(w) <= 0.45 * N  (words in >45% of definitions discarded)'),
    mono('L2 expansion: weight 0.5, corpus-lemma intermediates excluded'),
    mono('Clustering: complete-linkage'),
    mono('Thresholds: strong=10, medium=8, weak=5  (absolute IDF units)'),

    h2('Files'),
    bullet('potocki_definitions.json — Wiktionary definitions (81 lemmas)'),
    bullet('potocki_definitions_wn.json — WordNet 3.1 definitions'),
    bullet('potocki_definitions_mw.json — Merriam-Webster definitions'),
    bullet('fetch_mw.ipynb — API fetch notebook'),
    bullet('fetch_wordnet.ipynb — WordNet offline fetch notebook'),
    bullet('pipeline_real.py — Wiktionary pipeline with all fixes'),

  ]
},

// ── APPENDIX A — L1 seme profiles ─────────────────────────────────────────
{
  properties: {},
  children: (() => {
    const COLS=3, IMG_W=158, IMG_H=215;
    function imgCell(lemma) {
      const p = path.join(AGRAPHS, `${lemma}.png`);
      if (!fs.existsSync(p)) return new TableCell({children:[new Paragraph({children:[]})],borders:noBorder()});
      const buf = fs.readFileSync(p);
      return new TableCell({
        width:{size:Math.round(100/COLS),type:WidthType.PERCENTAGE}, borders:noBorder(),
        children:[new Paragraph({alignment:AlignmentType.CENTER, spacing:{before:30,after:30},
          children:[new ImageRun({data:buf,transformation:{width:IMG_W,height:IMG_H}})]})],
      });
    }
    function emptyCell() { return new TableCell({
      width:{size:Math.round(100/COLS),type:WidthType.PERCENTAGE}, borders:noBorder(),
      children:[new Paragraph({children:[]})]}); }
    const tableRows=[];
    for(let i=0;i<LEMMAS.length;i+=COLS){
      const chunk=LEMMAS.slice(i,i+COLS);
      while(chunk.length<COLS) chunk.push(null);
      tableRows.push(new TableRow({children:chunk.map(l=>l?imgCell(l):emptyCell())}));
    }
    return [
      h1('Appendix A — L1 seme profiles (Webster 1828)'),
      new Paragraph({spacing:{after:180},children:[new TextRun({
        text:'Each graph shows the direct seme ring (L1) for one corpus lemma, derived from the Webster 1828 definition. Nodes are the semes produced after FRAME filtering and lemmatization; edge weights are IDF scores (log N/df, cutoff df ≤ 0.45 × 81 = 36). L2 expansion (second ring, dashed edges) requires the full four-resource pipeline; run run_pipeline() in isotopy.py to obtain it. Lemmas in alphabetical order.',
        size:20, font:FONT, color:'555555',
      })]},),
      new Table({width:{size:100,type:WidthType.PERCENTAGE},rows:tableRows}),
    ];
  })(),
},

// ── APPENDIX B — Definition files ─────────────────────────────────────────────
{
  properties: {},
  children: [
    h1('Appendix B — Definition files: format and fetch'),
    body('The pipeline reads definitions from four JSON files, one per lexical resource. These are produced once by the fetch scripts and stored in the potocki/ folder. They are not regenerated at pipeline run time.'),
    h2('File names'),
    mono('potocki_definitions.json        — Wiktionary (81 corpus lemmas)'),
    mono('potocki_definitions_wn.json     — WordNet 3.1 (81 corpus lemmas)'),
    mono('potocki_definitions_mw.json     — Merriam-Webster (81 corpus lemmas)'),
    mono('potocki_l1_vocabulary.json      — computed L1 seme word list'),
    mono('potocki_l1_wk.json              — Wiktionary (~638 L1 words)'),
    mono('potocki_l1_wn.json              — WordNet (~638 L1 words)'),
    mono('potocki_l1_mw.json              — Merriam-Webster (~638 L1 words)'),
    mono('potocki_l1_w1828.json           — Webster 1828 (~638 L1 words)'),
    h2('JSON structure'),
    body('All definition files share the same structure:'),
    new Paragraph({spacing:{before:120,after:120},indent:{left:360},
      children:[new TextRun({size:18,font:'Courier New',color:BLACK,
        text:'{\n  "lemma_map": { "ghost": ["ghosts"], ... },\n  "definitions": {\n    "ghost": {\n      "raw_definitions": ["the soul of a dead person ...", ...],\n      "definition_words": ["soul", "dead", "spirit", ...]\n    }, ...\n  }\n}'})]}),
    body('raw_definitions contains the original definition strings (up to 3 per resource). definition_words is a pre-tokenised flat list used only for diagnostics; the pipeline re-tokenises raw_definitions at run time with the full FRAME filter applied.'),
    h2('Fetch scripts'),
    body('Two scripts handle the one-time fetch. Run them locally; upload the resulting JSON files to potocki/.'),
    bullet('step1_extract_l1_vocab.py — reads Phase-1 files, computes L1 vocabulary, writes potocki_l1_vocabulary.json'),
    bullet('step2_fetch_l1_resources.py — fetches L1 definitions from all four resources'),
    body('Phase-1 files (corpus lemmas) are fetched by the functions fetch_wiktionary(), fetch_wordnet(), fetch_mw() in isotopy.py. Run once per corpus; results are stable.'),
    h2('Webster 1828'),
    body('W1828 definitions are fetched from Project Gutenberg #673 (pg673.txt). Download the file manually and run:'),
    mono('python step2_fetch_l1_resources.py --w1828 --w1828-file pg673.txt'),
    body('Alternatively, pass --w1828-scrape to fetch entry by entry from webstersdictionary1828.com (~5 min). Coverage: ~400–500 of the 638 L1 words; words coined after 1828 will be absent, which is expected.'),
  ],
},

// ── APPENDIX C — FRAME Category 1 stop list ─────────────────────────────────
{
  properties: {},
  children: [
    h1('Appendix C — FRAME Category 1: definitional frame vocabulary'),
    body('Category 1 of the FRAME stop set contains words that appear in dictionary entries as structural scaffolding rather than as semantic content markers. They are part of the metalanguage of definitions — words that describe what logical category the definiendum belongs to, not what it means specifically.'),
    body('The list was assembled by inspection of the full definition corpus. It is organized into three sub-groups with distinct rationales. Automated removal via a frequency-list criterion was tested (BNC top-2000, DF_MIN=2) but found insufficient: all 89 candidate words survived the IDF cutoff at the standard threshold, and the frequency criterion over-excluded legitimate semes. The manual list is therefore the operative criterion, documented here for transparency and reproducibility.'),
    new Paragraph({ spacing:{before:120}, children:[new TextRun('')] }),
    ...CAT1_GROUPS.flatMap(group => [
      h2(group.label),
      body(group.desc),
      new Paragraph({
        spacing: {before:120, after:160},
        children: [new TextRun({
          text: group.words.sort().join('  ·  '),
          size: 20, font: 'Courier New', color: BLACK,
        })],
      }),
    ]),
    body('Total: 167 unique words. Words in Category 2 (domain junk, resource-specific artifacts) and Category 3 (corpus-lemma semes, added at run time) are documented separately in isotopy.py.'),
  ],
}

]});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('/home/claude/isotopy_dummies.docx', buf);
  console.log('Done:', buf.length, 'bytes');
});
