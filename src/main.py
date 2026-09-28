"""
Command-line evidence view for one DOCX file.

Usage (from the project root):

    python src/main.py path/to/file.docx
    python src/main.py path/to/file.docx --rsid-scope content
"""

import argparse
import sys
from pathlib import Path

from correlation_engine import RSID_SCOPES
from evidence_pipeline import analyse_docx


def local_name(tag):

    return tag.split("}", 1)[1] if "}" in tag else tag


def section(title):

    print()
    print(title)
    print("-" * 40)


def main(argv=None):

    project_root = Path(__file__).resolve().parent.parent

    parser = argparse.ArgumentParser(
        description="DOCX Edit-Trail Analyser (command line)"
    )
    parser.add_argument(
        "file",
        nargs="?",
        default=str(project_root / "samples" / "test.docx"),
    )
    parser.add_argument(
        "--rsid-scope", default="document", choices=RSID_SCOPES
    )
    args = parser.parse_args(argv)

    print("DOCX Edit-Trail Analyser")
    print("-" * 40)
    print(f"Analysing: {args.file}")

    try:
        evidence = analyse_docx(args.file, args.rsid_scope)
    except (FileNotFoundError, ValueError) as error:
        print(f"[ERROR] {error}")
        return 1

    for part, content in evidence["parts"].items():
        print(f"[{'PARSED' if content is not None else 'MISSING'}] {part}")

    section("RSID Evidence (word/settings.xml)")
    print(f"rsidRoot: {evidence['rsid_root']}")
    print(f"RSID table entries: {len(evidence['rsid_table'])}")
    for rsid in evidence["rsid_table"]:
        print(f"  - {rsid}")

    section("Document RSID Attributes (word/document.xml)")
    print(f"RSID attributes found: {len(evidence['document_rsids'])}")
    print(f"Distinct RSIDs referenced: {len(evidence['referenced_rsids'])}")
    for item in evidence["document_rsids"]:
        print(
            f"  {item['attribute']} = {item['value']} "
            f"on w:{local_name(item['element'])}"
        )

    section("Retained Revision Evidence")
    print(f"Revision markers found: {len(evidence['revisions'])}")
    for revision in evidence["revisions"]:
        print(
            f"  {revision['type']:<26} {revision['element']:<12} "
            f"id={revision['revision_id']} "
            f"author={revision['author']} date={revision['date']} "
            f"text={revision['text']!r}"
        )

    section("Core Document Properties (docProps/core.xml)")
    core = evidence["core_properties"]
    print(f"Creator: {core.get('creator')}")
    print(f"Last modified by: {core.get('last_modified_by')}")
    print(f"Created: {core.get('created')}")
    print(f"Modified: {core.get('modified')}")

    section("Application Properties (docProps/app.xml)")
    app = evidence["app_properties"]
    print(f"Application: {app.get('application')}")
    print(f"Application version: {app.get('app_version')}")

    section("Evidence Profile (0 none - 3 extensive)")
    names = {
        "revision_evidence": "Retained revisions",
        "rsid_evidence": "RSID pattern",
        "metadata_evidence": "Context metadata",
    }
    for key, name in names.items():
        dimension = evidence["evidence_profile"][key]
        bar = "#" * dimension["score"] + "." * (3 - dimension["score"])
        print(
            f"  {name:<20} [{bar}] {dimension['score']} "
            f"{dimension['label']}"
        )
        print(f"      {dimension['basis']}")

    classification = evidence["classification"]

    section(
        f"Strongest Individual Pattern (RSID scope: "
        f"{classification['rsid_scope']})"
    )
    print(f"Category: {classification['category']}")

    print()
    print("Basis:")
    for item in classification["basis"]:
        print(f"  - {item}")

    print()
    print("Supporting evidence (part / element / attribute = value):")
    if not classification["evidence"]:
        print("  (none)")
    for item in classification["evidence"]:
        print(
            f"  {item['part']} / {item['element']} / "
            f"{item['attribute']} = {item['value']}"
        )

    print()
    print("Interpretive Limitations:")
    for item in classification["limitations"]:
        print(f"  - {item}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
