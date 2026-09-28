import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))


from xml_parser import TargetXmlParser
from artifact_extractor import ArtifactExtractor


class TestArtifactExtractor(unittest.TestCase):

    def setUp(self):
        self.parser = TargetXmlParser()
        self.extractor = ArtifactExtractor()

    # -----------------------------------------------------
    # RSID root tests
    # -----------------------------------------------------

    def test_extract_rsid_root(self):

        xml = b"""
        <w:settings
            xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">

            <w:rsids>
                <w:rsidRoot w:val="00112233"/>
            </w:rsids>

        </w:settings>
        """

        root = self.parser.parse(xml)

        result = self.extractor.extract_rsid_root(
            root
        )

        self.assertEqual(
            result,
            "00112233"
        )

    def test_missing_rsid_root_returns_none(self):

        xml = b"""
        <w:settings
            xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        </w:settings>
        """

        root = self.parser.parse(xml)

        result = self.extractor.extract_rsid_root(
            root
        )

        self.assertIsNone(result)

    # -----------------------------------------------------
    # RSID table tests
    # -----------------------------------------------------

    def test_extract_rsid_table(self):

        xml = b"""
        <w:settings
            xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">

            <w:rsids>
                <w:rsid w:val="11111111"/>
                <w:rsid w:val="22222222"/>
                <w:rsid w:val="33333333"/>
            </w:rsids>

        </w:settings>
        """

        root = self.parser.parse(xml)

        result = self.extractor.extract_rsid_table(
            root
        )

        self.assertEqual(
            result,
            [
                "11111111",
                "22222222",
                "33333333",
            ]
        )

    def test_missing_rsid_table_returns_empty_list(self):

        xml = b"""
        <w:settings
            xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        </w:settings>
        """

        root = self.parser.parse(xml)

        result = self.extractor.extract_rsid_table(
            root
        )

        self.assertEqual(
            result,
            []
        )

    # -----------------------------------------------------
    # Document RSID tests
    # -----------------------------------------------------

    def test_extract_single_document_rsid(self):

        xml = b"""
        <w:document
            xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">

            <w:body>
                <w:p w:rsidR="11111111">
                    <w:r>
                        <w:t>Test</w:t>
                    </w:r>
                </w:p>
            </w:body>

        </w:document>
        """

        root = self.parser.parse(xml)

        result = self.extractor.extract_document_rsids(
            root
        )

        self.assertEqual(
            len(result),
            1
        )

        self.assertEqual(
            result[0]["attribute"],
            "rsidR"
        )

        self.assertEqual(
            result[0]["value"],
            "11111111"
        )

    def test_extract_multiple_document_rsids(self):

        xml = b"""
        <w:document
            xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">

            <w:body>

                <w:p
                    w:rsidR="11111111"
                    w:rsidRPr="22222222">

                    <w:r
                        w:rsidDel="33333333">
                        <w:t>Test</w:t>
                    </w:r>

                </w:p>

            </w:body>

        </w:document>
        """

        root = self.parser.parse(xml)

        result = self.extractor.extract_document_rsids(
            root
        )

        self.assertEqual(
            len(result),
            3
        )

        values = [
            item["value"]
            for item in result
        ]

        self.assertIn(
            "11111111",
            values
        )

        self.assertIn(
            "22222222",
            values
        )

        self.assertIn(
            "33333333",
            values
        )

    def test_no_document_rsids_returns_empty_list(self):

        xml = b"""
        <w:document
            xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">

            <w:body>
                <w:p>
                    <w:r>
                        <w:t>Test</w:t>
                    </w:r>
                </w:p>
            </w:body>

        </w:document>
        """

        root = self.parser.parse(xml)

        result = self.extractor.extract_document_rsids(
            root
        )

        self.assertEqual(
            result,
            []
        )

    def test_unrelated_attributes_are_ignored(self):

        xml = b"""
        <w:document
            xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">

            <w:body>
                <w:p
                    w:rsidR="11111111"
                    w:customAttribute="IGNORE_ME">
                </w:p>
            </w:body>

        </w:document>
        """

        root = self.parser.parse(xml)

        result = self.extractor.extract_document_rsids(
            root
        )

        self.assertEqual(
            len(result),
            1
        )

        self.assertEqual(
            result[0]["attribute"],
            "rsidR"
        )

    # -----------------------------------------------------
    # Revision tests
    # -----------------------------------------------------

    def test_extract_insertion_revision(self):

        xml = b"""
        <w:document
            xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">

            <w:body>
                <w:p>

                    <w:ins
                        w:author="Test User"
                        w:date="2026-09-05T10:00:00Z">

                        <w:r>
                            <w:t>Inserted text</w:t>
                        </w:r>

                    </w:ins>

                </w:p>
            </w:body>

        </w:document>
        """

        root = self.parser.parse(xml)

        result = self.extractor.extract_revisions(
            root
        )

        self.assertEqual(
            len(result),
            1
        )

        self.assertEqual(
            result[0]["type"],
            "insertion"
        )

        self.assertEqual(
            result[0]["author"],
            "Test User"
        )

        self.assertEqual(
            result[0]["date"],
            "2026-09-05T10:00:00Z"
        )

        self.assertEqual(
            result[0]["text"],
            "Inserted text"
        )

    def test_extract_deletion_revision(self):

        xml = b"""
        <w:document
            xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">

            <w:body>
                <w:p>

                    <w:del
                        w:author="Test User"
                        w:date="2026-09-05T11:00:00Z">

                        <w:r>
                            <w:delText>
                                Deleted text
                            </w:delText>
                        </w:r>

                    </w:del>

                </w:p>
            </w:body>

        </w:document>
        """

        root = self.parser.parse(xml)

        result = self.extractor.extract_revisions(
            root
        )

        self.assertEqual(
            len(result),
            1
        )

        self.assertEqual(
            result[0]["type"],
            "deletion"
        )

        self.assertEqual(
            result[0]["author"],
            "Test User"
        )

        self.assertEqual(
            result[0]["date"],
            "2026-09-05T11:00:00Z"
        )

        self.assertEqual(
            result[0]["text"].strip(),
            "Deleted text"
        )

    def test_extract_multiple_revisions(self):

        xml = b"""
        <w:document
            xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">

            <w:body>
                <w:p>

                    <w:ins
                        w:author="User A"
                        w:date="2026-09-05T10:00:00Z">

                        <w:r>
                            <w:t>New</w:t>
                        </w:r>

                    </w:ins>

                    <w:del
                        w:author="User B"
                        w:date="2026-09-05T11:00:00Z">

                        <w:r>
                            <w:delText>Old</w:delText>
                        </w:r>

                    </w:del>

                </w:p>
            </w:body>

        </w:document>
        """

        root = self.parser.parse(xml)

        result = self.extractor.extract_revisions(
            root
        )

        self.assertEqual(
            len(result),
            2
        )

        types = [
            revision["type"]
            for revision in result
        ]

        self.assertIn(
            "insertion",
            types
        )

        self.assertIn(
            "deletion",
            types
        )

    def test_revision_without_author_or_date(self):

        xml = b"""
        <w:document
            xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">

            <w:body>
                <w:p>

                    <w:ins>
                        <w:r>
                            <w:t>Inserted</w:t>
                        </w:r>
                    </w:ins>

                </w:p>
            </w:body>

        </w:document>
        """

        root = self.parser.parse(xml)

        result = self.extractor.extract_revisions(
            root
        )

        self.assertEqual(
            len(result),
            1
        )

        self.assertIsNone(
            result[0]["author"]
        )

        self.assertIsNone(
            result[0]["date"]
        )

    def test_no_revisions_returns_empty_list(self):

        xml = b"""
        <w:document
            xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">

            <w:body>
                <w:p>
                    <w:r>
                        <w:t>Normal text</w:t>
                    </w:r>
                </w:p>
            </w:body>

        </w:document>
        """

        root = self.parser.parse(xml)

        result = self.extractor.extract_revisions(
            root
        )

        self.assertEqual(
            result,
            []
        )

    # -----------------------------------------------------
    # Core property tests
    # -----------------------------------------------------

    # -----------------------------------------------------
    # Word-native revision structures
    # -----------------------------------------------------

    WORD_NATIVE_XML = b"""
    <w:document
        xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:body>
        <w:p w:rsidR="00AA0001" w:rsidRDefault="00AA0002">
          <w:pPr>
            <w:rPr>
              <w:ins w:id="10" w:author="Editor" w:date="2026-09-28T10:00:00Z"/>
            </w:rPr>
          </w:pPr>
          <w:ins w:id="11" w:author="Editor" w:date="2026-09-28T10:01:00Z">
            <w:r><w:t>red</w:t></w:r>
          </w:ins>
          <w:del w:id="12" w:author="Editor" w:date="2026-09-28T10:01:00Z">
            <w:r><w:delText>brown</w:delText></w:r>
          </w:del>
          <w:r>
            <w:rPr>
              <w:b/>
              <w:rPrChange w:id="13" w:author="Editor" w:date="2026-09-28T10:02:00Z">
                <w:rPr/>
              </w:rPrChange>
            </w:rPr>
            <w:t>fox</w:t>
          </w:r>
          <w:moveTo w:id="14" w:author="Editor" w:date="2026-09-28T10:03:00Z">
            <w:r><w:t>moved</w:t></w:r>
          </w:moveTo>
        </w:p>
      </w:body>
    </w:document>
    """

    def test_paragraph_mark_revision_not_counted_as_insertion(self):

        root = self.parser.parse(self.WORD_NATIVE_XML)
        result = self.extractor.extract_revisions(root)

        types = [r["type"] for r in result]

        self.assertEqual(types.count("insertion"), 1)
        self.assertEqual(types.count("deletion"), 1)
        self.assertEqual(types.count("paragraph_mark_insertion"), 1)

    def test_formatting_and_move_revisions_extracted(self):

        root = self.parser.parse(self.WORD_NATIVE_XML)
        result = self.extractor.extract_revisions(root)

        by_type = {r["type"]: r for r in result}

        self.assertIn("formatting_change", by_type)
        self.assertEqual(by_type["move_to"]["text"], "moved")
        self.assertEqual(
            by_type["formatting_change"]["element"], "w:rPrChange"
        )

    def test_revision_records_are_traceable(self):

        root = self.parser.parse(self.WORD_NATIVE_XML)
        result = self.extractor.extract_revisions(root)

        insertion = next(r for r in result if r["type"] == "insertion")

        self.assertEqual(insertion["part"], "word/document.xml")
        self.assertEqual(insertion["element"], "w:ins")
        self.assertEqual(insertion["revision_id"], "11")
        self.assertEqual(insertion["text"], "red")

    def test_rsid_r_default_is_extracted(self):

        root = self.parser.parse(self.WORD_NATIVE_XML)
        result = self.extractor.extract_document_rsids(root)

        attributes = {item["attribute"] for item in result}

        self.assertIn("rsidRDefault", attributes)
        self.assertTrue(
            all(item["part"] == "word/document.xml" for item in result)
        )

    def test_extract_core_properties(self):

        xml = b"""
        <cp:coreProperties
            xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:dcterms="http://purl.org/dc/terms/">

            <dc:creator>Thabang</dc:creator>

            <cp:lastModifiedBy>
                Test Editor
            </cp:lastModifiedBy>

            <dcterms:created>
                2026-09-01T10:00:00Z
            </dcterms:created>

            <dcterms:modified>
                2026-09-05T12:00:00Z
            </dcterms:modified>

        </cp:coreProperties>
        """

        root = self.parser.parse(xml)

        result = (
            self.extractor.extract_core_properties(
                root
            )
        )

        self.assertEqual(
            result["creator"],
            "Thabang"
        )

        self.assertEqual(
            result["last_modified_by"].strip(),
            "Test Editor"
        )

        self.assertEqual(
            result["created"].strip(),
            "2026-09-01T10:00:00Z"
        )

        self.assertEqual(
            result["modified"].strip(),
            "2026-09-05T12:00:00Z"
        )

    def test_missing_core_properties_return_none(self):

        xml = b"""
        <cp:coreProperties
            xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:dcterms="http://purl.org/dc/terms/">
        </cp:coreProperties>
        """

        root = self.parser.parse(xml)

        result = (
            self.extractor.extract_core_properties(
                root
            )
        )

        self.assertIsNone(
            result["creator"]
        )

        self.assertIsNone(
            result["last_modified_by"]
        )

        self.assertIsNone(
            result["created"]
        )

        self.assertIsNone(
            result["modified"]
        )

    # -----------------------------------------------------
    # Application property tests
    # -----------------------------------------------------

    def test_extract_application_properties(self):

        xml = b"""
        <Properties
            xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">

            <Application>
                Microsoft Office Word
            </Application>

            <AppVersion>
                16.0000
            </AppVersion>

        </Properties>
        """

        root = self.parser.parse(xml)

        result = (
            self.extractor.extract_application_properties(
                root
            )
        )

        self.assertEqual(
            result["application"].strip(),
            "Microsoft Office Word"
        )

        self.assertEqual(
            result["app_version"].strip(),
            "16.0000"
        )

    def test_missing_application_properties_return_none(
        self
    ):

        xml = b"""
        <Properties
            xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
        </Properties>
        """

        root = self.parser.parse(xml)

        result = (
            self.extractor.extract_application_properties(
                root
            )
        )

        self.assertIsNone(
            result["application"]
        )

        self.assertIsNone(
            result["app_version"]
        )


if __name__ == "__main__":
    unittest.main()