# DOCX Edit-Trail Analyser

A digital-forensics research tool that reads the hidden edit trail inside Microsoft Word `.docx` files. It extracts Revision Save Identifiers (RSIDs), retained tracked-change markup and document properties, then presents them as an **evidence profile** with every finding traceable to the XML that produced it.

**Research category:** Digital Authenticity
**Research theme:** Read hidden edit trails in digital files

> The tool never reports "edited" / "not edited", "authentic" or "forged". It reports *what evidence is present, how strong it is on each dimension, where it came from, and what it cannot prove.*

---

## Contents

- [Why](#why)
- [What it examines](#what-it-examines)
- [How it works](#how-it-works)
- [Evidence profile and categories](#evidence-profile-and-categories)
- [Visualisations](#visualisations)
- [Installation](#installation)
- [Usage](#usage)
- [Controlled corpus and ground truth](#controlled-corpus-and-ground-truth)
- [Evaluation and research questions](#evaluation-and-research-questions)
- [Project structure](#project-structure)
- [Testing](#testing)
- [Scope and limitations](#scope-and-limitations)
---

## Why

Investigators receive DOCX files that look complete and credible, but Word does not show how a file was created, copied, edited or cleaned. A DOCX is an OOXML package, a ZIP of XML parts, and some of those parts keep traces of editing that are invisible in Word. The difficulty is interpretation. RSIDs are not a chronological edit log; templates carry RSIDs into new files; accepting tracked changes erases their markup; metadata can be edited by anyone. The analyser therefore exposes the raw evidence and the limits of each inference rather than issuing a verdict.

## What it examines

Four OOXML parts, three evidence groups:

| Evidence group | Artifacts | Part |
| --- | --- | --- |
| RSID evidence | `rsidRoot`, RSID table; `rsidR`, `rsidRDefault`, `rsidRPr`, `rsidDel`, `rsidP`, `rsidSect`, `rsidTr` attributes | `word/settings.xml`, `word/document.xml` |
| Retained revision evidence | content insertions and deletions (`w:ins`, `w:del`), moves (`w:moveFrom`, `w:moveTo`), paragraph-mark and table-row revisions, formatting changes (`w:rPrChange`, `w:pPrChange`, ...), each with author, date, text and ID | `word/document.xml` |
| Context evidence | creator, last modifier, created and modified timestamps, application and version | `docProps/core.xml`, `docProps/app.xml` |

## How it works

```text
DOCX file
  -> Package Reader       (package_reader.py)      opens the ZIP, reads the 4 parts only
  -> Target XML Parser    (xml_parser.py)          namespace-aware parsing
  -> Artifact Extractor   (artifact_extractor.py)  typed, traceable evidence records
  -> Correlation Engine   (correlation_engine.py)  evidence profile + strongest pattern + trace
  -> Evidence View        (dashboard.py / main.py)
```

`evidence_pipeline.analyse_docx()` runs the four modules. The dashboard, the command-line tool and the batch evaluator all call it, so every interface produces identical evidence. The pipeline only ever sees the final DOCX; ground truth is compared afterwards by a separate evaluation layer.

## Evidence profile and categories

**Evidence profile (primary output).** Each dimension is scored independently from 0 to 3, so a document can register on several at once:

| Dimension | 0 | 1 | 2 | 3 |
| --- | --- | --- | --- | --- |
| Retained revisions | none | only paragraph-mark or formatting markers | 1-4 content revisions | 5+ |
| RSID pattern | none counted | 1 (one session) | 2-4 | 5+ |
| Context metadata | no signal | 1 signal | 2 signals (cap) | n/a |

The metadata signals are "modified is later than created" and "last modifier is not the creator". The thresholds are named constants in `CorrelationEngine`.

**Strongest individual pattern.** Rules are checked in priority order: *retained tracked-revision evidence*, then *multiple-RSID-pattern evidence*, then *metadata-only evidence*, then *no selected edit artifact observed*. Each result carries a `basis`, its `limitations`, and an `evidence` trace (OOXML part, element, attribute and value).

**RSID counting rule** (`--rsid-scope`, or the sidebar in the dashboard):

| Scope | Counts |
| --- | --- |
| `document` (default) | RSIDs referenced in `word/document.xml` |
| `content` | as `document`, excluding section properties (`w:sectPr`), which templates copy into new files |
| `all` | root, settings table and document combined (original prototype rule) |

All three are reported side by side in the corpus evaluation, as an ablation.

## Visualisations

**Single Document mode:**

- Evidence overview metrics and the artifact profile.
- RSID tab: root, table, attributes, occurrence map and relationship view.
- Revision tab: typed revision table and chart.
- Metadata tab.
- Interpretation tab: the **evidence profile chart**, the strongest pattern, the **supporting evidence trace** table, and limitations.
- Package details.

**Corpus Comparison mode:**

- Evidence profile grouped bars and the **evidence fingerprint heatmap**.
- **Artifact presence heatmap** (RQ1).
- Detection matrix and timestamp comparison.
- Ground-truth agreement chart.
- Research metrics.
- **RSID-rule ablation chart** and **confusion matrices** (RQ2).
- **Artifact survival heatmap** (RQ3).

The same figures are exported as PNG files by `batch_evaluate.py`.

## Installation

Requires Python 3.10+.

```bash
git clone https://github.com/InterTechSA/docx-edit-trail-analyser.git
cd docx-edit-trail-analyser
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

## Usage

**Dashboard (visual evidence view):**

```bash
streamlit run src/dashboard.py
```

Choose *Single Document* or *Corpus Comparison*, then upload DOCX files. In corpus mode, upload parents together with their derived samples so survival can be computed. Ground truth is loaded automatically from `samples/ground_truth/<same name>.json`.

**Command line (single file, text evidence view):**

```bash
python src/main.py samples/controlled/03_tracked_changes.docx
python src/main.py path/to/file.docx --rsid-scope content
```

**Batch evaluation (tables and figures for the report):**

```bash
python src/batch_evaluate.py                                   # pilot corpus
python src/batch_evaluate.py --samples samples/word_native --out results/word_native
```

This writes `summary.md`, `evidence_summary.csv`, `artifact_presence.csv`, `ground_truth_results.csv`, `survival.csv`, `metrics.json` and `fig1`-`fig6` PNG files.

## Controlled corpus and ground truth

| Folder | Contents |
| --- | --- |
| `samples/controlled/` | 3 python-docx samples (pilot validation of the extractor) |
| `samples/word_native/` | Microsoft Word samples created by the recorded protocol, plus `environment.json` |
| `samples/ground_truth/` | one JSON per sample: actions, parent (`derived_from`) or comparison sample (`compare_with`), transformation, expected evidence, classification label |

The ground truth for the 12 Word-native samples (W01-W12) was written **before** the documents were created (pre-registration). They cover:

- a baseline
- save-as without editing
- direct edits across sessions
- tracked changes retained, accepted and rejected
- two same-template negative controls
- Document Inspector cleaning
- a file-copy positive control
- paste into a new document

See **[docs/CORPUS_GUIDE.md](docs/CORPUS_GUIDE.md)** for the step-by-step protocol.

## Evaluation and research questions

| RQ | Question | Measured by |
| --- | --- | --- |
| RQ1 | Which selected RSID, revision-markup and property artifacts remain in final DOCX files after controlled creation, saving, editing and Track Changes actions? | artifact presence table and heatmap; ground-truth extraction correctness |
| RQ2 | Does rule-based correlation of RSID, revision and context evidence classify the predefined categories more accurately than a metadata-only baseline? | accuracy, per-category precision, recall and false-positive rate, correlation benefit, confusion matrices, RSID-rule ablation, template false positives |
| RQ3 | How do save without editing, accepting and rejecting tracked changes, copying and metadata cleaning affect the survival and interpretation of the selected artifacts? | parent-to-child survival rate per artifact group (survival heatmap) |

Undefined ratios are reported as `n/a`, never as 0 or 1. Metrics based on fewer than 10 labelled samples are flagged as illustrative.

**Pilot result (synthetic corpus, 3 samples):** 14/14 evaluated ground-truth checks matched. The pilot also showed that an unedited, template-derived file already carries 3 distinct RSIDs, all on `w:sectPr`, which motivated the `content` RSID rule. See `results/pilot_synthetic/`.

## Project structure

```text
docx-edit-trail-analyser/
|-- README.md
|-- requirements.txt
|-- docs/
|   |-- CORPUS_GUIDE.md                 what a corpus is + Word-native protocol
|   `-- TECHNICAL_AND_VIDEO_GUIDE.md    internals, every visual, demo script, Q&A
|-- src/
|   |-- package_reader.py               module 1
|   |-- xml_parser.py                   module 2
|   |-- artifact_extractor.py           module 3
|   |-- correlation_engine.py           module 4
|   |-- evidence_pipeline.py            runs modules 1-4 (shared by all interfaces)
|   |-- dashboard.py                    Streamlit visual evidence view
|   |-- main.py                         command-line evidence view
|   |-- batch_evaluate.py               corpus evaluation -> CSV / JSON / PNG
|   |-- corpus_evaluation.py            combines all evaluation components
|   |-- corpus_comparison.py            per-sample comparison records
|   |-- ground_truth_evaluator.py       expected vs observed
|   |-- baseline_classifier.py          metadata-only baseline (RQ2)
|   |-- research_metrics.py             precision / recall / FPR / survival / benefit / confusion
|   `-- survival_analysis.py            parent -> child artifact survival (RQ3)
|-- samples/
|   |-- controlled/                     pilot (python-docx)
|   |-- word_native/                    Word-native corpus + environment.json
|   `-- ground_truth/                   one JSON per sample
|-- results/                           batch evaluation outputs
`-- tests/                             unittest suite
```

## Testing

```bash
python -m unittest discover -s tests
```

There are 79 tests. They cover every module, Word-native revision structures (paragraph marks, moves, formatting changes), the three RSID rules, evidence traceability, survival analysis, corpus evaluation and the batch exporter.

## Scope and limitations

The analyser does **not**:

- determine authenticity or forgery
- identify the person who edited a file
- reconstruct complete edit history
- count editors or sessions from RSIDs
- recover deleted content or analyse disk images
- detect deliberate tampering with the XML

Author names, dates and timestamps are application-supplied and editable. The absence of an artifact does not show that an event did not happen. Results come from one workstation and one Word version, and should not be generalised beyond that without further samples.

## Status

- [x] Package Reader, Target XML Parser, Artifact Extractor
- [x] RSID, retained-revision and context-metadata extraction (including Word-native revision types)
- [x] Correlation Engine: evidence profile, strongest pattern, evidence trace, three RSID rules
- [x] Evidence views: Streamlit dashboard and command line
- [x] Evaluation: ground truth, metrics, metadata-only baseline, ablation, survival analysis
- [x] Batch evaluator with report figures
- [x] Pilot corpus (synthetic) evaluated
- [x] Word-native corpus protocol and pre-registered ground truth
- [ ] Word-native corpus created and evaluated
