import zipfile
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_DOCX_PART = "word/document.xml"


# =========================================================
# File validation
# =========================================================

def validate_docx_file(file_path):
    
    # Confirm that a path points to a readable DOCX package.
    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError(
            f"The file does not exist, please check path/file: {file_path}"
        )

    if file_path.suffix.lower() != ".docx":
        raise ValueError(
            "The selected file must be a DOCX file."
        )
        
    # Checking if the docx is a valid zip
    if not zipfile.is_zipfile(file_path):
        raise ValueError(
            f"The file has a .docx extension but is not a valid "
            f"DOCX (ZIP) package: {file_path}"
        )

    with zipfile.ZipFile(file_path) as package:
        if REQUIRED_DOCX_PART not in package.namelist():
            raise ValueError(
                f"The DOCX package is missing {REQUIRED_DOCX_PART}: "
                f"{file_path}"
            )

    return file_path


# =========================================================
# XML helpers
# =========================================================

# Strip a Clark-notation namespace: '{uri}rPr' -> 'rPr'.
def local_name(tag):
    
    if not isinstance(tag, str):
        return None

    return tag.split("}", 1)[1] if "}" in tag else tag


# =========================================================
# Value helpers
# =========================================================

def clean_text(value):
    
    #Strip whitespace; return None for missing or blank values.
    if value is None:
        return None

    value = value.strip()

    return value or None


def parse_timestamp(value):
    
    #Parse an OOXML W3CDTF timestamp into a timezone-aware datetime.
    #values are treated as UTC so that any two parsed imestamps can be compared safely.
    # Returns None when the value is missing or unparseable.

    value = clean_text(value)

    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed

def format_metric(value, decimals=2):

    if value is None:
        return "n/a"

    return f"{value:.{decimals}f}"