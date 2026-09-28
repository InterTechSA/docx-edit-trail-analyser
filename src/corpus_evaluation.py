"""
Corpus-level evaluation shared by the dashboard and the batch
command-line evaluator.

Given the evidence extracted from every sample and the matching
ground-truth records, it produces everything the research
questions need:

    RQ1  artifact_presence    which selected artifacts are present
                              in each final file
    RQ2  metrics / ablation   rule-based vs metadata-only baseline,
         confusion matrices   and the three RSID-scope variants
    RQ3  survival             which artifacts survive each
                              parent -> child transformation

plus the per-sample ground-truth agreement used for extraction
correctness.
"""

from pathlib import Path

from baseline_classifier import MetadataOnlyBaseline
from correlation_engine import RSID_SCOPES
from evidence_pipeline import correlate
from ground_truth_evaluator import GroundTruthEvaluator
from research_metrics import CATEGORIES, ResearchMetrics
from survival_analysis import artifact_sets, survival_table


def resolve_baseline(sample_name, ground_truth, analysed_samples,
                     ground_truth_records):
    """
    Pick the evidence a sample should be compared with for
    "modified_timestamp_later_than_baseline":

        1. its parent, named in "derived_from"
        2. otherwise the sample whose ground truth has
           "role": "baseline"
        3. otherwise the sample with sample_id "01_baseline"
           (the original synthetic corpus)
    """

    parent = ground_truth.get("derived_from")

    if parent:

        target = Path(parent).name

        for name, evidence in analysed_samples.items():
            if Path(name).name == target:
                return evidence

    for name, record in ground_truth_records.items():
        if record.get("role") == "baseline" and name != sample_name:
            return analysed_samples.get(name)

    for name, record in ground_truth_records.items():
        if record.get("sample_id") == "01_baseline":
            return analysed_samples.get(name)

    return None


def artifact_presence(analysed_samples):
    """
    RQ1: one row per sample, one boolean/count column per artifact
    group, from the final file only.
    """

    rows = []

    for name, evidence in analysed_samples.items():

        sets = artifact_sets(evidence)

        row = {"sample": name}

        for group, values in sets.items():
            row[group] = len(values)

        rows.append(row)

    return rows


def evaluate_corpus(analysed_samples, ground_truth_records):
    """
    Returns a dict with keys:
        evaluations, metrics, confusion, ablation, survival,
        presence, labelled_samples
    """

    evaluator = GroundTruthEvaluator()
    metrics_engine = ResearchMetrics()
    baseline = MetadataOnlyBaseline()

    evaluations = {}

    for sample_name, ground_truth in ground_truth_records.items():

        evidence = analysed_samples.get(sample_name)

        if evidence is None:
            continue

        evaluations[sample_name] = evaluator.evaluate_sample(
            ground_truth,
            evidence,
            resolve_baseline(
                sample_name,
                ground_truth,
                analysed_samples,
                ground_truth_records,
            ),
        )

    metrics = metrics_engine.evaluate_corpus(
        analysed_samples,
        ground_truth_records
    )

    # -------------------------------------------------
    # Labelled samples for RQ2
    # -------------------------------------------------

    labelled = [
        (name, record)
        for name, record in ground_truth_records.items()
        if name in analysed_samples
        and "classification" in record.get(
            "expected_selected_evidence", {}
        )
    ]

    y_true = [
        record["expected_selected_evidence"]["classification"]
        for _, record in labelled
    ]

    baseline_pred = [
        baseline.classify(
            analysed_samples[name].get("core_properties", {}),
            analysed_samples[name].get("app_properties", {}),
        )["category"]
        for name, _ in labelled
    ]

    # -------------------------------------------------
    # RSID-scope ablation
    # -------------------------------------------------

    ablation = {}
    confusion = {}

    negative_controls = [
        name for name, record in labelled
        if record.get("negative_control")
    ]

    for scope in RSID_SCOPES:

        predictions = [
            correlate(analysed_samples[name], scope)
            ["classification"]["category"]
            for name, _ in labelled
        ]

        report = (
            metrics_engine.classification_report(y_true, predictions)
            if y_true else None
        )

        control_fp = sum(
            1
            for (name, _), prediction in zip(labelled, predictions)
            if name in negative_controls
            and prediction == "multiple-RSID-pattern evidence"
        )

        ablation[scope] = {
            "accuracy": report["accuracy"] if report else None,
            "macro_precision": (
                report["macro_precision"] if report else None
            ),
            "macro_recall": report["macro_recall"] if report else None,
            "negative_controls": len(negative_controls),
            "negative_control_rsid_false_positives": control_fp,
            "predictions": dict(
                zip([name for name, _ in labelled], predictions)
            ),
        }

        confusion[f"rule ({scope})"] = metrics_engine.confusion_matrix(
            y_true, predictions
        )

    confusion["metadata-only baseline"] = (
        metrics_engine.confusion_matrix(y_true, baseline_pred)
    )

    ablation["metadata-only baseline"] = {
        "accuracy": (
            metrics_engine.classification_report(
                y_true, baseline_pred
            )["accuracy"]
            if y_true else None
        ),
        "predictions": dict(
            zip([name for name, _ in labelled], baseline_pred)
        ),
    }

    return {
        "labelled_samples": len(labelled),
        "true_labels": dict(
            zip([name for name, _ in labelled], y_true)
        ),
        "evaluations": evaluations,
        "metrics": metrics,
        "confusion": confusion,
        "categories": list(CATEGORIES),
        "ablation": ablation,
        "survival": survival_table(
            analysed_samples, ground_truth_records
        ),
        "presence": artifact_presence(analysed_samples),
    }
