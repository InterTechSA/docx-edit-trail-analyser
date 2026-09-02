TARGET_PARTS = [
    "word/document.xml",
    "word/settings.xml",
    "docProps/core.xml",
    "docProps/app.xml",
]


def validate_file(self):
        if not self.file_path.exists():
            raise FileNotFoundError(
                f"File does not exist: {self.file_path}"
            )

        if self.file_path.suffix.lower() != ".docx":
            raise ValueError(
                "The selected file must be a DOCX file."
            )