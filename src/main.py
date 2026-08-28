from pathlib import Path

from package_reader import DocxPackageReader


def main():
    print("DOCX Edit-Trail Analyser")
    print("-" * 40)

    project_root = Path(__file__).resolve().parent.parent
    file_path = project_root / "samples" / "test.docx"

    try:
        reader = DocxPackageReader(file_path)
        parts = reader.read_selected_parts()

        for part_name, content in parts.items():
            if content is None:
                print(f"[MISSING] {part_name}")
            else:
                print(f"[FOUND]   {part_name} ({len(content)} bytes)")

    except FileNotFoundError as error:
        print(f"[ERROR] {error}")
        print("Analysis could not be completed.")

    except ValueError as error:
        print(f"[ERROR] {error}")
        print("Analysis could not be completed.")


if __name__ == "__main__":
    main()