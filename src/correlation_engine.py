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

        NOTE: This categorical classification is retained for
        continuity with existing tests and the auditable-basis
        requirement. It intentionally reports the single
        strongest observed pattern. It should always be
        presented alongside score_evidence_dimensions(), which
        reports the full evidence profile across all dimensions
        rather than a single winning category, so that a reader
        is never left with an "edited" / "not edited" impression.
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

    def score_evidence_dimensions(
        self,
        rsid_root,
        rsid_table,
        document_rsids,
        revisions,
        core_properties,
        app_properties
    ):
        """
        Score the observed evidence independently across three
        dimensions, instead of collapsing everything into one
        winning category.

        This exists specifically so the tool can present a
        multi-dimensional evidence profile (e.g. a bar chart or
        radar chart per sample) rather than a single label such
        as "edited" or "not edited". A document can score highly
        on more than one dimension at once (e.g. rich metadata
        AND multiple RSIDs, with no retained revisions) — the
        classify() method above would only ever surface one of
        those, whereas this method preserves and reports all of
        them.

        Each dimension is scored on a 0-3 ordinal scale:
            0 = none observed
            1 = minimal
            2 = moderate
            3 = extensive

        Returns:
            dict: {
                "revision_evidence": {...},
                "rsid_evidence": {...},
                "metadata_evidence": {...},
            }
            Each entry contains "score" (0-3), "label", and
            "basis" (a short explanatory string).
        """

        return {
            "revision_evidence":
                self._score_revision_evidence(revisions),

            "rsid_evidence":
                self._score_rsid_evidence(
                    rsid_root,
                    rsid_table,
                    document_rsids
                ),

            "metadata_evidence":
                self._score_metadata_evidence(
                    core_properties,
                    app_properties
                ),
        }

    def _score_revision_evidence(self, revisions):

        count = len(revisions)

        if count == 0:
            score = 0
            basis = "No retained w:ins or w:del markup was observed."

        elif count <= 2:
            score = 2
            basis = (
                f"{count} retained tracked revision(s) "
                f"were observed."
            )

        else:
            score = 3
            basis = (
                f"{count} retained tracked revisions were "
                f"observed, indicating an extensive retained "
                f"revision trail."
            )

        return {
            "score": score,
            "label": self._label_for_score(score),
            "basis": basis,
        }

    def _score_rsid_evidence(
        self,
        rsid_root,
        rsid_table,
        document_rsids
    ):
        """
        Score RSID evidence using only RSIDs actually referenced
        by attributes in word/document.xml.

        RSIDs that appear only in the settings.xml RSID table
        (or as rsidRoot) are reported in the basis text but are
        NOT scored: templates and generators routinely
        pre-populate that table, so it is weak evidence of
        editing on its own.
        """

        referenced = {
            item.get("value")
            for item in document_rsids
            if item.get("value")
        }

        all_rsids = self._collect_unique_rsids(
            rsid_root,
            rsid_table,
            document_rsids
        )

        settings_only_count = len(all_rsids - referenced)

        referenced_count = len(referenced)

        # 0, 1, 2 referenced RSIDs map to scores 0, 1, 2;
        # 3 or more is scored 3.
        score = min(referenced_count, 3)

        if referenced_count == 0:
            basis = (
                "No RSIDs were referenced in word/document.xml."
            )

        elif referenced_count == 1:
            basis = (
                "1 distinct RSID is referenced in "
                "word/document.xml; a single value does not "
                "indicate a multi-session pattern."
            )

        else:
            basis = (
                f"{referenced_count} distinct RSIDs are "
                f"referenced in word/document.xml."
            )

        if settings_only_count:
            basis += (
                f" A further {settings_only_count} RSID(s) "
                f"appear only in the settings table and are "
                f"not scored."
            )

        return {
            "score": score,
            "label": self._label_for_score(score),
            "basis": basis,
            "referenced_count": referenced_count,
            "settings_only_count": settings_only_count,
        }

    def _score_metadata_evidence(
        self,
        core_properties,
        app_properties
    ):
        """
        Score context metadata by signals that hint at a
        save-after-creation history, rather than by how many
        fields are merely populated (nearly every Word-saved
        file has all of them).

        Signals (1 point each):
            - dcterms:modified is later than dcterms:created
            - cp:lastModifiedBy differs from dc:creator

        The score is capped at 2 because these values are
        editable and only contextual.
        """

        core = core_properties or {}

        creator = self._clean(core.get("creator"))
        last_modified_by = self._clean(
            core.get("last_modified_by")
        )

        created = self._parse_timestamp(core.get("created"))
        modified = self._parse_timestamp(core.get("modified"))

        signals = []

        if created and modified and modified > created:
            signals.append(
                "modified timestamp is later than created "
                "timestamp"
            )

        if (
            creator
            and last_modified_by
            and creator != last_modified_by
        ):
            signals.append(
                "last modifier differs from creator"
            )

        score = len(signals)

        if signals:
            basis = (
                "Context signals observed: "
                + "; ".join(signals)
                + ". Metadata is editable and capped at a "
                "moderate score."
            )
        else:
            basis = (
                "No context signal of a later save or a "
                "different last modifier was observed. "
                "Populated metadata fields alone are not "
                "scored."
            )

        return {
            "score": score,
            "label": self._label_for_score(score),
            "basis": basis,
        }

    def _clean(self, value):

        if value is None:
            return None

        value = value.strip()

        return value or None

    def _parse_timestamp(self, value):

        from datetime import datetime

        value = self._clean(value)

        if not value:
            return None

        try:
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError:
            return None

    def _label_for_score(self, score):

        labels = {
            0: "None observed",
            1: "Minimal",
            2: "Moderate",
            3: "Extensive",
        }

        return labels.get(score, "Unknown")

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