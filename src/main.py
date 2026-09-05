import sys
from pathlib import Path

from package_reader import DocxPackageReader
from xml_parser import TargetXmlParser
from artifact_extractor import ArtifactExtractor
from correlation_engine import CorrelationEngine


def main():

    print("DOCX Edit-Trail Analyser")
    print("-" * 40)

    project_root = Path(__file__).resolve().parent.parent

    # -------------------------------------------------
    # Select DOCX file
    # -------------------------------------------------

    if len(sys.argv) > 1:

        file_path = Path(sys.argv[1])

    else:

        file_path = (
            project_root
            / "samples"
            / "test.docx"
        )

    print(
        f"Analysing: {file_path}"
    )

    try:

        reader = DocxPackageReader(file_path)

        parts = reader.read_selected_parts()

        parser = TargetXmlParser()

        extractor = ArtifactExtractor()

        correlation_engine = CorrelationEngine()

        parsed_parts = {}

        # -------------------------------------------------
        # Parse selected XML parts
        # -------------------------------------------------

        for part_name, content in parts.items():

            if content is None:

                print(
                    f"[MISSING] {part_name}"
                )

                continue

            root = parser.parse(content)

            parsed_parts[part_name] = root

            print(
                f"[PARSED] {part_name}"
            )

        # -------------------------------------------------
        # Prepare evidence containers
        # -------------------------------------------------

        rsid_root = None

        rsid_table = []

        document_rsids = []

        revisions = []

        core_properties = {}

        app_properties = {}

        # -------------------------------------------------
        # RSID evidence
        # -------------------------------------------------

        settings_root = parsed_parts.get(
            "word/settings.xml"
        )

        if settings_root is not None:

            rsid_root = extractor.extract_rsid_root(
                settings_root
            )

            rsid_table = extractor.extract_rsid_table(
                settings_root
            )

            print()

            print("RSID Evidence")

            print("-" * 40)

            print(
                f"rsidRoot: {rsid_root}"
            )

            print(
                f"RSID table entries: "
                f"{len(rsid_table)}"
            )

            for rsid in rsid_table:

                print(
                    f"  - {rsid}"
                )

        # -------------------------------------------------
        # Document evidence
        # -------------------------------------------------

        document_root = parsed_parts.get(
            "word/document.xml"
        )

        if document_root is not None:

            document_rsids = (
                extractor.extract_document_rsids(
                    document_root
                )
            )

            print()

            print("Document RSID Attributes")

            print("-" * 40)

            print(
                f"RSID attributes found: "
                f"{len(document_rsids)}"
            )

            for item in document_rsids:

                print(
                    f"{item['attribute']} = "
                    f"{item['value']} "
                    f"on {item['element']}"
                )

            # ---------------------------------------------
            # Retained revisions
            # ---------------------------------------------

            revisions = (
                extractor.extract_revisions(
                    document_root
                )
            )

            print()

            print("Retained Revision Evidence")

            print("-" * 40)

            print(
                f"Revisions found: "
                f"{len(revisions)}"
            )

            for revision in revisions:

                print(
                    f"Type: "
                    f"{revision['type']}"
                )

                print(
                    f"Author: "
                    f"{revision['author']}"
                )

                print(
                    f"Date: "
                    f"{revision['date']}"
                )

                print(
                    f"Text: "
                    f"{revision['text']}"
                )

                print(
                    "-" * 20
                )

        # -------------------------------------------------
        # Core document properties
        # -------------------------------------------------

        core_root = parsed_parts.get(
            "docProps/core.xml"
        )

        if core_root is not None:

            core_properties = (
                extractor.extract_core_properties(
                    core_root
                )
            )

            print()

            print("Core Document Properties")

            print("-" * 40)

            print(
                f"Creator: "
                f"{core_properties['creator']}"
            )

            print(
                f"Last modified by: "
                f"{core_properties['last_modified_by']}"
            )

            print(
                f"Created: "
                f"{core_properties['created']}"
            )

            print(
                f"Modified: "
                f"{core_properties['modified']}"
            )

        # -------------------------------------------------
        # Application properties
        # -------------------------------------------------

        app_root = parsed_parts.get(
            "docProps/app.xml"
        )

        if app_root is not None:

            app_properties = (
                extractor.extract_application_properties(
                    app_root
                )
            )

            print()

            print("Application Properties")

            print("-" * 40)

            print(
                f"Application: "
                f"{app_properties['application']}"
            )

            print(
                f"Application version: "
                f"{app_properties['app_version']}"
            )

        # -------------------------------------------------
        # Correlation engine
        # -------------------------------------------------

        classification = (
            correlation_engine.classify(
                rsid_root=rsid_root,
                rsid_table=rsid_table,
                document_rsids=document_rsids,
                revisions=revisions,
                core_properties=core_properties,
                app_properties=app_properties,
            )
        )

        print()

        print("Evidence Classification")

        print("-" * 40)

        print(
            f"Category: "
            f"{classification['category']}"
        )

        print()

        print("Basis:")

        for item in classification["basis"]:

            print(
                f"  - {item}"
            )

        print()

        print("Interpretive Limitations:")

        for item in classification["limitations"]:

            print(
                f"  - {item}"
            )

        return 0

    except (FileNotFoundError, ValueError) as error:

        print(
            f"[ERROR] {error}"
        )

        return 1


if __name__ == "__main__":

    raise SystemExit(main())
