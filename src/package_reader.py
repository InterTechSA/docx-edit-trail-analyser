from pathlib import Path
from zipfile import ZipFile, BadZipFile

from helpers.constants import TARGET_PARTS
from helpers.helper_functions import validate_docx_file

from xml_parser import TargetXmlParser


class DocxPackageReader:

    def __init__(self, file_path):
        self.file_path = Path(file_path)

    def read_selected_parts(self):
        
        # Validate the file path and ensure it is a valid DOCX file
        validate_docx_file(self.file_path)

        parts = {}

        try:
            with ZipFile(self.file_path, "r") as docx_package:
                
                available_parts = set(docx_package.namelist())
                
                for part_name in TARGET_PARTS:
                    if part_name in available_parts:
                        parts[part_name] = docx_package.read(part_name)
                    else:
                        parts[part_name] = None

        except BadZipFile as error:
            raise ValueError(
                "The file has a .docx extension but is not a valid ZIP/OOXML package."
            ) from error

        return parts