from helpers.constants import NAMESPACES
from helpers.constants import RSID_ATTRIBUTE_NAMES
from helpers.constants import FORMATTING_CHANGE_ELEMENTS
from helpers.constants import RSID_ROOT_PATH


class ArtifactExtractor:

    # Extract the rsidRoot value from word/settings.xml.
    def extract_rsid_root(self, settings_root):

        rsid_root = settings_root.find(
            RSID_ROOT_PATH,
            NAMESPACES
        )
        
        if rsid_root is None:
            return None

        return rsid_root.get(
            f"{{{NAMESPACES['w']}}}val"
        )
                
    # Extract all RSID values from the RSID table from word/settings.xml.
    def extract_rsid_table(self, settings_root):

        rsid_elements = settings_root.findall(
            ".//w:rsids/w:rsid",
            NAMESPACES
        )

        rsids = []

        for element in rsid_elements:
            value = element.get(
                f"{{{NAMESPACES['w']}}}val"
            )

            if value is not None:
                rsids.append(value)

        return rsids

    # Extract RSID-related attributes from word/document.xml.
    def extract_document_rsids(self, document_root):
        
        rsid_attribute_names = RSID_ATTRIBUTE_NAMES

        results = []

        word_namespace = NAMESPACES["w"]

        for element in document_root.iter():

            for attribute_name, value in element.attrib.items():

                if not attribute_name.startswith(
                    f"{{{word_namespace}}}"
                ):
                    continue

                local_name = attribute_name.split("}", 1)[1]

                if local_name in rsid_attribute_names:
                    results.append({
                        "element": element.tag,
                        "attribute": local_name,
                        "value": value,
                        "part": "word/document.xml",
                    })

        return results
    
    # Extract retained tracked-revision markup from word/document.xml
    def extract_revisions(self, document_root):

        parent_map = {
            child: parent
            for parent in document_root.iter()
            for child in parent
        }

        revisions = []

        ordered_groups = [
            ("ins", "insertion"),
            ("del", "deletion"),
        ]

        deferred = []

        for local_name, base_type in ordered_groups:

            for element in document_root.iter(
                self._w(local_name)
            ):

                context = self._local_name(
                    parent_map.get(element)
                )

                if context == "rPr":
                    deferred.append(
                        self._revision_record(
                            element,
                            f"paragraph_mark_{base_type}",
                            local_name,
                            text=None,
                        )
                    )
                    continue

                if context == "trPr":
                    deferred.append(
                        self._revision_record(
                            element,
                            f"table_row_{base_type}",
                            local_name,
                            text=None,
                        )
                    )
                    continue

                revisions.append(
                    self._revision_record(
                        element,
                        base_type,
                        local_name,
                        text=self._extract_revision_text(
                            element,
                            base_type,
                        ),
                    )
                )

        for local_name, revision_type in (
            ("moveFrom", "move_from"),
            ("moveTo", "move_to"),
        ):

            for element in document_root.iter(
                self._w(local_name)
            ):
                deferred.append(
                    self._revision_record(
                        element,
                        revision_type,
                        local_name,
                        text=self._extract_revision_text(
                            element,
                            revision_type,
                        ),
                    )
                )

        for local_name in FORMATTING_CHANGE_ELEMENTS:

            for element in document_root.iter(
                self._w(local_name)
            ):
                deferred.append(
                    self._revision_record(
                        element,
                        "formatting_change",
                        local_name,
                        text=None,
                    )
                )

        return revisions + deferred

    def _revision_record(
        self,
        element,
        revision_type,
        local_name,
        text,
    ):

        return {
            "type": revision_type,
            "author": element.get(self._w("author")),
            "date": element.get(self._w("date")),
            "text": text,
            "part": "word/document.xml",
            "element": f"w:{local_name}",
            "revision_id": element.get(self._w("id")),
        }

    def _w(self, local_name):
        return f"{{{NAMESPACES['w']}}}{local_name}"

    def _local_name(self, element):

        if element is None:
            return None

        tag = element.tag

        if "}" in tag:
            return tag.split("}", 1)[1]

        return tag

    # Extract text associated with a retained revision.
    def _extract_revision_text(
        self,
        revision_element,
        revision_type
    ):

        if revision_type in ("insertion", "move_to"):
            text_elements = revision_element.findall(
                ".//w:t",
                NAMESPACES
            )

        elif revision_type == "deletion":
            text_elements = revision_element.findall(
                ".//w:delText",
                NAMESPACES
            )

        elif revision_type == "move_from":
            text_elements = (
                revision_element.findall(".//w:t", NAMESPACES)
                + revision_element.findall(
                    ".//w:delText", NAMESPACES
                )
            )

        else:
            return None

        text_parts = []

        for element in text_elements:

            if element.text:
                text_parts.append(element.text)

        if not text_parts:
            return None

        return "".join(text_parts)

    # Extract selected core document properties from docProps/core.xml.
    def extract_core_properties(self, core_root):

        creator = core_root.find(
            "dc:creator",
            NAMESPACES
        )

        last_modified_by = core_root.find(
            "cp:lastModifiedBy",
            NAMESPACES
        )

        created = core_root.find(
            "dcterms:created",
            NAMESPACES
        )

        modified = core_root.find(
            "dcterms:modified",
            NAMESPACES
        )

        return {
            "creator": self._element_text(creator),
            "last_modified_by": self._element_text(
                last_modified_by
            ),
            "created": self._element_text(created),
            "modified": self._element_text(modified),
        }

    # Extract selected application properties from docProps/app.xml.
    def extract_application_properties(self, app_root):

        application = app_root.find(
            "ep:Application",
            NAMESPACES
        )

        app_version = app_root.find(
            "ep:AppVersion",
            NAMESPACES
        )

        return {
            "application": self._element_text(application),
            "app_version": self._element_text(app_version),
        }

    def _element_text(self, element):

        if element is None:
            return None

        return element.text