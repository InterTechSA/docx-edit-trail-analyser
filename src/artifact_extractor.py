from xml_parser import NAMESPACES


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

# Tracked formatting-change elements (ECMA-376 Part 1, 17.13.5).
FORMATTING_CHANGE_ELEMENTS = (
    "rPrChange",
    "pPrChange",
    "sectPrChange",
    "tblPrChange",
    "trPrChange",
    "tcPrChange",
)

# Revision types that represent retained *content* changes.
CONTENT_REVISION_TYPES = frozenset({
    "insertion",
    "deletion",
    "move_from",
    "move_to",
})


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

    def extract_revisions(self, document_root):
        """
        Extract retained tracked-revision markup from
        word/document.xml.

        Word stores tracked changes in several structures, not
        only as run-level w:ins / w:del. Each record is given a
        precise type so that counts stay meaningful:

            insertion / deletion
                Content revisions: w:ins / w:del that wrap runs
                of text. These are what a reader would call a
                "tracked insertion" or "tracked deletion", and
                they are the only types the ground truth counts
                as retained insertions / deletions.

            paragraph_mark_insertion / paragraph_mark_deletion
                w:ins / w:del inside w:pPr/w:rPr. Word writes one
                every time a paragraph break is inserted or
                removed with Track Changes on. They carry no text,
                so counting them as insertions would inflate the
                insertion count on Word-native files.

            table_row_insertion / table_row_deletion
                w:ins / w:del inside w:trPr.

            move_from / move_to
                w:moveFrom / w:moveTo (tracked moves).

            formatting_change
                w:rPrChange, w:pPrChange, w:sectPrChange,
                w:tblPrChange, w:trPrChange, w:tcPrChange
                (tracked formatting changes).

        Every record also carries traceability fields (part,
        element, revision_id) so an investigator can locate the
        exact XML that produced it.

        Returns:
            list[dict]: Revision evidence records containing
            type, author, date, text, part, element, revision_id.
        """

        parent_map = {
            child: parent
            for parent in document_root.iter()
            for child in parent
        }

        revisions = []

        # Content insertions first, then content deletions, then
        # every other retained marker. The ordering is kept
        # stable so existing reports and tests remain comparable.
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

    def _extract_revision_text(
        self,
        revision_element,
        revision_type
    ):
        """
        Extract text associated with a retained revision.

        Insertions and move destinations normally use w:t.
        Deletions normally use w:delText. Move sources may use
        either, depending on the producing application.

        Returns:
            str | None
        """

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