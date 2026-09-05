from xml_parser import NAMESPACES


class ArtifactExtractor:

    def extract_rsid_root(self, settings_root):
        """
        Extract the rsidRoot value from word/settings.xml.

        Returns:
            str | None: The rsidRoot value if present.
        """

        rsid_root = settings_root.find(
            ".//w:rsids/w:rsidRoot",
            NAMESPACES
        )

        if rsid_root is None:
            return None

        return rsid_root.get(
            f"{{{NAMESPACES['w']}}}val"
        )

    def extract_rsid_table(self, settings_root):
        """
        Extract all RSID values from the RSID table
        in word/settings.xml.

        Returns:
            list[str]: RSID values found in the table.
        """

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

    def extract_document_rsids(self, document_root):
        """
        Extract RSID-related attributes from word/document.xml.

        Returns:
            list[dict]: RSID evidence records.
        """

        rsid_attribute_names = {
            "rsidR",
            "rsidRPr",
            "rsidDel",
            "rsidP",
            "rsidSect",
        }

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
                    })

        return results

    def extract_revisions(self, document_root):
        """
        Extract retained tracked revisions from word/document.xml.

        Looks for:
            w:ins
            w:del

        Returns:
            list[dict]: Revision evidence records containing
            type, author, date, and text where available.
        """

        revisions = []

        revision_types = {
            "insertion": ".//w:ins",
            "deletion": ".//w:del",
        }

        word_namespace = NAMESPACES["w"]

        author_attribute = f"{{{word_namespace}}}author"
        date_attribute = f"{{{word_namespace}}}date"

        for revision_type, path in revision_types.items():

            revision_elements = document_root.findall(
                path,
                NAMESPACES
            )

            for element in revision_elements:

                author = element.get(author_attribute)
                date = element.get(date_attribute)

                text = self._extract_revision_text(
                    element,
                    revision_type
                )

                revisions.append({
                    "type": revision_type,
                    "author": author,
                    "date": date,
                    "text": text,
                })

        return revisions

    def _extract_revision_text(
        self,
        revision_element,
        revision_type
    ):
        """
        Extract text associated with a retained revision.

        Insertions normally use w:t.
        Deletions normally use w:delText.

        Returns:
            str | None
        """

        if revision_type == "insertion":
            text_elements = revision_element.findall(
                ".//w:t",
                NAMESPACES
            )

        elif revision_type == "deletion":
            text_elements = revision_element.findall(
                ".//w:delText",
                NAMESPACES
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

    def extract_core_properties(self, core_root):
        """
        Extract selected core document properties
        from docProps/core.xml.

        Returns:
            dict: Core property values.
        """

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

    def extract_application_properties(self, app_root):
        """
        Extract selected application properties
        from docProps/app.xml.

        Returns:
            dict: Application property values.
        """

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
        """
        Return the text of an XML element.

        Returns:
            str | None
        """

        if element is None:
            return None

        return element.text