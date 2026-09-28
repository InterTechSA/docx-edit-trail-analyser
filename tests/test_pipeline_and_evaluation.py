import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
SAMPLES = PROJECT_ROOT / "samples" / "controlled"
GROUND_TRUTH = PROJECT_ROOT / "samples" / "ground_truth"

sys.path.insert(0, str(SRC_DIR))

from evidence_pipeline import analyse_docx, correlate  # noqa: E402
from survival_analysis import compare_pair, survival_table  # noqa: E402
from corpus_evaluation import evaluate_corpus, resolve_baseline  # noqa: E402
from research_metrics import ResearchMetrics  # noqa: E402
import batch_evaluate  # noqa: E402


def load_pilot_corpus():

    analysed = {}
    ground_truth = {}

    for path in sorted(SAMPLES.glob("*.docx")):
        analysed[path.name] = analyse_docx(path)
        with open(GROUND_TRUTH / f"{path.stem}.json") as handle:
            ground_truth[path.name] = json.load(handle)

    return analysed, ground_truth


class TestEvidencePipeline(unittest.TestCase):

    def test_tracked_sample_end_to_end(self):

        evidence = analyse_docx(SAMPLES / "03_tracked_changes.docx")

        self.assertEqual(
            evidence["classification"]["category"],
            "retained tracked-revision evidence"
        )
        self.assertEqual(
            evidence["evidence_profile"]["revision_evidence"]["score"], 2
        )
        self.assertTrue(evidence["classification"]["evidence"])

    def test_template_rsids_live_on_section_properties(self):

        # Pilot finding: the python-docx template puts its RSIDs on
        # w:sectPr, so only the "content" rule discounts them.
        evidence = analyse_docx(SAMPLES / "01_baseline.docx")

        self.assertEqual(
            correlate(evidence, "document")["classification"]["category"],
            "multiple-RSID-pattern evidence"
        )
        self.assertEqual(
            correlate(evidence, "content")["classification"]["category"],
            "metadata-only evidence"
        )

    def test_correlate_does_not_mutate_input(self):

        evidence = analyse_docx(SAMPLES / "01_baseline.docx")
        before = evidence["classification"]["category"]

        correlate(evidence, "content")

        self.assertEqual(evidence["classification"]["category"], before)


class TestSurvivalAnalysis(unittest.TestCase):

    def test_identical_files_fully_survive(self):

        evidence = analyse_docx(SAMPLES / "01_baseline.docx")

        rows = {r["artifact"]: r for r in compare_pair(evidence, evidence)}

        self.assertEqual(rows["Referenced RSIDs"]["survival_rate"], 1.0)
        self.assertIsNone(rows["Content revisions"]["survival_rate"])

    def test_accepting_changes_loses_revisions(self):

        parent = {
            "rsid_root": "A", "rsid_table": ["A"],
            "document_rsids": [{"value": "A"}],
            "revisions": [
                {"type": "insertion", "text": "red", "author": "E"},
                {"type": "deletion", "text": "brown", "author": "E"},
            ],
            "core_properties": {"creator": "X"},
            "app_properties": {},
        }
        child = dict(parent, revisions=[])

        rows = {r["artifact"]: r for r in compare_pair(parent, child)}

        self.assertEqual(rows["Content revisions"]["survival_rate"], 0.0)
        self.assertEqual(rows["Author metadata"]["survival_rate"], 1.0)

    def test_survival_table_uses_derived_from(self):

        analysed, ground_truth = load_pilot_corpus()

        rows = survival_table(analysed, ground_truth)

        self.assertTrue(rows)
        self.assertTrue(
            all(r["parent"] == "01_baseline.docx" for r in rows)
        )


class TestCorpusEvaluation(unittest.TestCase):

    def test_pilot_corpus_evaluates_cleanly(self):

        analysed, ground_truth = load_pilot_corpus()

        results = evaluate_corpus(analysed, ground_truth)

        matched = sum(
            e["matched_count"] for e in results["evaluations"].values()
        )
        mismatched = sum(
            e["mismatched_count"] for e in results["evaluations"].values()
        )

        self.assertGreater(matched, 0)
        self.assertEqual(mismatched, 0)
        self.assertEqual(
            set(results["ablation"]),
            {"document", "content", "all", "metadata-only baseline"}
        )

    def test_baseline_resolves_to_parent(self):

        analysed, ground_truth = load_pilot_corpus()

        baseline = resolve_baseline(
            "02_edited.docx",
            ground_truth["02_edited.docx"],
            analysed,
            ground_truth,
        )

        self.assertIs(baseline, analysed["01_baseline.docx"])

    def test_confusion_matrix(self):

        result = ResearchMetrics().confusion_matrix(
            ["a", "a", "b"], ["a", "b", "b"], labels=["a", "b"]
        )

        self.assertEqual(result["matrix"], [[1, 1], [0, 1]])


class TestBatchEvaluate(unittest.TestCase):

    def test_batch_writes_tables_and_figures(self):

        out_dir = Path(tempfile.mkdtemp())

        try:
            code = batch_evaluate.main([
                "--samples", str(SAMPLES),
                "--ground-truth", str(GROUND_TRUTH),
                "--out", str(out_dir),
            ])

            self.assertEqual(code, 0)

            for name in (
                "evidence_summary.csv", "survival.csv",
                "metrics.json", "summary.md",
            ):
                self.assertTrue((out_dir / name).exists(), name)

        finally:
            shutil.rmtree(out_dir)


if __name__ == "__main__":
    unittest.main()
