TARGET_PARTS = [
    "word/document.xml",
    "word/settings.xml",
    "docProps/core.xml",
    "docProps/app.xml",
]

NAMESPACES = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
}

# RSID attributes examined in word/document.xml.
#   rsidR        paragraph / run / section added
#   rsidRDefault default RSID for runs in a paragraph (Word writes
#                this on almost every paragraph, so omitting it
#                under-reports RSID evidence on Word-native files)
#   rsidRPr      run properties last modified
#   rsidDel      paragraph mark / run deleted
#   rsidP        paragraph properties last modified
#   rsidSect     section properties
#   rsidTr       table row properties

RSID_ATTRIBUTE_NAMES = frozenset({
    "rsidR",
    "rsidRDefault",
    "rsidRPr",
    "rsidDel",
    "rsidP",
    "rsidSect",
    "rsidTr",
})

FORMATTING_CHANGE_ELEMENTS = (
    "rPrChange",
    "pPrChange",
    "sectPrChange",
    "tblPrChange",
    "trPrChange",
    "tcPrChange",
)

CONTENT_REVISION_TYPES = frozenset({
    "insertion",
    "deletion",
    "move_from",
    "move_to",
})

RSID_ROOT_PATH = ".//w:rsids/w:rsidRoot"

RSID_SCOPES = ("document", "content", "all")

# Elements whose RSIDs describe section layout rather than text.
# Templates carry these into every new document.
SECTION_ELEMENTS = frozenset({"sectPr"})

CATEGORIES = [
    "retained tracked-revision evidence",
    "multiple-RSID-pattern evidence",
    "metadata-only evidence",
    "no selected edit artifact observed",
]

# Artifacts whose presence/absence is stated in the ground truth,
# mapped to (ground-truth key, revision type).
REVISION_ARTIFACTS = {
    "Retained insertions": ("retained_insertions", "insertion"),
    "Retained deletions": ("retained_deletions", "deletion"),
}