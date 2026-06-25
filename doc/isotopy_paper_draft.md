# Semantic Flatland: A Minimalistic Operational Pipeline for Isotopy Detection

**Andrea Valle**
Università di Torino

---

## 1. Introduction

The notion of isotopy, introduced by Greimas (1966) to describe the recurrence of semantic units across a textual portion, has remained one of the most productive concepts in European semiotics. Crucial in semiotic theory and its applications, it has been discussed by authors belonging to different paradigms, from Eco, who incorporated it into his narrative theory (Eco 1979), to Rastier, who placed it at the centre of his so-called interpretive semantics (Rastier 1987).

Yet a persistent gap separates the theoretical articulation of isotopy from any operational procedure for its detection. On one side we know what an isotopy is (or should be); on the other side we have no clear account of how to find one in a text, and from a text.

This paper proposes a computational pipeline for isotopy detection that takes that gap seriously. The approach is explicitly minimalistic along two axes:

1. *Theoretically*, it adheres to compositional semantics — meaning is modeled as a structured combination of semic units — but postulates no hierarchy among those units.
2. *Methodologically*, it introduces no purpose-built lexical resource and requires no annotated corpus or domain ontology. What it does provide is a clear formalization of isotopy as a graph-theoretic object, a reproducible detection procedure, and empirical results that are auditable and adjustable.

We argue that this double minimalism is not a theoretical impoverishment but a principled choice: the minimum structure needed to detect isotopy without presupposing the analytic categories the analysis is supposed to produce.

While mostly grounded in European semiotics, the paper is nevertheless situated at the intersection of several disciplines — lexical semantics, classic knowledge representation, and cognitive science — from which notions are borrowed selectively. The commitment to operationalizability over theoretical completeness is what makes that eclecticism principled rather than arbitrary.

We illustrate the pipeline on two passages from nineteenth-century prose fiction: the gallows scene from Jan Potocki's *The Manuscript Found in Saragossa* (written ca. 1804, Maclean translation, Penguin 2008) and the opening paragraph of Edgar Allan Poe's "The Fall of the House of Usher" (1839). The two passages are comparable in length and share a Gothic register, but differ substantially in semantic structure — a difference the pipeline makes visible and quantifiable.

---

## 2. Theoretical background


### 2.1 Isotopy: concept and history

