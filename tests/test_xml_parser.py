import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from xml_parser import TargetXmlParser


class TestTargetXmlParser(unittest.TestCase):

    def setUp(self):
        self.parser = TargetXmlParser()

    def test_valid_xml_can_be_parsed(self):
        xml_content = b"""
        <root>
            <child>Test</child>
        </root>
        """

        root = self.parser.parse(xml_content)

        self.assertEqual(root.tag, "root")

    def test_missing_xml_raises_error(self):
        with self.assertRaises(ValueError):
            self.parser.parse(None)

    def test_empty_xml_raises_error(self):
        with self.assertRaises(ValueError):
            self.parser.parse(b"")

    def test_malformed_xml_raises_error(self):
        malformed_xml = b"""
        <root>
            <child>
        </root>
        """

        with self.assertRaises(ValueError):
            self.parser.parse(malformed_xml)

    def test_word_namespace_lookup(self):
        xml_content = b"""
        <w:document
            xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">

            <w:body>
                <w:p>
                    <w:r>
                        <w:t>Test document</w:t>
                    </w:r>
                </w:p>
            </w:body>

        </w:document>
        """

        root = self.parser.parse(xml_content)

        body = self.parser.find(
            root,
            ".//w:body"
        )

        self.assertIsNotNone(body)

    def test_find_all_returns_multiple_elements(self):
        xml_content = b"""
        <w:document
            xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">

            <w:body>
                <w:p />
                <w:p />
                <w:p />
            </w:body>

        </w:document>
        """

        root = self.parser.parse(xml_content)

        paragraphs = self.parser.find_all(
            root,
            ".//w:p"
        )

        self.assertEqual(len(paragraphs), 3)

    def test_missing_element_returns_none(self):
        xml_content = b"""
        <w:document
            xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">

            <w:body />

        </w:document>
        """

        root = self.parser.parse(xml_content)

        result = self.parser.find(
            root,
            ".//w:tbl"
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()