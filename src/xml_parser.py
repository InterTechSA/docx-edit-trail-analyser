import defusedxml.ElementTree as ET

from helpers.constants import NAMESPACES

class TargetXmlParser:

    def parse(self, xml_content):
        
        if xml_content is None:
            raise ValueError("No XML content found.")

        if not xml_content:
            raise ValueError("XML content empty.")

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