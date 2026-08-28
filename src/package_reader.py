from pathlib import Path
from zipfile import ZipFile, BadZipFile


TARGET_PARTS = [
    "word/document.xml",
    "word/settings.xml",
    "docProps/core.xml",
    "docProps/app.xml",
]

class DocxPackageReader:
    def __init__(self, file_path):
        self.file_path = Path(file_path)

    def validate_file(self):
        if not self.file_path.exists():
            raise FileNotFoundError(
                f"File does not exist: {self.file_path}"
            )

        if self.file_path.suffix.lower() != ".docx":
            raise ValueError(
                "The selected file must be a DOCX file."
            )

    def read_selected_parts(self):
        self.validate_file()

        parts = {}

        try:
            with ZipFile(self.file_path, "r") as docx_package:
                available_parts = set(docx_package.namelist())

                for part_name in TARGET_PARTS:
                    if part_name in available_parts:
                        parts[part_name] = docx_package.read(part_name)
                    else:
                        parts[part_name] = None

        except BadZipFile:
            raise ValueError(
                "The file has a .docx extension but is not a valid ZIP/OOXML package."
            )

        return parts