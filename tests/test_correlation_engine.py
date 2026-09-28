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

        # Two distinct RSIDs referenced in word/document.xml.
        result = self.engine.classify(
            rsid_root="11111111",
            rsid_table=["11111111", "22222222"],
            document_rsids=[
                {"element": "p", "attribute": "rsidR",
                 "value": "11111111"},
                {"element": "r", "attribute": "rsidRPr",
                 "value": "22222222"},
            ],
            revisions=[],
            core_properties={},
            app_properties={},
        )

        self.assertEqual(
            result["category"],
            "multiple-RSID-pattern evidence"
        )

    def test_settings_only_rsids_do_not_trigger_document_scope(self):

        # Template-style case: extra RSIDs exist only in the
        # settings table. Under the default "document" scope this
        # must NOT be reported as a multiple-RSID pattern.
        result = self.engine.classify(
            rsid_root="11111111",
            rsid_table=["11111111", "22222222", "33333333"],
            document_rsids=[
                {"element": "p", "attribute": "rsidR",
                 "value": "11111111"},
            ],
            revisions=[],
            core_properties={"creator": "Test User"},
            app_properties={},
        )

        self.assertEqual(
            result["category"],
            "metadata-only evidence"
        )

    def test_all_scope_reproduces_prototype_rule(self):

        engine = CorrelationEngine(rsid_scope="all")

        result = engine.classify(
            rsid_root="11111111",
            rsid_table=["11111111", "22222222"],
            document_rsids=[
                {"element": "p", "attribute": "rsidR",
                 "value": "11111111"},
            ],
            revisions=[],
            core_properties={},
            app_properties={},
        )

        self.assertEqual(
            result["category"],
            "multiple-RSID-pattern evidence"
        )

        self.assertEqual(result["rsid_scope"], "all")

    def test_content_scope_ignores_section_property_rsids(self):

        engine = CorrelationEngine(rsid_scope="content")

        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

        kwargs = dict(
            rsid_root=None,
            rsid_table=[],
            document_rsids=[
                {"element": ns + "sectPr", "attribute": "rsidR",
                 "value": "00FC693F"},
                {"element": ns + "sectPr", "attribute": "rsidSect",
                 "value": "00034616"},
                {"element": ns + "p", "attribute": "rsidR",
                 "value": "00AA0001"},
            ],
            revisions=[],
            core_properties={"creator": "x"},
            app_properties={},
        )

        self.assertEqual(
            engine.classify(**kwargs)["category"],
            "metadata-only evidence"
        )
        self.assertEqual(
            self.engine.classify(**kwargs)["category"],
            "multiple-RSID-pattern evidence"
        )

    def test_invalid_scope_rejected(self):

        with self.assertRaises(ValueError):
            CorrelationEngine(rsid_scope="everything")

    def test_classification_and_profile_agree_on_rsids(self):

        kwargs = dict(
            rsid_root="11111111",
            rsid_table=["11111111", "22222222", "33333333"],
            document_rsids=[
                {"element": "p", "attribute": "rsidR",
                 "value": "11111111"},
            ],
            revisions=[],
            core_properties={},
            app_properties={},
        )

        category = self.engine.classify(**kwargs)["category"]
        profile = self.engine.score_evidence_dimensions(**kwargs)

        self.assertNotEqual(
            category, "multiple-RSID-pattern evidence"
        )
        self.assertLessEqual(profile["rsid_evidence"]["score"], 1)

    def test_evidence_trace_names_part_element_and_value(self):

        result = self.engine.classify(
            rsid_root=None,
            rsid_table=[],
            document_rsids=[],
            revisions=[{
                "type": "insertion",
                "author": "Test User",
                "date": "2026-09-05T10:00:00Z",
                "text": "red",
                "part": "word/document.xml",
                "element": "w:ins",
            }],
            core_properties={},
            app_properties={},
        )

        trace = result["evidence"]

        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[0]["part"], "word/document.xml")
        self.assertEqual(trace[0]["element"], "w:ins")
        self.assertIn("text=red", trace[0]["value"])

    def test_metadata_trace_lists_populated_fields(self):

        result = self.engine.classify(
            rsid_root=None,
            rsid_table=[],
            document_rsids=[],
            revisions=[],
            core_properties={"creator": "A", "modified": None},
            app_properties={"application": "Microsoft Office Word"},
        )

        parts = {item["part"] for item in result["evidence"]}

        self.assertEqual(
            parts, {"docProps/core.xml", "docProps/app.xml"}
        )
        self.assertEqual(len(result["evidence"]), 2)

    def test_paragraph_mark_only_revisions_score_minimal(self):

        profile = self.engine.score_evidence_dimensions(
            rsid_root=None,
            rsid_table=[],
            document_rsids=[],
            revisions=[{"type": "paragraph_mark_insertion"}],
            core_properties={},
            app_properties={},
        )

        self.assertEqual(profile["revision_evidence"]["score"], 1)

    def test_revision_scores_are_graded(self):

        def score(n):
            return self.engine.score_evidence_dimensions(
                rsid_root=None, rsid_table=[], document_rsids=[],
                revisions=[{"type": "insertion"}] * n,
                core_properties={}, app_properties={},
            )["revision_evidence"]["score"]

        self.assertEqual(score(0), 0)
        self.assertEqual(score(1), 2)
        self.assertEqual(score(4), 2)
        self.assertEqual(score(5), 3)

    def test_rsid_scores_are_graded(self):

        def score(n):
            rsids = [
                {"element": "p", "attribute": "rsidR",
                 "value": f"{i:08d}"}
                for i in range(n)
            ]
            return self.engine.score_evidence_dimensions(
                rsid_root=None, rsid_table=[],
                document_rsids=rsids, revisions=[],
                core_properties={}, app_properties={},
            )["rsid_evidence"]["score"]

        self.assertEqual(
            [score(n) for n in (0, 1, 2, 4, 5, 40)],
            [0, 1, 2, 2, 3, 3]
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