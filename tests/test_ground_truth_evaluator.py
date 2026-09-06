import unittest

from src.ground_truth_evaluator import (
    GroundTruthEvaluator
)


class TestGroundTruthEvaluator(
    unittest.TestCase
):

    def setUp(self):
        self.evaluator = (
            GroundTruthEvaluator()
        )

    def create_evidence(
        self,
        revisions=None,
        rsids=None,
        core=None,
        app=None,
        classification=None
    ):
        return {
            "revisions":
                revisions or [],

            "unique_rsids":
                rsids or [],

            "core_properties":
                core or {},

            "app_properties":
                app or {},

            "classification": {
                "category":
                    classification
            },
        }

    def test_expected_zero_revisions(self):

        ground_truth = {
            "sample_id":
                "01_baseline",

            "expected_selected_evidence": {
                "retained_insertions": 0,
                "retained_deletions": 0,
            },
        }

        evidence = self.create_evidence()

        result = (
            self.evaluator.evaluate_sample(
                ground_truth,
                evidence
            )
        )

        self.assertEqual(
            result["matched_count"],
            2
        )

        self.assertEqual(
            result["mismatched_count"],
            0
        )

    def test_expected_insertion(self):

        ground_truth = {
            "expected_selected_evidence": {
                "retained_insertions": 1,
                "insertion_text": "red",
            }
        }

        evidence = self.create_evidence(
            revisions=[
                {
                    "type": "insertion",
                    "text": "red",
                }
            ]
        )

        result = (
            self.evaluator.evaluate_sample(
                ground_truth,
                evidence
            )
        )

        self.assertEqual(
            result["matched_count"],
            2
        )

    def test_expected_deletion(self):

        ground_truth = {
            "expected_selected_evidence": {
                "retained_deletions": 1,
                "deletion_text": "brown",
            }
        }

        evidence = self.create_evidence(
            revisions=[
                {
                    "type": "deletion",
                    "text": "brown",
                }
            ]
        )

        result = (
            self.evaluator.evaluate_sample(
                ground_truth,
                evidence
            )
        )

        self.assertEqual(
            result["matched_count"],
            2
        )

    def test_revision_author(self):

        ground_truth = {
            "expected_selected_evidence": {
                "revision_author":
                    "Controlled Editor"
            }
        }

        evidence = self.create_evidence(
            revisions=[
                {
                    "type": "insertion",
                    "author":
                        "Controlled Editor",
                }
            ]
        )

        result = (
            self.evaluator.evaluate_sample(
                ground_truth,
                evidence
            )
        )

        self.assertEqual(
            result["matched_count"],
            1
        )

    def test_revision_dates_ignore_order(self):

        ground_truth = {
            "expected_selected_evidence": {
                "revision_dates": [
                    "2026-09-05T18:25:00Z",
                    "2026-09-05T18:26:00Z",
                ]
            }
        }

        evidence = self.create_evidence(
            revisions=[
                {
                    "type": "insertion",
                    "date":
                        "2026-09-05T18:26:00Z",
                },
                {
                    "type": "deletion",
                    "date":
                        "2026-09-05T18:25:00Z",
                },
            ]
        )

        result = (
            self.evaluator.evaluate_sample(
                ground_truth,
                evidence
            )
        )

        self.assertEqual(
            result["matched_count"],
            1
        )

    def test_classification_match(self):

        ground_truth = {
            "expected_selected_evidence": {
                "classification":
                    (
                        "retained "
                        "tracked-revision evidence"
                    )
            }
        }

        evidence = self.create_evidence(
            classification=(
                "retained "
                "tracked-revision evidence"
            )
        )

        result = (
            self.evaluator.evaluate_sample(
                ground_truth,
                evidence
            )
        )

        self.assertEqual(
            result["matched_count"],
            1
        )

    def test_context_metadata_present(self):

        ground_truth = {
            "expected_selected_evidence": {
                "context_metadata_present":
                    True
            }
        }

        evidence = self.create_evidence(
            core={
                "creator": "python-docx"
            }
        )

        result = (
            self.evaluator.evaluate_sample(
                ground_truth,
                evidence
            )
        )

        self.assertEqual(
            result["matched_count"],
            1
        )

    def test_modified_later_than_baseline(self):

        ground_truth = {
            "expected_selected_evidence": {
                (
                    "modified_timestamp_"
                    "later_than_baseline"
                ):
                    True
            }
        }

        baseline = self.create_evidence(
            core={
                "modified":
                    "2026-09-05T17:05:00Z"
            }
        )

        edited = self.create_evidence(
            core={
                "modified":
                    "2026-09-05T18:15:00Z"
            }
        )

        result = (
            self.evaluator.evaluate_sample(
                ground_truth,
                edited,
                baseline
            )
        )

        self.assertEqual(
            result["matched_count"],
            1
        )

    def test_rsid_no_claim_not_evaluated(self):

        ground_truth = {
            "expected_selected_evidence": {
                "rsid_expectation":
                    (
                        "No claim; generator "
                        "behavior is not "
                        "Microsoft Word behavior."
                    )
            }
        }

        evidence = self.create_evidence(
            rsids=[
                "AAA",
                "BBB",
            ]
        )

        result = (
            self.evaluator.evaluate_sample(
                ground_truth,
                evidence
            )
        )

        self.assertEqual(
            result["evaluated_count"],
            0
        )

        self.assertEqual(
            result[
                "not_evaluated_count"
            ],
            1
        )

        self.assertEqual(
            result["results"][0][
                "status"
            ],
            "Not evaluated"
        )

    def test_mismatch_detected(self):

        ground_truth = {
            "expected_selected_evidence": {
                "retained_insertions": 1
            }
        }

        evidence = self.create_evidence()

        result = (
            self.evaluator.evaluate_sample(
                ground_truth,
                evidence
            )
        )

        self.assertEqual(
            result["matched_count"],
            0
        )

        self.assertEqual(
            result["mismatched_count"],
            1
        )


if __name__ == "__main__":
    unittest.main()