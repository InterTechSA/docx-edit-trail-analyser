class CorrelationEngine:
    """
    Correlates extracted DOCX artifacts into explainable
    evidence categories.

    The engine does not determine whether a document is
    authentic or forged. It only describes patterns found
    in the selected artifacts.
    """

    def classify(
        self,
        rsid_root,
        rsid_table,
        document_rsids,
        revisions,
        core_properties,
        app_properties
    ):
        """
        Classify the available evidence.

        Categories:
            - retained tracked-revision evidence
            - multiple-RSID-pattern evidence
            - metadata-only evidence
            - no selected edit artifact observed

        Returns:
            dict: Classification result containing
            category, basis, and limitations.
        """

        unique_rsids = self._collect_unique_rsids(
            rsid_root,
            rsid_table,
            document_rsids
        )

        metadata_present = self._metadata_present(
            core_properties,
            app_properties
        )

        # -------------------------------------------------
        # Highest-priority evidence:
        # retained tracked revisions
        # -------------------------------------------------

        if revisions:

            return {
                "category":
                    "retained tracked-revision evidence",

                "basis": [
                    (
                        f"{len(revisions)} retained tracked "
                        f"revision(s) were observed."
                    ),
                    (
                        "The document contains retained "
                        "w:ins and/or w:del revision markup."
                    ),
                ],

                "limitations": [
                    (
                        "Retained revisions do not represent "
                        "a complete chronological history of "
                        "the document."
                    ),
                    (
                        "Revision author metadata should not "
                        "be treated as proof of the physical "
                        "identity of an editor."
                    ),
                ],
            }

        # -------------------------------------------------
        # Multiple distinct RSIDs
        # -------------------------------------------------

        if len(unique_rsids) > 1:

            return {
                "category":
                    "multiple-RSID-pattern evidence",

                "basis": [
                    (
                        f"{len(unique_rsids)} distinct RSID "
                        f"values were observed across the "
                        f"selected RSID artifacts."
                    ),
                    (
                        "No retained w:ins or w:del revisions "
                        "were observed."
                    ),
                ],

                "limitations": [
                    (
                        "Multiple RSIDs do not prove the "
                        "number of editors or editing sessions."
                    ),
                    (
                        "RSIDs may arise from editing, "
                        "document operations, templates, or "
                        "other application behaviour."
                    ),
                    (
                        "The observed RSIDs do not form a "
                        "complete chronological edit log."
                    ),
                ],
            }

        # -------------------------------------------------
        # Metadata but no selected RSID/revision evidence
        # -------------------------------------------------

        if metadata_present:

            return {
                "category":
                    "metadata-only evidence",

                "basis": [
                    (
                        "Document metadata was observed, but "
                        "no retained tracked revisions or "
                        "multiple-RSID pattern was detected."
                    ),
                ],

                "limitations": [
                    (
                        "Metadata values may be editable and "
                        "should be treated as contextual "
                        "evidence rather than proof of editing "
                        "history."
                    ),
                    (
                        "The absence of selected edit artifacts "
                        "does not prove that the document was "
                        "never edited."
                    ),
                ],
            }

        # -------------------------------------------------
        # Nothing selected was observed
        # -------------------------------------------------

        return {
            "category":
                "no selected edit artifact observed",

            "basis": [
                (
                    "No retained tracked revisions, "
                    "multiple-RSID pattern, or selected "
                    "metadata values were observed."
                ),
            ],

            "limitations": [
                (
                    "The absence of selected artifacts does "
                    "not establish that the document has no "
                    "editing history."
                ),
                (
                    "Relevant artifacts may have been removed, "
                    "accepted, overwritten, or may not have "
                    "been generated."
                ),
            ],
        }

    def _collect_unique_rsids(
        self,
        rsid_root,
        rsid_table,
        document_rsids
    ):
        """
        Collect distinct RSID values from the selected
        RSID evidence sources.

        Returns:
            set[str]
        """

        unique_rsids = set()

        if rsid_root:
            unique_rsids.add(rsid_root)

        for rsid in rsid_table:
            if rsid:
                unique_rsids.add(rsid)

        for item in document_rsids:

            value = item.get("value")

            if value:
                unique_rsids.add(value)

        return unique_rsids

    def _metadata_present(
        self,
        core_properties,
        app_properties
    ):
        """
        Determine whether any selected metadata value
        is present.

        Returns:
            bool
        """

        if core_properties:

            for value in core_properties.values():
                if value:
                    return True

        if app_properties:

            for value in app_properties.values():
                if value:
                    return True

        return False