# Semantic Flatland: A Minimalistic Operational Pipeline for Isotopy Detection

Code and data for the paper:

> Andrea Valle, "Semantic Flatland: A Minimalistic Operational Pipeline for Isotopy Detection," submitted to *Digital Scholarship in the Humanities* (Oxford University Press).

---

## Overview

This repository contains the full pipeline for computational isotopy detection in literary prose, as described in the paper. The pipeline takes a source text and a set of lexical resources as input and produces ranked isotopy clusters as output in five stages:

1. **Lexeme extraction** — tokenize, POS tag, filter, lemmatize
2. **Definition lookup and sense selection** — fetch definitions, tokenize/lemmatize senses, redirect filter, Lesk scoring, top-2 selection, merge and filter
3. **IDF weighting, profile construction, and bipartite graph**
4. **Similarity scoring and graph construction** — project/min operator, edge scores, similarity graph, threshold S/M/W
5. **Clustering** — complete-linkage clustering at three threshold tiers

The pipeline is applied to two passages: the gallows scene from Jan Potocki's *The Manuscript Found in Saragossa* (Day 1) and the opening paragraph of Edgar Allan Poe's "The Fall of the House of Usher."

---

## Repository Structure

```
isotopy.py                    # Core pipeline
consolidate.py                # Consolidates results across configurations
experiment_tautology_context.py  # Documents the tautology gate experiment

fetch_mw.ipynb                # Fetch Merriam-Webster definitions
fetch_w1828.ipynb             # Fetch Webster 1828 definitions
fetch_wiktionary.ipynb        # Fetch Wiktionary definitions
fetch_wordnet.ipynb           # Fetch WordNet definitions

make_comparison_svg.py        # Generate comparison matrix figures (Figs 14, 15)
make_edge_distribution.py     # Generate edge score distribution figure (Fig Z)
make_seme_bipartite.py        # Generate full bipartite graphs (Figs X, Y)
make_seme_star.py             # Generate seme star visualizations

data/
  potocki_results.json        # Full results, Potocki passage
  poe_results.json            # Full results, Poe passage
  potocki_ablation.json       # Ablation study results, Potocki
  poe_ablation.json           # Ablation study results, Poe

figures/
  isotopy_pipeline_diagram.svg
  isotopy_bipartite_abstract.svg
  isotopy_stage4_similarity.svg
  isotopy_stage5_clustering.svg
  isotopy_edge_distribution.pdf
  isotopy_bipartite_potocki_panel.pdf
  isotopy_bipartite_poe_panel.pdf
  isotopy_potocki_comparison.svg
  isotopy_poe_comparison.svg
  potocki_strong_graph.svg
  poe_strong_graph.svg
```

---

## Dependencies

```bash
pip install simplemma graphviz matplotlib networkx
```

- [`simplemma`](https://github.com/adbar/simplemma) — multilingual lemmatizer
- `graphviz` — graph layout and rendering
- `matplotlib` — edge distribution plots
- `networkx` — graph operations (optional)

Python 3.10+.

---

## Data Format

The JSON result files have the following top-level keys:

- `lemmas` — list of source lexemes
- `idf` — IDF weights per seme
- `expanded` — seme profiles per lexeme (seme → IDF weight)
- `raw_edges` — all pairwise similarity scores
- `tiers` — STRONG / MEDIUM / WEAK cluster lists

The ablation JSON files are lists of `{config, tiers}` objects, one per resource configuration (`WK`, `WN`, `MW`, `W1828`, `WK+WN+MW`, `WK+WN+MW+W1828`).

---

## Reproducing the Results

1. Fetch definitions using the four notebooks (requires API keys for MW and W1828 sources where applicable).
2. Run `isotopy.py` on each passage with the desired resource configuration.
3. Run `consolidate.py` to produce the ablation JSON files.
4. Run the `make_*.py` scripts to regenerate figures.

---

## Citation

```
@article{valle2025flatland,
  author  = {Valle, Andrea},
  title   = {Semantic Flatland: A Minimalistic Operational Pipeline for Isotopy Detection},
  journal = {Digital Scholarship in the Humanities},
  year    = {2025},
  note    = {Submitted}
}
```

---

## License

Code: MIT License.  
Data (JSON files): CC BY 4.0.  
Source texts (Appendix A of the paper): Potocki passage © Penguin/Ian Maclean translation; Poe passage public domain (Project Gutenberg).