Since *Sémantique structurale*, for Greimas (1966), isotopy is the property that makes a text readable as a coherent object: the redundancy of semic categories across the syntagmatic axis ensures that successive lexemes can be integrated into a unified semantic plane. The key distinction is between nuclear semes, which individuate a lexeme within a semantic field, and classemes, which are contextually assigned and ensure compatibility between adjacent lexemes. Isotopy is carried by classematic recurrence. In the *Dictionnaire* isotopy is defined as "the iterativity along a syntagmatic chain, of classemes ensuring the discourse-enunciate its homogeneity" (Greimas and Courtés 1979, s.v. *Isotopie*). Even if the *Dictionnaire* traces the origin of the name to chemistry and physics, this seems an a posteriori etymology (Rastier 1987, citing Greimas's personal communication). Rather, the underlying idea of a plane more aptly recalls an isoline — "a curve connecting points where the function has the same particular value" — resulting in a plane section, such as mean sea level. Also, the original 1966 formulation uses the informational term "redundancy," while the *Dictionnaire* proposes "iterativity." As Rastier (1987) notes, the latter term's focus is inherently procedural; he accordingly prefers "iteration" (an operation) to "iterativity" (an abstract feature). Rather than a result, isotopy is an ongoing process. Two features thus emerge: (1) isotopy defines a common plane, on the model of the semantic isoline; (2) isotopy is an ongoing construction of that plane by an iterative procedure. In short, isotopy is the construction of a plane by connecting points having the same semantic value.

[^transl]: All translations from French and Italian are by the author unless otherwise noted.

Following Greimas, the concept was subsequently extended and revised by several authors. Kerbrat-Orecchioni (1976) broadened it to cover not only semantic semes but other semiotic units — phonemes, rhythm, connotative values — redefining isotopy as a general principle of textual coherence. Eco (1980) underlined the procedural feature in isotopy by emphasizing the progressive, oriented directionality inherent to its construction: "isotopy refers almost always to constancy in going in a direction that a text exhibits when submitted to rules of interpretive coherence" (Eco 1980: 153). For a recent survey of the concept's history and its applications in literary analysis see Binelli (2025).

The most extensive treatment of isotopy is due to Rastier (1987, see also 1991), who elaborates the Greimasian foundation into a full taxonomy of semic components: inherent vs. afferent, generic vs. specific, micro- vs. macro-semantic. In his fine-grained organization Rastier proposes complex structures to account for semantic features. As an example, a "semic molecule" is a graph structure articulating relations among semes (1987: 193, 1991: 202). Here, semes, in turn, can be described internally in terms of subfeatures.[^molecule] The result is a finely articulated descriptive metalanguage.

[^molecule]: One could observe that at this point these subatomic elements could be even called "semions."


### 2.2 The operationalization gap and its structural causes

The great metalinguistic construction around the notion of isotopy leaves one question unanswered: how are semes identified? And consequently: how are they differentiated typologically? The solution invoked is recourse to the analyst's intuition. Rastier himself is disarmingly candid about this: "intuition may reflect an objective reality. Its well-known insufficiencies do not prevent it from being useful, even indispensable, to scientific activity" (1987, p. 108).[^r108] The metalanguage of interpretive semantics is therefore a theory for reporting the results of an analysis already performed, not a procedure for performing it. Its criteria are never operationalized. The point is confirmed from within the tradition itself: Pincemin (2012) states explicitly that interpretive semantics "is not a formal semantics in which meaning would be modelled as a computation."[^pincemin2]

[^r108]: "l'intuition peut refléter une réalité objective. Leurs insuffisances bien connues ne les empêchent pas d'être utiles, voire indispensables, à l'activité scientifique."
[^pincemin2]: "La sémantique interprétative n'est pas une sémantique formelle, dans laquelle le sens se modéliserait comme un calcul."

It should be noted that Rastier has also engaged with corpus analysis in a computational register, producing work in the textometric tradition (Rastier 2011). While this work is indeed technically grounded, it is at the same time categorically distinct from a computational operationalization of *Sémantique interprétative*. Textometry measures distributional patterns; it does not implement semic decomposition or isotopy detection. The relationship between Rastier's textometric practice and his theoretical framework remains, to our knowledge, unspecified. The two bodies of work coexist without an explicit bridge.

Closer to a genuine operationalization are the systems developed in the French NLP community during the 1990s: PASTEL (Tanguy) and ThemeEditor (Beust), along with at least one doctoral thesis proposing a formal computer model of *Sémantique interprétative* [**VERIFY**]. Tanguy's PASTEL is explicitly positioned as computer-aided interpretive semantics — a cooperative human-machine architecture in which the machine handles formal manipulation while the human analyst retains all interpretive decisions. Both PASTEL and ThemeEditor require purpose-built semantic resources — annotated lexicons in which semic categories have been pre-assigned — introducing a circularity: isotopy detection confirms what was decided when the resource was built.

To sum up, Rastier states three constraints at the basis of his approach: "we will avoid postulating deep semantic structures"[^r220a]; "interpretation [...] reduces for us to a rule-governed assignment of meaning, without any need to invoke a hermeneutic subject or a model reader"[^r220b]; and "the intentionality of the enunciating subject [...] reduces for us to an unverifiable conjecture"[^r220c] (1987, p. 220). While the third point is not in discussion, the first two are debatable. First, the whole metalinguistic description of interpretive semantics takes into account the lexical surface only as a starting point to reach a different plane: Rastier asks for trespassing the "signal" level of the lexicalized text. If so, we are pushed into a depth, a semantic one — yet we do not know how to reach it. Second, the rule-governed assignment is an unspecified algorithm, as we do not know the rules but by intuition.

[^r220a]: "nous éviterons de postuler des structures sémantiques profondes."
[^r220b]: "l'interprétation [...] se réduit pour nous à une assignation réglée du sens, sans qu'il soit besoin d'évoquer un herméneute, ou un lecteur modèle."
[^r220c]: "l'intentionnalité du sujet énonçant [...] se réduit alors pour nous à une conjecture invérifiable."

### 2.3 What is a seme? The labelling problem

While discussing Greimas, Eco already noted in 1975 that semic analysis results in the identification of a set of metalinguistic labels. What is the status of these labels? They properly identify semes and therefore have a distinct, explicitly metalinguistic status. Yet, as Eco (1975: 173) observes, this "does not dispel the impression that we are facing lexical facts that explain other lexical facts, nor the impression that we are not dealing with a small, finite set of semantic universals capable of explaining an extremely high number of expressions."[^eco75] For Rastier, this fact is not particularly problematic, since "the aim is to analyse sememes so as to differentiate them, not to analyse the denominations of semes."[^rastier38] But as Eco notes, the labelling problem is a technical formulation of a more general one: it is not only a matter of how to retrieve a seme and describe it, but, properly, of defining what a seme is. If, indeed, following Rastier, there is no traffic between lexematic labelling and the seme as a semantic unit, then the last link between the linguistic and the semantic dimension is severed. Taking up Eco's point, Paolucci (2010) asks: what are these labels if not interpretants of the same lexeme — other lexical signs that illuminate it under a certain aspect?

[^eco75]: "non elude l'impressione di trovarci di fronte a fatti lessicali che spiegano altri fatti lessicali, né quella di non avere a che fare con un insieme ridotto e finito di universali semantici capaci di spiegare una quantità altissima di espressioni" (Eco 1975: 173).
[^rastier38]: "l'objectif visé est d'analyser les sémèmes de façon à pouvoir les différencier, et non d'analyser les dénominations des sèmes" (Rastier 1987: 38).

Paolucci proposes a Peircean alternative: treat semes for what they actually are — interpretants, other lexemes of the object language that interpret the first lexeme. "Semes for what they actually are, namely interpretants, that is, other lexemes of the object language that interpret the first lexemes by conferring upon them an effect of depth."[^paol2] On this account, a seme is not a deep unit underlying the surface lexeme; it is a non-lexicalized unit of value that presides over lexicalization — "an element not immediately present, but made present by the text precisely insofar as it is not immediately present."[^paol3] The Peircean alternative to Greimas's depth illusion is what Paolucci calls, borrowing from Abbott's mathematical fable, *flatlandia* — the flat surface that interpretation fills rather than transcends: "its rhizomatic process never transcends the flat surface it fills: flatland."[^paol4]

[^paol2]: "I semi per quello che sono in realtà, e cioè interpretanti, e cioè altri lessemi della lingua oggetto che interpretano i primi lessemi conferendogli un effetto di profondità."
[^paol3]: "un elemento non immediatamente presente, ma presentificato dal testo proprio in quanto non immediatamente presente."
[^paol4]: "il suo processo rizomatico non trascende mai la superficie piatta che riempie: flatlandia."

While keeping the reference to semantics, in what follows we similarly opt for a flat approach to its description. We present a pipeline that aims at taking the Peircean move literally: semes are nothing else than definition words — other lexemes from the object language that interpret the target lexeme. There is no depth. There is only the weighted surface of lexicographic co-occurrence, organized into a structured plane.

We propose to operationalize this stance directly. Definition words are semes-as-interpretants — mute strings, carrying no interpretive presupposition, weighted by their rarity in the corpus. Following Paolucci's Peircean reframing, the seme is not a primitive feature of a formal system but an interpretant — another lexeme of the object language that illuminates the first. This position has a direct operational consequence: if semes are other lexemes, they can be found in dictionaries. The dictionary is not a secondary approximation of semantic structure; it is one of the primary sites where the community's interpretive acts are deposited and made public. A dictionary is a finite slice of an encyclopedia; more dictionaries capture different slices. Following a radically flat paradigm, the semantic description we propose results in mere collections of units.

This is consistent with Hurford's (2007) observation that lexical meaning can be modeled as a list of semantic features without presupposing a hierarchical organization among them. The list is sufficient for many semantic phenomena thought to require richer structure. The flatland stance: what is needed for isotopy detection is a weighted set of interpretants per lexeme, drawn from culturally deposited lexicographic descriptions, scored against the specific textual context. Nothing more is assumed about their internal structure. The operationalization follows directly. A seme is a virtual lexeme appearing in a sense. The seme set of a lexeme is the union of semes across its senses in the selected resources. The number of resources consulted is variable — a parameter, not a constant — a degree of freedom that can be used theoretically, as we show in §4.1.

Paolucci's definition of isotopy follows from his flatland assumption: "an isotopy is a dissemination in the same place (iso-topos), a dissemination that leads to the same location, a semantic path in which semes seem to go in that same direction."[^paol5] Isotopy is a dissemination that throws semes in the same direction onto the same encyclopedic plane — far more than Rastier's iteration, it is a vector on the flatland. The direction is what the analyst reads in the cluster output; the flatland is what the pipeline produces.

[^paol5]: "un'isotopia è una disseminazione nello stesso luogo (iso-topos), una disseminazione che conduce nello stesso posto, un percorso semantico in cui i semi sembrano andare in quella stessa direzione."

This reformulation of isotopy is consistent with the one that appears in Eco's *The Role of the Reader* (1979). Where Greimas treats isotopy as a property of the text-as-completed-object, Eco reconceives it as a dynamic process of reading: isotopy is not given but constructed, updated at each step as new lexemes confirm or force revision of the reader's running semic hypotheses. The reader maintains a provisional interpretation that is perpetually open to correction.

The analyst names the clusterized isotopy after reading its contents: an explicit act of interpretation performed on the flat surface, in full view, rather than concealed inside a rhetoric of semic depth. We borrow the definition from Rastier (syntagmatic iteration) while implementing the epistemology from Eco/Paolucci (semes as interpretants on a flat encyclopedic plane). Moreover, the running definition of isotopy maps directly onto a computational parameter. The memory window — the number of lexemes held simultaneously in scope for semic comparison — is the formal analogue of the reader's attention span. A wider window models a reader who integrates distant textual elements into a single isotopic plane; a narrower window models local, incremental construction. We return to this in §3.2.


### 2.4 Positioning among adjacent disciplines

The pipeline draws on, without committing to, several adjacent research traditions.

The dominant computational approach to lexical meaning is distributional semantics, whose theoretical and methodological foundations are comprehensively surveyed in Lenci & Sahlgren (2023). Building on Harris's distributional hypothesis — that words occurring in similar contexts have similar meanings — distributional models derive semantic representations from co-occurrence statistics in large corpora. Distributional semantics is, in a precise sense, also a semantic flatland: it postulates no hierarchical structure among semantic features, no nuclear/classeme distinction, no prior taxonomy. In this respect the pipeline and distributional semantics share the same basic epistemological stance. The difference is not flatland versus hierarchy; it is *which* flatland, grounded in *which* theory of what constitutes semantic evidence. Distributional semantics encodes *meaning as where words go*; the pipeline encodes *meaning as what a culture has found worth recording* — the seme as interpretant deposited in a dictionary. For literary text analysis of period texts, the second kind of evidence is more appropriate: it is closer to the encyclopedic competence the text presupposes. There is also a transparency argument: a word embedding is not auditable, while the pipeline's similarity is fully explainable from specific dictionary entries with specific IDF weights.

In lexical semantics, Mel'čuk and Polguère's Meaning-Text Theory (1987, 2007) offers the most rigorous existing formal metalanguage for lexical description. The tradeoff against the pipeline is coverage and portability versus analytic precision. In knowledge representation, the classic semantic network tradition (Quillian 1968; Brachman & Levesque 1985) and WordNet (Miller 1995) provide formal ancestors for the bipartite seme graph; the key difference is the pipeline's non-hierarchical structure. In cognitive science, IDF weighting has a family resemblance to salience-based accounts of categorization (Rosch 1975; Fillmore 1982; Gärdenfors 2000).


---

## 3. The pipeline

### 3.1 Architecture

The pipeline operates on a single base unit: the **lexeme**, defined as a lemmatized content word. Lexemes appear in two roles: **source lexemes**, extracted directly from the source text, and **semes** — virtual lexemes activated by source lexemes through their definition senses. A **sense** is a single gloss text associated with one reading of a lexeme in a dictionary entry; a **definition** is the full collection of senses for that entry. Semes are lemmatized by the same procedure as source lexemes and are absent from the source text — they constitute the intermediate vocabulary through which source lexemes are compared.

A seme is operationalized as a virtual lexeme: a word appearing in a sense definition — a deliberate simplification that trades analytic precision for transparency and reproducibility. This is the Paolucci/flatland move applied operationally: semes are nothing other than other lexemes of the object language that interpret the source lexeme, with no recourse to a separate metalinguistic level. The operationalization restricts the analysis to lexicalized cultural units — concepts for which a linguistic community has found it necessary to assign a word, and whose semantic content is therefore publicly recorded in dictionaries.[^modalities] This is also why the pipeline stops at a single hop: the seme set of a source lexeme is exactly the words found in its own senses, nothing more.[^l2exp]

The pipeline takes as input a source text and a set of lexical resources, and produces as output a ranked list of isotopy clusters. The five stages are shown in Figure P, in a bustrophedic layout (as indicated by arrows). Color encodes stage membership; diamond-marked nodes are filter or gate operations.

[**Figure P**: Pipeline diagram. Five stages from source text (top left) to isotopy clusters (bottom left), bustrophedic layout. Stage inputs/outputs: source text → source lexeme set → seme list per lexeme → weighted bipartite graph → scored lexeme–lexeme edges → isotopy clusters. ◆ = filter/gate node (redirect filter, length filter, IDF cutoff, threshold gates).]

The pipeline uses two hand-curated stoplists — exclusion lists in the NLP tradition — defined here as they are referenced throughout the processing stages:

- **FRAME** — a stop set of generic lexicographic scaffolding: closed-class function words, semantically bleached verbs, and generic frame nouns that describe the logical category of the definiendum rather than its semantic content (*person*, *thing*, *state*, *make*, *take*). These words activate the frame of lexicographic discourse, not the frame of the definiendum. The FRAME list is compiled by inspecting the most frequent definition words across resources and flagging those that recur as generic scaffolding, with entries added incrementally as new corpora exposed gaps (e.g. *thinke*, an orthographic variant found in older digitized dictionaries).
- **JUNK** — resource-specific structural artifacts: e.g. ISO 639 language codes from Wiktionary, part-of-speech labels, markup fragments, OCR concatenation artifacts from digitized historical sources (e.g. `togaze`, `rackingtorture`), and similar format noise carrying no lexical meaning. JUNK entries are curated per resource.

Both are completely discarded — excluded from the Lesk context and from the final seme profile. These are the only non-automatic steps in the current pipeline, requiring human curation — though both are in principle partially automatizable (FRAME via corpus-frequency thresholding, JUNK via pattern matching on known resource metadata formats). Everything else runs without human intervention once these lists are fixed.


**Stage 1 — Lexeme extraction.** Stage 1 takes the source text as input and produces the set of source lexemes that will drive all subsequent processing. The source text is first tokenized into surface forms, then each token is assigned a part-of-speech tag. Tokens tagged as nouns, verbs, adjectives, or adverbs are retained; function words and all other categories are discarded. The surviving tokens are then lemmatized — reduced to their canonical root by morphematic extraction — yielding the source lexeme set. The Day 1 Potocki passage yields 81 lexemes; the Poe opening paragraph yields 99. These are standard NLP operations, implemented here via `simplemma` (Barbaresi 2021) for lemmatization and regex-based tokenization, deliberately chosen over heavier dependency parsers or neural taggers to keep the pipeline lightweight, interpretable, and free of black-box components.

Lemmatization already involves a step beyond pure lexical appearance, since it abstracts away from inflectional variation (*hanging*, *hanged*, *hangs* → *hang*). Yet this abstraction remains firmly anchored to the lexical surface: it operates at the morpheme level, identifying the invariant root shared by a set of inflected forms, without making any claim about meaning. Lemmatization is, in this sense, a form of morphematic extraction rather than semantic interpretation — it stays on the same flat plane as the rest of the pipeline, one level of abstraction up from the token but no closer to any postulated depth. One deliberate limitation: adverbs are not reduced to their adjectival base (*slowly* is not mapped to *slow*). This is both a practical choice — adverb-to-adjective mapping is not reliably handled by standard lemmatizers without POS-aware context — and a principled one: adverbs appearing in dictionary definitions are part of the lexicographic record and are retained as such, contributing at whatever IDF weight they naturally carry. In practice their contribution is minimal, since definition adverbs tend to be high-frequency and are therefore suppressed by the IDF filter at Stage 3.

**Stage 2 — Definition lookup and sense selection.** Stage 2 takes the source lexeme set and, for each lexeme, retrieves and ranks senses from the selected resources, producing a seme list per lexeme. For each lexeme, definitions are fetched from the selected resources. The senses of each entry are processed through four steps.

1. **Redirect filter** — senses that are redirect entries or too short are discarded. Redirect entries include grammatical form glosses ("plural of X", "past tense of Y", "present participle of Z"), ISO 639 language code entries ("ISO 639-3 code for Sentani"), and alternative spelling entries ("Commonwealth English for skeptical"). Senses made up of two words or fewer are also discarded as uninformative. These two checks — redirect detection and length filtering — are the only hard pre-filters in the pipeline.[^redirect] Lesk scoring handles genuinely circular senses naturally — they contain almost no content words and score near zero on source text overlap.

2. **Lesk scoring** — sense selection depends on a source-derived context *C* that must be built before scoring can happen. This requires two passes.

   *Prior pass*: for each lexeme, the first three senses per resource are fetched and redirect-filtered. The sense texts are tokenized, lemmatized, and cleaned using the FRAME and JUNK filters. The resulting seme sets are used only to compute document frequency: for each seme *w*, df(*w*) is the number of lexemes whose first-pass seme set contains *w*. The context *C* is then the union of the full Stage 1 lexeme set and the rare semes from this pass — those with df ≤ 10. These rare semes are semantically distinctive precisely because they are low-frequency across the source text's definitional vocabulary.

   *Main pass*: with *C* established, surviving senses (from step 1) are scored. The Lesk score for a sense *s* is the overlap between its seme list *D(s)* and the context *C*:

   score(*s*) = |*D(s)* ∩ *C*|

   Source lexemes are included in *C* — a source lexeme appearing in a sense definition as a seme is precisely the kind of source-relevant overlap Lesk scoring is designed to exploit.

3. **Top-2 selection** — senses are ranked by Lesk score; ties are broken by resource order. The two highest-scoring senses per resource are retained.

4. **Merge and filter** — the seme lists of selected senses from all resources under consideration are concatenated into a single seme list per lexeme. FRAME and JUNK words are then discarded, along with all source lexemes (which remain in *C* for scoring but are excluded from the final seme set). The surviving tokens constitute the lexeme's seme set.

**Stage 3 — IDF weighting, profile construction, and bipartite graph.** Stage 2 yields, for each source lexeme, a flat list of semes drawn from its selected senses. Stage 3 transforms that list into a weighted profile by scoring each seme according to how discriminating it is across the source text as a whole. The core weighting mechanism is inverse document frequency (IDF), standard in information retrieval (Lenci and Sahlgren 2023, ch. 2). The intuition is simple: a seme that appears in the definitions of many lexemes is uninformative about any one of them — it is semantic background. A seme that appears in only a handful of definitions is highly informative: if two lexemes share it, that overlap is unlikely to be accidental.

Concretely, the IDF computation borrows the document/corpus metaphor from information retrieval: the source text's lexemes collectively form the corpus, and each lexeme's seme set plays the role of a document within it.

- **N** = total number of source lexemes in the source text
- **df(*w*)** = number of lexemes whose seme set contains seme *w*
- **IDF(*w*)** = log(*N* / df(*w*))

A seme present in every lexeme's definition pool scores 0 (df = N); one found in only a single lexeme's pool scores log(*N*).[^idf_numbers] The measure is entirely source-internal: *N* and df(*w*) are both derived from the definitions fetched for this source text's lexemes, with no reference to any external corpus. The same seme will receive a different IDF score in a different source text — IDF here is a source-specific measure of seme rarity, not a universal one. Semes exceeding the df > 0.45 × *N* threshold (an empirically determined cutoff) are discarded entirely as semantic scaffolding; surviving semes contribute their IDF score to the lexeme's weighted **seme profile** — the full set of ⟨seme, IDF-weight⟩ pairs for that lexeme. It is the surviving, IDF-weighted semes (seme profile) that enter the similarity graph.

The bipartite graph is then constructed by collecting all semes across all lexeme profiles and linking each seme to the lexemes it belongs to via a weighted edge, whose weight is IDF(*w*) as accumulated in the lexeme's profile — encoding how discriminating that seme is for that lexeme across the source text's full definitional vocabulary. This graph is the output of Stage 3 and the input to Stage 4. The abstract structure is shown in Figure B; the full graphs for both passages are visualized in Figures X and Y; the seme profiles are discussed concretely for *hang* in §4.3.

[**Figure B**: Abstract bipartite graph of lexemes and semes. Black circles: source lexemes (*l*₁, *l*₂, *l*₃). Gray circles: semes (*s*₁–*s*₇); fill darkness records IDF weight (darker = rarer = more discriminating). Edge thickness records the IDF weight of the seme in that lexeme's profile; these weights are exploited in Stage 4. Semes *s*₁, *s*₂, *s*₃ are shared across two lexemes each and carry isotopy signal; *s*₄ is shared across all three lexemes (low IDF, functions as a classeme); *s*₅, *s*₆, *s*₇ are private to a single lexeme and contribute to its profile without generating cross-lexeme connections.]

**Stage 4 — Similarity scoring and graph construction.** Stage 4 takes the weighted seme profiles, computes a pairwise similarity score for every lexeme pair that shares at least one seme, and assembles those scores into a similarity graph. The score is obtained by projecting the bipartite graph onto the lexeme side. Where profile(*l*, *w*) denotes the IDF weight of seme *w* in lexeme *l*'s profile:

score(*l*₁, *l*₂) = Σ_*w* min(profile(*l*₁, *w*), profile(*l*₂, *w*))

That is: for each seme *w* shared by both lexemes, take the lower of the two IDF weights; then sum those values across all shared semes. The minimum operator takes the conservative estimate of shared evidence: a seme counts only as strongly as the weaker of the two lexemes supports it, preventing a strong weight in one profile from inflating a connection the other profile barely has. The sum rewards multiple shared semes. This operation can be read as a recast of Greimas's nuclear/classeme distinction as a gradient: high-IDF semes (rare, discriminating) function empirically as nuclear semes; low-IDF semes (broadly shared) function as classemes. Rather than classifying semes into discrete types, here we weight them continuously.

The similarity score is a continuous value, but isotopy detection requires a discrete decision: which lexeme pairs share enough semic evidence to count as isotopically connected? Thresholds convert the continuous score into that decision. While the score is continuous, we propose a three-level hierarchy — STRONG, MEDIUM, WEAK — forming a hierarchy that captures isotopic evidence at different degrees of lexical density. The specific threshold values are reported in §4.1, where the resource configuration that calibrates them is introduced. Absolute thresholds are preferred over normalized ones because isotopic density varies by semantic field: lexically overdetermined isotopies produce high scores, obliquely evoked ones produce low scores. A single normalized threshold would erase this empirically observable multi-scale structure. The thresholds serve as gates: pairs below the WEAK threshold contribute no evidence of isotopic connection and are excluded from the clustering stage.

**Stage 5 — Clustering.** Stage 5 takes the scored lexeme pairs and groups them into isotopy clusters by applying complete-linkage clustering at three threshold levels. Connected components above threshold are identified using complete-linkage: two lexemes may belong to the same cluster only if every pair within the cluster exceeds the threshold — that is, the cluster is a clique in the thresholded graph. This is the computational translation of Greimas's redundancy criterion. Complete-linkage enforces *semantic compactness*: every member of a cluster must share direct semic evidence with every other member. Single-linkage (union-find), by contrast, allows *semantic drift*: lexemes connected only by a transitive chain of above-threshold edges would merge into the same cluster even when the endpoints share no direct evidence. Semantic drift does not correspond to isotopy as recurrence — it corresponds to associative spread, which is a distinct and theoretically interesting phenomenon — closer to what isotopy theory calls semantic drift or thematic migration — but one that complete-linkage deliberately excludes in order to model recurrence specifically. A consequence of complete-linkage is that the cluster report is exhaustive: every detected pairwise isotopic connection is represented either as a standalone two-lexeme cluster or subsumed into a larger cluster whose membership implies it. A pair appears standalone only when no third lexeme connects to both members above the threshold.

[^idf_numbers]: For the two passages analysed here, N = 81 (Potocki Day 1) and N = 98 (Poe opening paragraph), giving a maximum single-lexeme IDF of log(81) ≈ 4.4 and log(98) ≈ 4.6 respectively.

[^redirect]: Without the redirect filter, ISO 639 terms such as `code`, `iso`, `language` — appearing in only a handful of definitions — score spuriously high on IDF and produce false clusters. Empirical testing showed that removing the filter creates a false MEDIUM-tier cluster {*old*, *say*, *see*, *set*} connected by ISO metadata, and false WEAK edges via `participle` and `present`.

[^modalities]: The operationalization restricts the analysis to lexicalized cultural units. Other semiotic modalities — perceptual, gestural, pictorial — also carry semic content and participate in isotopy construction (Eco 1984; Rastier 1987, ch. 3), but their operationalization requires different resources and different formalisms. They are outside the scope of this pipeline, not excluded in principle.

[^l2exp]: A natural extension would be a two-hop expansion: for each seme, look up its own senses in turn and add those words at a discounted weight (e.g. 0.5 × IDF). The weight decay would enforce locality — at depth *n*, weight = (0.5)^(*n*−1) — preventing the small-world structure of the definitional network (Steyvers & Tenenbaum 2005) from collapsing all distinctions at depth 3–4, where a large fraction of the lexicon becomes reachable from any starting lexeme and isotopy clusters dissolve into an undifferentiated mass. The two-hop level is the furthest locally informative expansion; a single hop is sufficient for the passages analysed here.

### 3.2 The memory window

The extent of the semantic flatland depends on a parameter we call the memory window: the number of lexemes in scope for a given analysis. A wider window admits more lexemes, the terrain expands, and new isotopy ridges may emerge connecting clusters that a narrower window would leave separate. A narrower window produces a smaller but denser patch.

In Eco's terms (§2.3), the memory window is the computational model of the reader's attention span during isotopy construction. A static analysis over a fixed passage is the limiting case: the window covers the entire passage simultaneously. A sequential analysis — processing lexemes in reading order, recomputing IDF incrementally — models the dynamic construction Eco describes, with the window size controlling how far back in the text semic confirmation can reach. In this sequential mode the window is typically a *moving* window: as new lemmas enter at the forward edge, earlier lexemes drop out at the trailing edge. Isotopy is then not a global property of the passage but a locally computed one, varying as the window slides forward through the text. The cognitive reality of such a window is well established: Just & Carpenter (1980) provide a foundational account of reading as incremental working-memory-constrained processing, and Daneman & Carpenter (1980) demonstrate empirically that individual differences in reading span — the number of items a reader can hold active simultaneously — directly predict comprehension performance (for a subsequent capacity theory see Just & Carpenter 1992). Both modes are available in the pipeline; the analyses presented here use the static mode, with sequential analysis reserved for future work.

Even a moving window, however, does not fully capture the dynamics of reading. Certain lexemes — or certain seme activations — have a persistence that a purely positional window cannot model. A word like *ghost* in the Potocki passage activates a semantic field that continues to condition subsequent interpretation even after it has formally left the window, because its salience at the moment of reading was particularly high. It functions as a semantic milestone: a prior high-salience item that leaves a trace not erased by the window's forward movement. This is related to what Eco calls the encyclopedia already activated at a given reading moment — the set of semantic fields that have been primed and remain available for confirmation or revision.

A window with salience-weighted persistence — where milestone lexemes decay more slowly than positionally ordinary ones — would capture this effect, but at the cost of introducing new parameters: what counts as a milestone, and by how much does its decay differ? These questions are tractable but beyond the current scope. We acknowledge the gap as a known boundary of its minimalism: the moving window addresses the sequential dimension of reading; the milestone problem addresses its mnemonic dimension. Both are real; only the first is currently modelled. The sequential mode has not yet been implemented; it remains a viable extension of the present pipeline, and its full discussion is deferred to future work.

---

---

## 4. Results


### 4.1 Lexical resources and the encyclopedia

The pipeline is resource-pluralist. No lexical resource is purpose-built for this analysis; each is purpose-selected on theoretical grounds. The distinction matters: purpose-built resources (annotated corpora, domain ontologies, dedicated lexicons) embed analytic decisions that are invisible to the user of the pipeline. Purpose-selected general-purpose resources (dictionaries, thesauri, wordnets) make their contents publicly available and independently verifiable. The seme set of a lexeme is the union of content words across all selected resources: the number of resources is variable, and increasing it expands the semantic flatland without altering its topology.[^nelson]

[^nelson]: Independent evidence that semantic similarity is locally structured — rather than spreading uniformly across the lexicon — comes from free association norms (Nelson, McEvoy & Schreiber 2004). Associative responses cluster tightly around stimulus words, with rapid decay at distance. Our IDF weighting produces the same locality by suppressing broadly shared semes: the seme graph is dense locally and sparse globally, consistent with the associative structure Nelson et al. document empirically. The free association norms are methodologically uncontrolled from the pipeline's perspective — they encode idiosyncratic associative processes rather than culturally deposited lexicographic descriptions — but they provide convergent evidence for the locality assumption underlying the IDF design.

For the analyses presented here, four resources are used: Wiktionary, WordNet 3.1, Merriam-Webster Collegiate, and Webster's 1828 American Dictionary. The first three are contemporary general-purpose resources. The fourth requires a separate argument.

The three modern resources share a structural property: they rank senses by 21st-century corpus frequency — a criterion that systematically deprioritises period-appropriate senses for texts written two centuries earlier. For a passage from 1804 whose vocabulary centres on execution, the supernatural, and Gothic horror, this produces the wrong primary sense in several critical cases: the execution sense of *hang* is ranked below the intransitive motion sense; the theological sense of *body* — the body as distinguished from the soul — is ranked below the anatomical sense. Lesk selection (Stage 2, §3.1) corrects for this bias by reranking senses against the passage's own lexical context: senses whose vocabulary resonates with the passage's actual lexemes score higher, regardless of which dictionary they come from or what that dictionary's default sense ordering happens to be.

Webster 1828 participates in this same Lesk-based selection. It receives no special treatment — no bypass of sense ranking. What it contributes is not a different procedure but different content: senses that encode the theological, Gothic, and legal registers as primary, because that was their actual frequency in the Anglophone encyclopedic register of the period. When the passage context contains lexemes like *gallows*, *execute*, *corpse*, *heaven*, and *vampire*, the period-appropriate senses in W1828 naturally win the Lesk competition on their own merits — they score higher on contextual overlap precisely because they fit the text better than the generic modern alternatives. The resource selection is a hermeneutic decision; the sense selection mechanism is uniform. W1828 is not protected from the selection criterion: it wins because it is the right resource for the job.

Using a digitized historical resource introduces a class of noise absent from modern lexical databases: OCR concatenation artifacts. The pipeline's W1828 source is a digitized transcription in which illustrative example sentences occasionally run on from the definition text without proper word boundaries, producing tokens such as `togaze` ("to gaze"), `rackingtorture` ("racking torture"), and `torturemay` ("torture may"). These are handled by a two-stage fix: first, a parser-level rule strips example sentences introduced by `; as,` before the definition text is stored; second, the handful of residual artifacts not caught by this rule are added to JUNK. This is a specific instance of the general situation documented in digital corpus linguistics (Lenci and Sahlgren 2023): digitized corpora carry noise from the digitization process itself, and pipelines operating on historical texts must make explicit decisions about how to handle it. The pipeline's approach — strip at parse time where possible, discard at token level otherwise — is conservative and fully documented; a researcher working from a cleaner W1828 digitization would obtain slightly different seme profiles for the affected lexemes.

The theoretical basis is Eco's notion of the encyclopedia as a synchronic-diachronic construct (Eco 1984): the encyclopedia is not a snapshot of meaning at a single moment but a stratified archive in which earlier semantic strata remain available for activation. Reading a whale as a big fish is not an error if you are operating within the pre-Linnaean encyclopedic block — it is the correct reading within that stratum. Linnaeus did not replace that stratum; he added a new one. A competent reader of a medieval bestiary activates the pre-Linnaean block; a competent reader of a modern zoology textbook activates the Linnaean one. The full pipeline runs over a stack of resources that are not contemporaneous — Wiktionary, WordNet, MW Collegiate, Webster 1828 — each encoding a different historical slice of the English lexicon's self-description. Selecting W1828 formalizes the hypothesis that a competent reader of Potocki activates the pre-modern encyclopedic stratum, in which *vampire* is primarily a supernatural demon and *gallows* is an execution apparatus whose defining feature is suspension.

A consequence of this framing is that pool-aggregation — merging all resource profiles into a single IDF-weighted seme set — can inadvertently suppress exactly the stratum the hermeneutic decision was designed to activate. The *vampire–ghost* pair illustrates the dilution effect: W1828 independently encodes *vampire* with supernatural semes, but in the merged four-resource profile those semes are overwhelmed by the zoological vocabulary (*bat*, *blood*, *linne*) that W1828 also legitimately encodes for *Vespertilio vampyrus*, suppressing the mythological connection entirely. The *gallows–hang* pair shows the opposite: robust even in the merged profile (STRONG, weight 13.99), because the execution register in W1828 is reinforced rather than diluted by the other resources. This is not a pipeline failure but a theoretically interesting phenomenon: pool-aggregation models the simultaneous activation of all encyclopedic strata at once, which Eco's own model does not require. An alternative design — max-aggregation, retaining the highest per-resource score for each pair — would model the reader as consulting multiple perspectives and keeping a connection if *any* perspective supports it. Max-aggregation is monotone (adding a resource can only increase or maintain pair scores) but sacrifices the IDF recalibration that makes pool-aggregation principled. The choice between them is a theoretical one about how the Model Reader's encyclopedic competence operates, and is left as an open design parameter for future work.

The choice between pool and max aggregation maps onto two distinct models of encyclopedic reading, both of which the comparison table in §4 makes visible simultaneously. **Pool aggregation** models the reader as a unified semantic subject whose encyclopedic competences are activated simultaneously and recalibrate each other: the IDF landscape shifts globally as resources are combined, and connections that existed in a single resource may be suppressed when that resource's distinctive vocabulary is diluted by the others. It is a synchronic operation — all strata collapsed onto a single semantic plane. **Max aggregation** models the reader as summoning each encyclopedic stratum independently and retaining a connection if any stratum supports it: the result is the union of per-resource testimonies, without forcing them into competition. It is a diachronic operation — each stratum consulted in its own terms, the reader switching between encyclopedic blocks without interference. The comparison table encodes both modes: the single-resource columns (WK, WN, MW, W1828) give max aggregation directly — the union of their detections is the max-aggregation result — while the combined columns (WK+WN+MW, WK+WN+MW+W1828) give pool aggregation. A reader can read the table in either mode.

For the resource configuration used in this paper — Wiktionary, WordNet 3.1, Merriam-Webster Collegiate, and Webster 1828 — the three threshold values are set at STRONG (*t* ≥ 10), MEDIUM (*t* ≥ 8), and WEAK (*t* ≥ 5) in raw IDF units. These values were determined empirically by inspecting the ranked-score distribution for both passages and identifying the natural gaps that separate lexically overdetermined isotopies from obliquely evoked ones; they would require recalibration for a substantially different resource array or corpus size.

The array of resources is open. A different analyst working on a different text could substitute or add resources on equally principled grounds. The pipeline architecture does not privilege any particular selection.

### 4.2 Edge score distribution and multi-scale structure

Before examining specific isotopies, we look at the global structure of the edge score distribution for both passages (Figure Z).

The distribution follows an approximate power law in both cases: log-log regression yields slope −0.551 (R² = 0.956) for Potocki and slope −0.534 (R² = 0.948) for Poe. The near-identical exponents across two different texts suggest this is a property of the pipeline architecture rather than of the specific passages — an emergent consequence of IDF weighting, which is itself logarithmic, applied to a heavy-tailed distribution of definitional co-occurrences. The max/median score ratio is 16× for Potocki and 14× for Poe, confirming the heavy tail.

This power-law structure provides independent justification for the multi-scale threshold design. A single linear threshold applied to a power-law distribution would be arbitrary — there is no principled location for it. Three thresholds (WEAK=5, MEDIUM=8, STRONG=10) respect the natural gaps visible in the ranked-score plot and carve the distribution into interpretively meaningful tiers. The strongest edges (story–tale: 53.84; day–year: 49.37) reflect lexical overdetermination — multiple dictionaries converging on the same definitional vocabulary. The weakest genuine isotopy edges (ghost–demon: 6.09; sink–think: 11.71 at STRONG boundary) reflect oblique semantic kinship through one or two shared high-IDF semes. A single threshold cannot respect both scales; the tiered design does.

The power-law finding is not incidental. Steyvers & Tenenbaum (2005) demonstrate that lexical networks — WordNet, Roget's Thesaurus, and free association norms — exhibit small-world properties including power-law degree distributions. The pipeline samples from these networks through definitional co-occurrence; the power-law edge score distribution is inherited from the scale-free structure of the underlying lexical resources. The near-identical exponents across two different texts (−0.551 and −0.555) confirm that this is a property of the resource architecture, not of the passages themselves.

[**Figure Z**: Edge score distribution for Potocki (left) and Poe (right). Top row: scores ranked from strongest to weakest; dashed lines mark the three tier thresholds (STRONG=10, MEDIUM=8, WEAK=5); shaded regions indicate tier membership. Bottom row: log-log plot of the same data with linear regression fit; slope and R² reported in legend. The near-linear log-log relationship confirms an approximate power-law distribution in both passages.]

The full bipartite similarity graph for both passages is shown in Figures X and Y. These figures visualize the complete semantic flatland before any thresholding: all lexeme–seme connections above the 25th percentile of IDF scores are shown, making sub-threshold structure visible alongside the isotopy clusters that emerge at higher thresholds.

The Potocki graph (Figure X, Panel A) shows a dense core of inter-connected lexeme nodes surrounded by peripheral isolate constellations — the classic topology of a passage organized around multiple competing isotopies. The Poe graph (Figure Y, Panel A) is more fragmented: fewer inter-lexeme bridge connections, more isolated local clusters, reflecting a passage organized around a single dominant isotopy (interiority) with the remaining vocabulary distributed around it without strong mutual connections.

The insets (Panel B) zoom into the clusters of theoretical interest. In the Potocki inset the semes *soul* and *spirit* appear as bridge nodes connecting two sub-clusters: a theological-atmospheric group (*ghost*, *demon*, *heaven*, *eerie*) and an execution-corporeal group (*gallows*, *hang*, *corpse*, *body*, *flesh*). These bridge semes are precisely the ones that W1828 encodes as primary and modern resources do not — the structural basis of the promotion effect discussed in §4.3. In the Poe inset two sub-clusters are visible: a core interiority group (*soul*, *spirit*, *life*, *sense*, *mind*) and a peripheral corporeal-vital group (*decay*, *heart*, *feeling*, *sensation*), connected by bridge semes encoding animate and vital functions. The bridge edges are the structural basis of the full-pipeline promotion of *heart–life* and *decay–sense* to STRONG discussed in §4.5.

[**Figure X**: Bipartite similarity graph, Potocki Day 1 passage. Black nodes: lexemes; gray nodes: semes, gray level proportional to IDF weight (darker = rarer). Edges above p25 IDF threshold; edge gray level proportional to weight. Layout: sfdp. 81 lexeme nodes, 1,406 seme nodes, 1,118 edges. Panel B: subgraph of lexemes *gallows*, *hang*, *corpse*, *ghost*, *body*, *break*, *flesh*, *demon*, *vampire*, *heaven*, *living*; seme labels shown for IDF above p75 within the subgraph.]

[**Figure Y**: Bipartite similarity graph, Poe opening paragraph. Same encoding as Figure X. 98 lexeme nodes, 1,817 seme nodes, 1,925 edges. Panel B: subgraph of lexemes *soul*, *spirit*, *heart*, *life*, *sense*, *decay*, *mind*, *feeling*, *sensation*; seme labels shown for IDF above p75 within the subgraph.]

The full cluster report for both passages across all resource configurations is given in the Appendix.

### 4.3 Potocki, *The Manuscript Found in Saragossa*, Day 1 — three modern resources

Running the pipeline with Wiktionary, WordNet 3.1, and Merriam-Webster yields the following isotopy clusters. Figure 14 shows detection results for ten representative pairs.

[**Figure 14: isotopy_potocki_comparison.html — three modern resources matrix**]

Story–tale and ghastly–hideous are robust across all three resources — definitionally dense pairs that any dictionary will connect. Ghost–demon is absent in WordNet (glosses too terse) but present in both Wiktionary and Merriam-Webster via *spirit* and *soul*.

Gyration–swing is the most resource-dependent finding: Wiktionary gives rich motion vocabulary while Merriam-Webster's gyration entry is circular ("an act of gyrating") — a definition containing almost no content words, which scores zero on Lesk overlap and falls outside the top-2 cut. The pair clusters only from the Wiktionary contribution.

Agree–consent is absent from Wiktionary and WordNet but strongly present in Merriam-Webster, which recovers the legal-consensual sense precisely. This is MW's systematic contribution: editorial precision in legal and institutional vocabulary.

The supernatural cluster — ghost, demon, vampire — is absent or weak across all three modern resources. This is not an error; it is a finding. The passage evokes the supernatural through the structural position of rare terms, not through lexical accumulation. But it also points to the limits of modern lexicography for a 1804 text: the theological and Gothic senses that Potocki presupposes in his reader are not the primary senses of these lexemes in any contemporary dictionary.

### 4.4 Potocki — adding Webster 1828

[**Figure 15: isotopy_potocki_comparison.html — all four resources matrix**]

Adding W1828 changes the isotopy structure substantially. The W1828 column is present across all representative pairs. The most consequential recoveries are:

**Body–ghost** (absent in WN and MW, WEAK in WK, STRONG in W1828): W1828 encodes the theological sense of *body* — the body as distinguished from the soul — as primary. Modern resources foreground the anatomical sense. W1828's entry connects both lexemes directly through *soul*, *spirit*, and *divine*, producing a STRONG edge that three modern resources combined cannot generate.

**Gallows–hang** (STRONG in W1828 alone; edge score 13.99 in full pipeline, above the STRONG threshold, but not surfacing as a standalone cluster due to complete-linkage: *gallows* is pulled into the force–mountain–vampire clique while *hang* clusters with *swing*): W1828 gives the execution sense of *hang* as primary — "to suspend by the neck until dead" — and this sense survives and dominates even in the merged profile. Modern resources rank the execution sense below the intransitive motion sense, so no individual modern resource detects the pair; but W1828's execution vocabulary is distinctive enough (high IDF for *suspend* and *neck*) that it pulls the merged profile decisively into the execution register.

**Ghost–vampire** remains WEAK even with W1828. Potocki uses these terms precisely but sparingly — one occurrence each. The isotopy is evoked through structural position, not through lexical redundancy. The pipeline correctly quantifies this restraint.

The fresh results confirm the W1828 contribution quantitatively: the full four-resource pipeline yields 35 STRONG clusters against 16 for the three modern resources combined. The *ghost–vampire* pair is notable: it remains sub-weak (weight 4.92, below the WEAK threshold of 5.0) even in the full pipeline. This reflects a genuine W1828 lexicographic fact — the 1828 entry for *vampire* encodes both a mythological sense and a zoological sense (Linné's *Vespertilio vampyrus*), and the zoological vocabulary dilutes the mythological seme overlap. This is correct lexicographic behavior, not a pipeline failure: W1828 is used as a general-purpose dictionary, not a purpose-built Gothic lexicon.

### 4.5 Poe, "The Fall of the House of Usher" — three modern resources

[**Figure: isotopy_poe_comparison.html — three modern resources matrix**]

The Poe passage presents a structurally different isotopy picture. Where the Potocki passage organizes around execution, the supernatural, and legal accord, the Poe passage organizes around interiority — the narrator's inner states as they register and process the scene. MW alone carries the inner-life cluster: life–soul, life–spirit, and soul–spirit all appear at WEAK in MW and are absent in both WK and WN. WK and WN are largely silent on Poe's vocabulary of consciousness.

Dreariness–dreary, the one pair that appears at STRONG in MW isolation, illustrates the point: Merriam-Webster's editorial precision recovers the emotional-atmospheric sense directly. WK treats the pair as morphologically related but semantically underspecified; WN's glosses are too terse to generate the seme overlap.

### 4.6 Poe — adding Webster 1828

[**Figure: isotopy_poe_comparison.html — all four resources matrix**]

W1828's contribution to Poe is real but semantically distinct from its Potocki contribution. Two pairs absent from all three modern resources become STRONG under W1828:

**Heart–life**: W1828 foregrounds the vital and animating sense of both lexemes — *heart* as the seat of life and feeling, *life* as the animating principle — through shared semes *vital*, *animate*, *seat*. Modern resources treat *heart* primarily as an anatomical organ and *life* as a biographical concept.

**Decay–sense**: W1828 gives *sense* a strong corporeal meaning — the bodily faculty of perception — and connects *decay* to organic deterioration in the same register. The connection is to the body as a sensing, deteriorating thing. Modern resources separate the psychological and physical senses of both lexemes, preventing the connection.

Unlike Potocki, where W1828 recovers a supernatural cluster invisible to modern dictionaries, for Poe W1828 deepens the interiority cluster by recovering the corporeal-vital senses of consciousness words. The hermeneutic decision to include W1828 carries different weight for different texts — it is not a universal enrichment but a resource whose contribution is passage-specific.

### 4.7 Reading the clusters

The isotopy clusters are not the end of the analysis — they are structured input for interpretive work. Three observations from the Potocki results illustrate the relationship between detection and interpretation.

First, the agree–consent cluster at STRONG: it is as lexically dense as the narrative isotopy. This is significant because the passage turns on consent — the brothers act "with the consent of heaven," Alphonse consents to approach the gallows, the theologian's argument concerns what one may legitimately believe. The legal-consensual isotopy is structurally central to the passage's logic, and the pipeline detects it at the appropriate strength.

Second, the gyration–swing cluster at MEDIUM: the brothers Zoto are hanging on the gallows. Their rotary motion is a physical fact of the scene. The pipeline detects it as a distinct isotopy — a perceptual-kinetic register that runs alongside the supernatural and execution isotopies. As argued in §3.1, this is a genuine detection at the lexical layer of a semantic content that is also present in other modalities.

Third, the near-isolation of *ghost*, *demon*, and *vampire* as separate terms across most configurations — *ghost–vampire* remains sub-weak even in the full pipeline: Potocki uses these terms precisely but sparingly — one occurrence each. The isotopy is evoked through structural position, not through lexical redundancy. The pipeline correctly identifies their singularity. It cannot explain it — that explanation requires the kind of literary analysis the pipeline serves, not replaces.

For Poe, the permanent isolation of *opium* across all configurations is the most striking result. *Opium* has no lexical neighbors in the passage and remains isolated at all tiers and in all resource configurations. It is semantically the most charged word in the paragraph — the pivot on which the narrator's self-description of his psychological state turns — yet it shares no semes with any other lexeme. The pipeline surfaces its singularity correctly. The isolation is the fingerprint of what the model cannot do: *opium*'s semantic weight in the passage is carried by afferent, contextually activated semes that no dictionary records as primary.

---

## 5. Discussion

### 5.1 What the flatland buys

Before enumerating what the pipeline provides, it is worth stating the theoretical commitment that underlies the resource-pluralist architecture. Most computational semantics — whether distributional, knowledge-based, or neural — implicitly assumes that there is a correct semantic representation that better data or better models would converge toward. The pipeline rejects this assumption. Its claim is that there are semantic formats, not a semantic format. Meaning is not a Platonic object waiting to be correctly encoded; it is a set of culturally sedimented usages, partially captured by each lexical resource, none of which is privileged. WordNet and Webster 1828 disagree about the primary sense of *body* not because one is wrong but because they encode different cultural moments. The disagreement is data, not error.

This is consistent with Peirce's unlimited semiosis: meaning is always in process, always deferred toward further interpretants, never arriving at a final representation. The encyclopedia — in Eco's sense — is the cultural accumulation of that process at a given moment. Multiple resources are multiple moments: a sampling of the semiotic process rather than a snapshot of a static semantic state. The variability of the resource array is therefore not a limitation to be apologized for but the feature that makes the pipeline genuinely semiotic rather than merely computational. It models meaning as cultural exploration rather than as approximation of a fixed target.

A consequence follows for the interpretation of results. When the full pipeline promotes nearly all pairs to STRONG, the right reading is not that the pipeline is too permissive but that the text is semantically dense when read through the full encyclopedic accumulation available to us. A thinner encyclopedia — fewer resources, narrower historical range — produces fewer detected isotopies, not because they are absent from the text but because the cultural equipment to detect them is not assembled. The supernatural isotopy in Potocki is real; it requires W1828 to become visible. The resource selection is an epistemic act, not a technical parameter.

The minimalism of the semantic flatland yields four further properties that are not jointly available in the Greimasian tradition:

The model is **operationalized**: given a text and a set of resources, any analyst applying the same procedure obtains the same clusters. Reproducibility is not a standard that literary semiotics has historically held itself to; introducing it is a substantive contribution.

The model provides a **clear formalization**: isotopy clusters are connected components of a weighted graph above a threshold. The mathematical object is explicit, and its parameters are adjustable. The formalization does not replace interpretation — the theoretical reading of what a cluster means remains the analyst's contribution — but it makes the substrate of that interpretation auditable.

The model is **minimalistic**: it adheres to compositional semantics without postulating a hierarchy. The IDF gradient does the work that the nuclear/classeme distinction was supposed to do, without requiring a prior taxonomy of semic components. Semes are treated as cultural units that receive a lexical description — nothing more is assumed about their internal structure.

The model uses **general-purpose, purpose-selected resources**: no dedicated annotation is required. The pipeline can be applied to any text for which the relevant lexical resources exist, and the number and selection of resources is a theoretically meaningful degree of freedom rather than a fixed parameter.

### 5.2 What the flatland costs

The costs are real and should be stated plainly. The collapse of semic hierarchy means that distinctions Rastier considers theoretically significant — between inherent and afferent semes, between micro- and macro-semantic levels — are invisible to the pipeline. Whether those distinctions are doing genuine explanatory work, or whether they are taxonomic scaffolding that accrues over time without proportional empirical payoff, is a question the pipeline cannot answer. It can only report that the results it produces are interpretively defensible without them.

The surface-based, definition-centered operationalization of semes is a deliberate simplification. It captures what appears in dictionary definitions, which is not the same as what a trained semiotician would assign. The gap is empirically observable in the isolates: *opium* in the Poe passage has no lexical neighbors in the passage and remains a permanent isolate at all tiers, despite being semantically the most charged term. The pipeline correctly identifies its singularity but cannot explain it — that explanation requires exactly the kind of contextual, afferent seme assignment that the flatland excludes. The isolate is the fingerprint of what the model cannot do.

The moving window model, discussed in §3.2, addresses the sequential dimension of reading but not its mnemonic dimension. High-salience lexemes — semantic milestones — persist in the reader's active encyclopedia beyond their positional window, conditioning interpretation at a distance. A salience-weighted persistence model would capture this, at the cost of additional parameters. The current pipeline stays minimal by acknowledging the gap rather than filling it with an underspecified mechanism. Complexity is addressed honestly; it is not hidden inside the formalism.

### 5.3 Beyond lexicalization

The pipeline operationalizes isotopy detection at the lexical layer — the layer where cultural units have received a linguistic description and that description has been stored in a dictionary. This is a principled scope limitation, not a theoretical commitment to the primacy of language. Eco is explicit that the encyclopedia is not exclusively linguistic: perceptual contents, gestural schemas, pictorial conventions, and musical figures all participate in the construction of meaning and are all, in principle, sites of isotopic recurrence.

A cluster such as `gyration–swing` in the Potocki passage illustrates the point. The pipeline detects it correctly as a STRONG isotopy grounded in shared kinetic-rotational semes. But the full semantic weight of that cluster — a hanged body turning in the wind, the physical obscenity of the gallows scene — is carried as much by perceptual and gestural content as by lexical description. The pipeline detects the lexical surface of an isotopy whose depth is multimodal.

Extending the flatland to other modalities would require purpose-selected resources of a different kind: image databases, gesture lexicons, domain-specific perceptual ontologies. The architecture is in principle compatible with such extensions — the bipartite graph would simply gain additional seme types alongside definitional content words. Whether IDF weighting remains appropriate across modalities is an open question. What the present pipeline demonstrates is that the lexical layer alone is sufficient to detect isotopic structure that is interpretively significant, and that the structure it misses is systematically identifiable — through the isolates, through sub-threshold edges, and through clusters whose detected content is perceptual rather than cultural-symbolic.

---

## 6. A note on AI assistance and the two flatlands

This paper was developed in part through dialogue with a large language model (Claude, Anthropic). The irony is not incidental: a system whose semantic representations are fundamentally distributional — trained on co-occurrence statistics across vast corpora, producing opaque high-dimensional embeddings — was used to help articulate the argument for a lexicographic, definition-based, transparent alternative. The two flatlands were in dialogue throughout the writing process.

This does not undermine the argument; it sharpens it. The LLM contributed fluency, literature retrieval, and generative pressure on the theoretical claims. It could not show its work. When it identified *ghost* and *demon* as semantically related, no seme weights, IDF scores, or dictionary entries were available for inspection. The pipeline can provide exactly that. The difference between a system that produces defensible outputs and one that produces auditable reasoning is not a technical detail — it is the difference between a tool and an oracle. This paper is an argument for tools.

We flag this not to perform transparency but because it is genuinely relevant to the epistemological claims made in §5.1. The question of what kind of semantic evidence is appropriate for literary scholarship is not only a question about dictionaries and corpora — it is also a question about which computational partners humanists should choose, and why.

---

## References

Barbaresi, A. (2021). *simplemma*: A simple multilingual lemmatizer for Python. https://github.com/adbar/simplemma

Binelli, A. (2025). Isotopy and literary translation: Semiotic tools for a stylistic target. *LEA — Lingue e Letterature d'Oriente e d'Occidente*, 14. https://doi.org/10.36253/lea-1824-484x-16841

Brachman, R. J., & Levesque, H. J. (eds.) (1985). *Readings in Knowledge Representation*. San Mateo, CA: Morgan Kaufmann.

Daneman, M., & Carpenter, P. A. (1980). Individual differences in working memory and reading. *Journal of Verbal Learning and Verbal Behavior*, 19, 450–466.

Eco, U. (1975). *Trattato di semiotica generale*. Milan: Bompiani.

Eco, U. (1979). *The Role of the Reader*. Bloomington: Indiana University Press.

Eco, U. (1980). Two problems in textual interpretation. *Poetics Today*, 2, 145–161.

Eco, U. (1984). *Semiotics and the Philosophy of Language*. Bloomington: Indiana University Press.

Fillmore, C. J. (1982). Frame semantics. In *Linguistics in the Morning Calm*. Seoul: Hanshin, 111–137.

Gärdenfors, P. (2000). *Conceptual Spaces: The Geometry of Thought*. Cambridge, MA: MIT Press.

Greimas, A. J. (1966). *Sémantique structurale*. Paris: Larousse.

Greimas, A. J., & Courtés, J. (1979). *Sémiotique: Dictionnaire raisonné de la théorie du langage*. Paris: Hachette.

Hurford, J. R. (2007). *The Origins of Meaning*. Oxford: Oxford University Press.

Just, M. A., & Carpenter, P. A. (1980). A theory of reading: From eye fixations to comprehension. *Psychological Review*, 87, 329–354.

Just, M. A., & Carpenter, P. A. (1992). A capacity theory of comprehension: Individual differences in working memory. *Psychological Review*, 99, 122–149.

Kerbrat-Orecchioni, C. (1976). Problématique de l'isotopie. *Linguistique et sémiologie* (Travaux du Centre de Recherches Linguistiques et Sémiologiques de Lyon), 1, 11–34. [Not available online; discussed in Binelli 2025.]

Lenci, A., & Sahlgren, M. (2023). *Distributional Semantics*. Cambridge: Cambridge University Press.

Mel'čuk, I., & Polguère, A. (2007). *Lexique actif du français*. Brussels: De Boeck.

Miller, G. A. (1995). WordNet: A lexical database for English. *Communications of the ACM*, 38(11), 39–41.

Nelson, D. L., McEvoy, C. L., & Schreiber, T. A. (2004). The University of South Florida free association, rhyme, and word fragment norms. *Behavior Research Methods, Instruments, & Computers*, 36(3), 402–407.

Paolucci, C. (2010). *Struttura e interpretazione*. Milano: Bompiani. [**PAGE REFERENCE TO VERIFY**]

Pincemin, B. (2012). Sémantique interprétative et textométrie. *Texto!* XVII(3). http://www.revue-texto.net/index.php?id=3049

Poe, E. A. (1840). "The Fall of the House of Usher." In *Tales of the Grotesque and Arabesque*. Philadelphia: Lea and Blanchard.

Potocki, J. (2008). *The Manuscript Found in Saragossa*. Trans. I. Maclean. London: Penguin.

Quillian, M. R. (1968). Semantic memory. In M. Minsky (ed.), *Semantic Information Processing*. Cambridge, MA: MIT Press, 227–270.

Rastier, F. (1987). *Sémantique interprétative*. Paris: PUF.

Rastier, F. (1991). *Sémantique et recherches cognitives*. Paris: PUF.

Rastier, F. (2011). *La mesure et le grain: Sémantique de corpus*. Paris: Champion.

Steyvers, M., & Tenenbaum, J. B. (2005). The large-scale structure of semantic networks: Statistical analyses and a model of semantic growth. *Cognitive Science*, 29(1), 41–78.

Rosch, E. (1975). Cognitive representations of semantic categories. *Journal of Experimental Psychology: General*, 104(3), 192–233.
