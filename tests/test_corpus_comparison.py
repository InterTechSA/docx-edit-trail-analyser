import unittest

from src.corpus_comparison import CorpusComparison


class TestCorpusComparison(unittest.TestCase):

    def setUp(self):

        self.comparison = CorpusComparison()

    def create_evidence(
        self,
        unique_rsids=None,
        document_rsids=None,
        revisions=None,
        core_properties=None,
        app_properties=None,
        category="metadata-only evidence"
    ):

        return {
            "unique_rsids":
                unique_rsids or [],

            "document_rsids":
                document_rsids or [],

            "revisions":
                revisions or [],

            "core_properties":
                core_properties or {},

            "app_properties":
                app_properties or {},

            "classification": {
                "category": category
            },
        }

    def test_create_basic_sample_record(self):

        evidence = self.create_evidence(
            unique_rsids=[
                "AAA",
                "BBB"
            ],
            document_rsids=[
                {
                    "value": "AAA"
                }
            ],
            core_properties={
                "creator": "Test Author",
                "modified":
                    "2026-09-05T18:00:00Z",
            },
        )

        result = (
            self.comparison.create_sample_record(
                "sample.docx",
                evidence
            )
        )

        self.assertEqual(
            result["sample"],
            "sample.docx"
        )

        self.assertEqual(
            result["distinct_rsids"],
            2
        )

        self.assertEqual(
            result[
                "document_rsid_attributes"
            ],
            1
        )

    def test_counts_insertions(self):

        evidence = self.create_evidence(
            revisions=[
                {
                    "type": "insertion"
                },
                {
                    "type": "insertion"
                },
            ]
        )

        result = (
            self.comparison.create_sample_record(
                "sample.docx",
                evidence
            )
        )

        self.assertEqual(
            result["insertions"],
            2
        )

        self.assertEqual(
            result["deletions"],
            0
        )

    def test_counts_deletions(self):

        evidence = self.create_evidence(
            revisions=[
                {
                    "type": "deletion"
                }
            ]
        )

        result = (
            self.comparison.create_sample_record(
                "sample.docx",
                evidence
            )
        )

        self.assertEqual(
            result["deletions"],
            1
        )

    def test_counts_total_revisions(self):

        evidence = self.create_evidence(
            revisions=[
                {
                    "type": "insertion"
                },
                {
                    "type": "deletion"
                },
            ]
        )

        result = (
            self.comparison.create_sample_record(
                "sample.docx",
                evidence
            )
        )

        self.assertEqual(
            result["retained_revisions"],
            2
        )

    def test_preserves_classification(self):

        evidence = self.create_evidence(
            category=(
                "retained tracked-revision "
                "evidence"
            )
        )

        result = (
            self.comparison.create_sample_record(
                "sample.docx",
                evidence
            )
        )

        self.assertEqual(
            result["classification"],
            (
                "retained tracked-revision "
                "evidence"
            )
        )

    def test_create_multiple_records(self):

        samples = {
            "baseline.docx":
                self.create_evidence(),

            "edited.docx":
                self.create_evidence(),
        }

        result = (
            self.comparison
            .create_comparison_records(
                samples
            )
        )

        self.assertEqual(
            len(result),
            2
        )

    def test_artifact_matrix_detects_presence(self):

        records = [
            {
                "sample": "sample.docx",
                "distinct_rsids": 2,
                "document_rsid_attributes": 1,
                "insertions": 1,
                "deletions": 0,
                "creator": "Test Author",
                "modified":
                    "2026-09-05T18:00:00Z",
                "application":
                    "Test Application",
            }
        ]

        matrix = (
            self.comparison
            .create_artifact_matrix(
                records
            )
        )

        self.assertTrue(
            matrix[0][
                "rsid_evidence"
            ]
        )

        self.assertTrue(
            matrix[0][
                "retained_insertion"
            ]
        )

        self.assertFalse(
            matrix[0][
                "retained_deletion"
            ]
        )

    def test_artifact_matrix_handles_absence(self):

        records = [
            {
                "sample": "sample.docx",
                "distinct_rsids": 0,
                "document_rsid_attributes": 0,
                "insertions": 0,
                "deletions": 0,
                "creator": None,
                "modified": None,
                "application": None,
            }
        ]

        matrix = (
            self.comparison
            .create_artifact_matrix(
                records
            )
        )

        self.assertFalse(
            matrix[0][
                "rsid_evidence"
            ]
        )

        self.assertFalse(
            matrix[0][
                "creator_metadata"
            ]
        )


if __name__ == "__main__":
    unittest.main()