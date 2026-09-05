from pathlib import Path

from package_reader import DocxPackageReader
from xml_parser import TargetXmlParser


def main():
    print("DOCX Edit-Trail Analyser")
    print("-" * 40)

    project_root = Path(__file__).resolve().parent.parent
    file_path = project_root / "samples" / "test.docx"

    try:
        reader = DocxPackageReader(file_path)
        parts = reader.read_selected_parts()

        parser = TargetXmlParser()

        for part_name, content in parts.items():

            if content is None:
                print(f"[MISSING] {part_name}")
                continue

            root = parser.parse(content)

            print(
                f"[PARSED] {part_name} "
                f"(root: {root.tag})"
            )

            if part_name == "word/document.xml":
                body = parser.find(root, ".//w:body")

                if body is not None:
                    print("[FOUND] Word document body")
                else:
                    print("[NOT FOUND] Word document body")

        return 0

    except (FileNotFoundError, ValueError) as error:
        print(f"[ERROR] {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())