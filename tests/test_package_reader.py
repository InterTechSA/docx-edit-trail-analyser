import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from package_reader import DocxPackageReader


class TestDocxPackageReader(unittest.TestCase):

    def test_missing_file_raises_error(self):
        reader = DocxPackageReader("file_that_does_not_exist.docx")

        with self.assertRaises(FileNotFoundError):
            reader.read_selected_parts()

    def test_wrong_extension_raises_error(self):
        with tempfile.NamedTemporaryFile(suffix=".txt") as temp_file:
            reader = DocxPackageReader(temp_file.name)

            with self.assertRaises(ValueError):
                reader.read_selected_parts()

    def test_invalid_docx_package_raises_error(self):
        with tempfile.NamedTemporaryFile(
            suffix=".docx",
            delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"This is not a valid DOCX file.")

        try:
            reader = DocxPackageReader(temp_path)

            with self.assertRaises(ValueError):
                reader.read_selected_parts()

        finally:
            temp_path.unlink(missing_ok=True)

    def test_valid_docx_returns_selected_parts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = Path(temp_dir) / "test.docx"

            with ZipFile(docx_path, "w") as package:
                package.writestr(
                    "word/document.xml",
                    "<document />"
                )
                package.writestr(
                    "word/settings.xml",
                    "<settings />"
                )
                package.writestr(
                    "docProps/core.xml",
                    "<coreProperties />"
                )
                package.writestr(
                    "docProps/app.xml",
                    "<Properties />"
                )

            reader = DocxPackageReader(docx_path)
            parts = reader.read_selected_parts()

            self.assertIn("word/document.xml", parts)
            self.assertIn("word/settings.xml", parts)
            self.assertIn("docProps/core.xml", parts)
            self.assertIn("docProps/app.xml", parts)

            self.assertIsNotNone(
                parts["word/document.xml"]
            )

    def test_missing_optional_part_returns_none(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = Path(temp_dir) / "test.docx"

            with ZipFile(docx_path, "w") as package:
                package.writestr(
                    "word/document.xml",
                    "<document />"
                )

            reader = DocxPackageReader(docx_path)
            parts = reader.read_selected_parts()

            self.assertIsNotNone(
                parts["word/document.xml"]
            )

            self.assertIsNone(
                parts["word/settings.xml"]
            )

            self.assertIsNone(
                parts["docProps/core.xml"]
            )

            self.assertIsNone(
                parts["docProps/app.xml"]
            )


if __name__ == "__main__":
    unittest.main()