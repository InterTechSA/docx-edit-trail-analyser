from baseline_classifier import MetadataOnlyBaseline


CATEGORIES = [
    "retained tracked-revision evidence",
    "multiple-RSID-pattern evidence",
    "metadata-only evidence",
    "no selected edit artifact observed",
]

# Artifacts whose presence/absence is stated in the ground truth,
# mapped to (ground-truth key, revision type).
REVISION_ARTIFACTS = {
    "Retained insertions": ("retained_insertions", "insertion"),
    "Retained deletions": ("retained_deletions", "deletion"),
}


def _ratio(numerator, denominator):
    """Return numerator/denominator, or None when undefined."""

    if denominator == 0:
        return None

    return numerator / denominator


def _mean_defined(values):
    """Mean of the values that are not None; None if there are none."""

    defined = [v for v in values if v is not None]

    if not defined:
        return None

    return sum(defined) / len(defined)


class ResearchMetrics:
    """
    Evaluation metrics named in the proposal: extraction
    correctness (see GroundTruthEvaluator), precision, recall,
    false-positive rate, artifact survival rate and correlation
    benefit.

    Every ratio is None when its denominator is zero, so an
    undefined metric is never silently reported as 0 or 1.
    """

    # -----------------------------------------------------
    # Multi-class classification quality
    # -----------------------------------------------------

    def classification_report(
        self,
        y_true,
        y_pred,
        labels=CATEGORIES
    ):

        total = len(y_true)

        correct = sum(
            1 for t, p in zip(y_true, y_pred) if t == p
        )

        per_class = {}

        for label in labels:

            tp = sum(
                1 for t, p in zip(y_true, y_pred)
                if t == label and p == label
            )
            fp = sum(
                1 for t, p in zip(y_true, y_pred)
                if t != label and p == label
            )
            fn = sum(
                1 for t, p in zip(y_true, y_pred)
                if t == label and p != label
            )
            tn = total - tp - fp - fn

            per_class[label] = {
                "support": tp + fn,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
                "precision": _ratio(tp, tp + fp),
                "recall": _ratio(tp, tp + fn),
                "false_positive_rate": _ratio(fp, fp + tn),
            }

        return {
            "samples": total,
            "accuracy": _ratio(correct, total),
            "macro_precision": _mean_defined(
                c["precision"] for c in per_class.values()
            ),
            "macro_recall": _mean_defined(
                c["recall"] for c in per_class.values()
                if c["support"] > 0
            ),
            "per_class": per_class,
        }

    # -----------------------------------------------------
    # Confusion matrix
    # -----------------------------------------------------

    def confusion_matrix(self, y_true, y_pred, labels=CATEGORIES):
        """
        Rows are the ground-truth category, columns the predicted
        category: matrix[i][j] = number of samples whose true
        category is labels[i] and predicted category labels[j].
        """

        index = {label: i for i, label in enumerate(labels)}

        matrix = [[0 for _ in labels] for _ in labels]

        for truth, prediction in zip(y_true, y_pred):

            if truth in index and prediction in index:
                matrix[index[truth]][index[prediction]] += 1

        return {"labels": list(labels), "matrix": matrix}

    # -----------------------------------------------------
    # Binary artifact detection (present / absent)
    # -----------------------------------------------------

    def binary_report(self, expected_flags, observed_flags):

        pairs = list(zip(expected_flags, observed_flags))

        tp = sum(1 for e, o in pairs if e and o)
        fp = sum(1 for e, o in pairs if not e and o)
        fn = sum(1 for e, o in pairs if e and not o)
        tn = sum(1 for e, o in pairs if not e and not o)

        return {
            "samples": len(pairs),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": _ratio(tp, tp + fp),
            "recall": _ratio(tp, tp + fn),
            "false_positive_rate": _ratio(fp, fp + tn),
        }

    # -----------------------------------------------------
    # Artifact survival
    # -----------------------------------------------------

    def survival_rate(self, expected_counts, observed_counts):
        """
        Of the artifacts the controlled actions should have left
        in the file (sum of expected counts), the fraction that
        were observed in the final DOCX. Observed artifacts beyond
        the expected count do not raise the rate.
        """

        total_expected = 0
        survived = 0

        for expected, observed in zip(
            expected_counts, observed_counts
        ):

            if expected > 0:
                total_expected += expected
                survived += min(observed, expected)

        return _ratio(survived, total_expected)

    # -----------------------------------------------------
    # Correlation benefit (RQ2)
    # -----------------------------------------------------

    def correlation_benefit(self, y_true, rule_pred, baseline_pred):
        """
        Accuracy of the rule-based correlation versus the
        metadata-only baseline on the same labelled samples.
        benefit = rule accuracy - baseline accuracy.
        """

        total = len(y_true)

        rule_correct = [t == p for t, p in zip(y_true, rule_pred)]
        base_correct = [t == p for t, p in zip(y_true, baseline_pred)]

        rule_accuracy = _ratio(sum(rule_correct), total)
        baseline_accuracy = _ratio(sum(base_correct), total)

        benefit = None

        if rule_accuracy is not None and baseline_accuracy is not None:
            benefit = rule_accuracy - baseline_accuracy

        return {
            "samples": total,
            "rule_accuracy": rule_accuracy,
            "baseline_accuracy": baseline_accuracy,
            "benefit": benefit,
            "rule_only_correct": sum(
                1 for r, b in zip(rule_correct, base_correct)
                if r and not b
            ),
            "baseline_only_correct": sum(
                1 for r, b in zip(rule_correct, base_correct)
                if b and not r
            ),
        }

    # -----------------------------------------------------
    # Whole-corpus evaluation
    # -----------------------------------------------------

    def evaluate_corpus(self, analysed_samples, ground_truth_records):
        """
        analysed_samples:     {sample_name: evidence dict}
        ground_truth_records: {sample_name: ground-truth dict}

        Only samples whose ground truth states an expectation
        contribute to the corresponding metric, and the number of
        contributing samples is always returned so a caller can
        show how much data each figure rests on.
        """

        baseline = MetadataOnlyBaseline()

        y_true = []
        rule_pred = []
        baseline_pred = []

        artifact_data = {
            name: {"expected": [], "observed": []}
            for name in REVISION_ARTIFACTS
        }

        for sample_name, ground_truth in ground_truth_records.items():

            evidence = analysed_samples.get(sample_name)

            if evidence is None:
                continue

            expected = ground_truth.get(
                "expected_selected_evidence", {}
            )

            if "classification" in expected:

                y_true.append(expected["classification"])

                rule_pred.append(
                    evidence.get("classification", {}).get("category")
                )

                baseline_pred.append(
                    baseline.classify(
                        evidence.get("core_properties", {}),
                        evidence.get("app_properties", {}),
                    )["category"]
                )

            for name, (key, revision_type) in REVISION_ARTIFACTS.items():

                if key not in expected:
                    continue

                observed_count = sum(
                    1
                    for revision in evidence.get("revisions", [])
                    if revision.get("type") == revision_type
                )

                artifact_data[name]["expected"].append(expected[key])
                artifact_data[name]["observed"].append(observed_count)

        artifacts = {}

        all_expected = []
        all_observed = []

        for name, data in artifact_data.items():

            if not data["expected"]:
                continue

            report = self.binary_report(
                [e > 0 for e in data["expected"]],
                [o > 0 for o in data["observed"]],
            )

            report["survival_rate"] = self.survival_rate(
                data["expected"], data["observed"]
            )

            artifacts[name] = report

            all_expected.extend(data["expected"])
            all_observed.extend(data["observed"])

        return {
            "labelled_samples": len(y_true),

            "classification": (
                self.classification_report(y_true, rule_pred)
                if y_true else None
            ),

            "baseline_classification": (
                self.classification_report(y_true, baseline_pred)
                if y_true else None
            ),

            "correlation_benefit": (
                self.correlation_benefit(
                    y_true, rule_pred, baseline_pred
                )
                if y_true else None
            ),

            "artifacts": artifacts,

            "overall_survival_rate": self.survival_rate(
                all_expected, all_observed
            ),
        }