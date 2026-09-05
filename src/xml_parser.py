import xml.etree.ElementTree as ET


NAMESPACES = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
}


class TargetXmlParser:

    def parse(self, xml_content):
        if xml_content is None:
            raise ValueError("XML content is missing.")

        if not xml_content:
            raise ValueError("XML content is empty.")

        try:
            return ET.fromstring(xml_content)

        except ET.ParseError as error:
            raise ValueError(
                f"Unable to parse XML content: {error}"
            ) from error

    def find(self, root, path):
        return root.find(path, NAMESPACES)

    def find_all(self, root, path):
        return root.findall(path, NAMESPACES)