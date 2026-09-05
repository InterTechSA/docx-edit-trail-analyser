import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))


from correlation_engine import CorrelationEngine


class TestCorrelationEngine(unittest.TestCase):

    def setUp(self):

        self.engine = CorrelationEngine()

    def test_retained_revision_evidence_has_priority(self):

        result = self.engine.classify(
            rsid_root="11111111",

            rsid_table=[
                "11111111",
                "22222222",
            ],

            document_rsids=[],

            revisions=[
                {
                    "type": "insertion",
                    "author": "Test User",
                    "date": "2026-09-05T10:00:00Z",
                    "text": "Inserted text",
                }
            ],

            core_properties={},

            app_properties={},
        )

        self.assertEqual(
            result["category"],
            "retained tracked-revision evidence"
        )

    def test_multiple_rsid_pattern_evidence(self):

        result = self.engine.classify(
            rsid_root="11111111",

            rsid_table=[
                "11111111",
                "22222222",
            ],

            document_rsids=[
                {
                    "element": "p",
                    "attribute": "rsidR",
                    "value": "11111111",
                }
            ],

            revisions=[],

            core_properties={},

            app_properties={},
        )

        self.assertEqual(
            result["category"],
            "multiple-RSID-pattern evidence"
        )

    def test_duplicate_rsids_do_not_count_as_multiple(self):

        result = self.engine.classify(
            rsid_root="11111111",

            rsid_table=[
                "11111111",
                "11111111",
            ],

            document_rsids=[
                {
                    "element": "p",
                    "attribute": "rsidR",
                    "value": "11111111",
                }
            ],

            revisions=[],

            core_properties={
                "creator": "Test User",
                "last_modified_by": None,
                "created": None,
                "modified": None,
            },

            app_properties={},
        )

        self.assertEqual(
            result["category"],
            "metadata-only evidence"
        )

    def test_metadata_only_evidence(self):

        result = self.engine.classify(
            rsid_root=None,

            rsid_table=[],

            document_rsids=[],

            revisions=[],

            core_properties={
                "creator": "Test User",
                "last_modified_by": "Test User",
                "created": "2026-09-01T10:00:00Z",
                "modified": "2026-09-05T10:00:00Z",
            },

            app_properties={
                "application": "Microsoft Office Word",
                "app_version": "16.0000",
            },
        )

        self.assertEqual(
            result["category"],
            "metadata-only evidence"
        )

    def test_application_metadata_alone_counts_as_metadata(self):

        result = self.engine.classify(
            rsid_root=None,

            rsid_table=[],

            document_rsids=[],

            revisions=[],

            core_properties={
                "creator": None,
                "last_modified_by": None,
                "created": None,
                "modified": None,
            },

            app_properties={
                "application": "Microsoft Office Word",
                "app_version": None,
            },
        )

        self.assertEqual(
            result["category"],
            "metadata-only evidence"
        )

    def test_no_selected_edit_artifact_observed(self):

        result = self.engine.classify(
            rsid_root=None,

            rsid_table=[],

            document_rsids=[],

            revisions=[],

            core_properties={
                "creator": None,
                "last_modified_by": None,
                "created": None,
                "modified": None,
            },

            app_properties={
                "application": None,
                "app_version": None,
            },
        )

        self.assertEqual(
            result["category"],
            "no selected edit artifact observed"
        )

    def test_classification_contains_basis(self):

        result = self.engine.classify(
            rsid_root="11111111",

            rsid_table=[
                "11111111",
                "22222222",
            ],

            document_rsids=[],

            revisions=[],

            core_properties={},

            app_properties={},
        )

        self.assertIn(
            "basis",
            result
        )

        self.assertGreater(
            len(result["basis"]),
            0
        )

    def test_classification_contains_limitations(self):

        result = self.engine.classify(
            rsid_root="11111111",

            rsid_table=[
                "11111111",
                "22222222",
            ],

            document_rsids=[],

            revisions=[],

            core_properties={},

            app_properties={},
        )

        self.assertIn(
            "limitations",
            result
        )

        self.assertGreater(
            len(result["limitations"]),
            0
        )


if __name__ == "__main__":
    unittest.main()