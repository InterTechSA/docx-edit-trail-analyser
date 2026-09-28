from datetime import datetime


CONTENT_REVISION_TYPES = frozenset({
    "insertion",
    "deletion",
    "move_from",
    "move_to",
})

RSID_SCOPES = ("document", "content", "all")

# Elements whose RSIDs describe section layout rather than text.
# Templates carry these into every new document.
SECTION_ELEMENTS = frozenset({"sectPr"})


class CorrelationEngine:
    """
    Correlates extracted DOCX artifacts into explainable
    evidence categories.

    The engine does not determine whether a document is
    authentic or forged. It only describes patterns found
    in the selected artifacts.

    rsid_scope controls which RSIDs count towards the
    multiple-RSID rule:

        "document" (default)
            Only RSIDs referenced by attributes in
            word/document.xml. RSIDs that exist only in the
            settings.xml RSID table (or only as rsidRoot) are
            reported but do not trigger the rule, because
            templates routinely pre-populate that table and would
            otherwise make a freshly created document look like a
            multi-session document.

        "content"
            Like "document", but also ignores RSIDs found on
            section-properties elements (w:sectPr). The pilot
            corpus showed that a brand-new document created from
            a template already carries several distinct RSIDs on
            w:sectPr, copied from the template, before any text
            is typed.

        "all"
            RSIDs from rsidRoot, the settings table and the
            document combined. This was the rule used by the
            first prototype; it is kept so the two rules can be
            compared as an ablation on the controlled corpus
            (particularly on the same-template negative controls).

    Both classify() and score_evidence_dimensions() use the same
    scope, so the category and the evidence profile can never
    disagree about RSIDs.
    """

    # -----------------------------------------------------
    # Scoring thresholds (0-3 ordinal scale).
    #
    # Declared as class constants so they are visible, citable
    # in the report, and can be re-calibrated against the
    # Word-native corpus without touching the scoring logic.
    # -----------------------------------------------------

    # Distinct counted RSIDs -> score.
    #   0       -> 0 none observed
    #   1       -> 1 minimal  (consistent with a single save session)
    #   2 - 4   -> 2 moderate
    #   >= 5    -> 3 extensive
    RSID_MODERATE_MIN = 2
    RSID_EXTENSIVE_MIN = 5

    # Content revisions (insertions, deletions, moves) -> score.
    #   none, but other markers (paragraph marks, formatting) -> 1
    #   1 - 4   -> 2 moderate
    #   >= 5    -> 3 extensive
    REVISION_EXTENSIVE_MIN = 5

    def __init__(self, rsid_scope="document"):

        if rsid_scope not in RSID_SCOPES:
            raise ValueError(
                f"rsid_scope must be one of {RSID_SCOPES}"
            )

        self.rsid_scope = rsid_scope

    # =====================================================
    # Categorical classification
    # =====================================================

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

        Categories (checked in priority order):
            - retained tracked-revision evidence
            - multiple-RSID-pattern evidence
            - metadata-only evidence
            - no selected edit artifact observed

        Returns:
            dict: category, basis, limitations, evidence (a list
            of traceable records naming the OOXML part, element,
            attribute and value that support the category) and
            rsid_scope.

        This categorical result reports the single strongest
        observed pattern. It should always be presented alongside
        score_evidence_dimensions(), which reports the full
        evidence profile, so a reader is never left with an
        "edited" / "not edited" impression.
        """

        revisions = revisions or []

        counted_rsids = self._counted_rsids(
            rsid_root, rsid_table, document_rsids
        )

        all_rsids = self._collect_unique_rsids(
            rsid_root, rsid_table, document_rsids
        )

        referenced_rsids = self._referenced_rsids(document_rsids)

        settings_only = all_rsids - referenced_rsids

        metadata_present = self._metadata_present(
            core_properties, app_properties
        )

        # -------------------------------------------------
        # Highest priority: retained tracked revisions
        # -------------------------------------------------

        if revisions:

            breakdown = self._revision_breakdown(revisions)

            return self._result(
                "retained tracked-revision evidence",
                basis=[
                    (
                        f"{len(revisions)} retained tracked-"
                        f"revision marker(s) were observed "
                        f"({breakdown})."
                    ),
                    (
                        "The markup is present in "
                        "word/document.xml and is visible to "
                        "anyone who opens the file with Track "
                        "Changes shown."
                    ),
                ],
                limitations=[
                    (
                        "Retained revisions do not represent a "
                        "complete chronological history of the "
                        "document; accepted or rejected changes "
                        "leave no w:ins / w:del markup."
                    ),
                    (
                        "Revision author and date values are "
                        "application-supplied and editable; they "
                        "do not prove the physical identity of "
                        "an editor or the true time of an edit."
                    ),
                ],
                evidence=self._revision_trace(revisions),
            )

        # -------------------------------------------------
        # Multiple distinct RSIDs
        # -------------------------------------------------

        if len(counted_rsids) > 1:

            basis = [
                (
                    f"{len(counted_rsids)} distinct RSID values "
                    f"were counted ({self._scope_description()})."
                ),
                (
                    "No retained tracked-revision markup was "
                    "observed."
                ),
            ]

            if self.rsid_scope != "all" and settings_only:
                basis.append(
                    f"A further {len(settings_only)} RSID(s) "
                    f"appear only in word/settings.xml and were "
                    f"not counted."
                )

            return self._result(
                "multiple-RSID-pattern evidence",
                basis=basis,
                limitations=[
                    (
                        "Multiple RSIDs do not prove the number "
                        "of editors or editing sessions."
                    ),
                    (
                        "RSIDs may arise from editing, copy and "
                        "paste, template inheritance, or other "
                        "application behaviour."
                    ),
                    (
                        "The observed RSIDs do not form a "
                        "complete chronological edit log."
                    ),
                ],
                evidence=self._rsid_trace(
                    rsid_root, document_rsids, counted_rsids
                ),
            )

        # -------------------------------------------------
        # Metadata but no selected RSID / revision evidence
        # -------------------------------------------------

        if metadata_present:

            basis = [
                (
                    "Document metadata was observed, but no "
                    "retained tracked revisions or multiple-"
                    "RSID pattern was detected."
                ),
            ]

            if settings_only and self.rsid_scope != "all":
                basis.append(
                    f"{len(settings_only)} RSID(s) appear only "
                    f"in word/settings.xml; these were not "
                    f"counted because templates commonly "
                    f"pre-populate that table."
                )

            return self._result(
                "metadata-only evidence",
                basis=basis,
                limitations=[
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
                evidence=self._metadata_trace(
                    core_properties, app_properties
                ),
            )

        # -------------------------------------------------
        # Nothing selected was observed
        # -------------------------------------------------

        return self._result(
            "no selected edit artifact observed",
            basis=[
                (
                    "No retained tracked revisions, multiple-"
                    "RSID pattern, or selected metadata values "
                    "were observed."
                ),
            ],
            limitations=[
                (
                    "The absence of selected artifacts does not "
                    "establish that the document has no editing "
                    "history."
                ),
                (
                    "Relevant artifacts may have been removed, "
                    "accepted, overwritten, or may not have been "
                    "generated."
                ),
            ],
            evidence=[],
        )

    # =====================================================
    # Evidence profile (non-binary view)
    # =====================================================

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
        dimensions instead of collapsing everything into one
        winning category.

        This drives the dashboard's evidence-profile charts. A
        document can score on more than one dimension at once
        (for example moderate metadata AND extensive RSIDs with
        no retained revisions); classify() surfaces only one.

        Each dimension is scored on a 0-3 ordinal scale:
            0 = none observed, 1 = minimal,
            2 = moderate,      3 = extensive

        Each entry contains "score", "label", "basis" and the raw
        counts behind the score.
        """

        return {
            "revision_evidence":
                self._score_revision_evidence(revisions or []),

            "rsid_evidence":
                self._score_rsid_evidence(
                    rsid_root, rsid_table, document_rsids
                ),

            "metadata_evidence":
                self._score_metadata_evidence(
                    core_properties, app_properties
                ),
        }

    def _score_revision_evidence(self, revisions):

        content_count = sum(
            1 for r in revisions
            if r.get("type") in CONTENT_REVISION_TYPES
        )

        other = len(revisions) - content_count

        if content_count == 0 and other == 0:
            score = 0
            basis = (
                "No retained tracked-revision markup was observed."
            )

        elif content_count == 0:
            score = 1
            basis = (
                f"No retained content revisions, but {other} "
                f"other tracked marker(s) (paragraph-mark, "
                f"table-row or formatting changes) were observed."
            )

        else:
            score = (
                3 if content_count >= self.REVISION_EXTENSIVE_MIN
                else 2
            )
            basis = (
                f"{content_count} retained content revision(s) "
                f"were observed"
            )
            basis += (
                f", plus {other} other tracked marker(s)."
                if other else "."
            )

        return {
            "score": score,
            "label": self._label_for_score(score),
            "basis": basis,
            "content_count": content_count,
            "other_marker_count": other,
        }

    def _score_rsid_evidence(
        self,
        rsid_root,
        rsid_table,
        document_rsids
    ):
        """
        Score RSID evidence from the same RSID set that classify()
        counts, so the profile and the category always agree.
        """

        counted = self._counted_rsids(
            rsid_root, rsid_table, document_rsids
        )

        referenced = self._referenced_rsids(document_rsids)

        all_rsids = self._collect_unique_rsids(
            rsid_root, rsid_table, document_rsids
        )

        settings_only_count = len(all_rsids - referenced)

        counted_count = len(counted)

        if counted_count == 0:
            score = 0
        elif counted_count < self.RSID_MODERATE_MIN:
            score = 1
        elif counted_count < self.RSID_EXTENSIVE_MIN:
            score = 2
        else:
            score = 3

        if counted_count == 0:
            basis = (
                f"No RSIDs were counted "
                f"({self._scope_description()})."
            )

        elif counted_count == 1:
            basis = (
                "1 distinct RSID was counted; a single value is "
                "consistent with one save session and does not "
                "indicate a multi-session pattern."
            )

        else:
            basis = (
                f"{counted_count} distinct RSIDs were counted "
                f"({self._scope_description()})."
            )

        if self.rsid_scope != "all" and settings_only_count:
            basis += (
                f" A further {settings_only_count} RSID(s) "
                f"appear only in the settings table and are not "
                f"scored."
            )

        return {
            "score": score,
            "label": self._label_for_score(score),
            "basis": basis,
            "counted_count": counted_count,
            "referenced_count": len(referenced),
            "settings_only_count": settings_only_count,
            "rsid_scope": self.rsid_scope,
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
        last_modified_by = self._clean(core.get("last_modified_by"))

        created = self._parse_timestamp(core.get("created"))
        modified = self._parse_timestamp(core.get("modified"))

        signals = []

        if created and modified and modified > created:
            signals.append(
                "modified timestamp is later than created timestamp"
            )

        if creator and last_modified_by and creator != last_modified_by:
            signals.append("last modifier differs from creator")

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
                "No context signal of a later save or a different "
                "last modifier was observed. Populated metadata "
                "fields alone are not scored."
            )

        return {
            "score": score,
            "label": self._label_for_score(score),
            "basis": basis,
            "signals": signals,
        }

    # =====================================================
    # Traceability helpers
    # =====================================================

    def _result(self, category, basis, limitations, evidence):

        return {
            "category": category,
            "basis": basis,
            "limitations": limitations,
            "evidence": evidence,
            "rsid_scope": self.rsid_scope,
        }

    def _revision_trace(self, revisions):

        trace = []

        for revision in revisions:

            element = revision.get("element") or (
                "w:ins" if revision.get("type") == "insertion"
                else "w:del"
            )

            trace.append({
                "evidence_group": "retained revision",
                "part": revision.get("part", "word/document.xml"),
                "element": element,
                "attribute": "w:author / w:date",
                "value": (
                    f"type={revision.get('type')}; "
                    f"author={revision.get('author')}; "
                    f"date={revision.get('date')}; "
                    f"text={revision.get('text')}"
                ),
            })

        return trace

    def _rsid_trace(self, rsid_root, document_rsids, counted_rsids):

        first_location = {}

        for item in document_rsids or []:

            value = item.get("value")

            if value and value not in first_location:
                first_location[value] = item

        trace = []

        for rsid in sorted(counted_rsids):

            item = first_location.get(rsid)

            if item is not None:

                element = item.get("element", "")

                if "}" in element:
                    element = element.split("}", 1)[1]

                trace.append({
                    "evidence_group": "RSID",
                    "part": item.get("part", "word/document.xml"),
                    "element": f"w:{element}",
                    "attribute": f"w:{item.get('attribute')}",
                    "value": rsid,
                })

            else:

                trace.append({
                    "evidence_group": "RSID",
                    "part": "word/settings.xml",
                    "element": (
                        "w:rsids/w:rsidRoot"
                        if rsid == rsid_root
                        else "w:rsids/w:rsid"
                    ),
                    "attribute": "w:val",
                    "value": rsid,
                })

        return trace

    def _metadata_trace(self, core_properties, app_properties):

        sources = [
            ("docProps/core.xml", core_properties, {
                "creator": "dc:creator",
                "last_modified_by": "cp:lastModifiedBy",
                "created": "dcterms:created",
                "modified": "dcterms:modified",
            }),
            ("docProps/app.xml", app_properties, {
                "application": "Application",
                "app_version": "AppVersion",
            }),
        ]

        trace = []

        for part, values, elements in sources:

            for key, element in elements.items():

                value = (values or {}).get(key)

                if value:
                    trace.append({
                        "evidence_group": "context metadata",
                        "part": part,
                        "element": element,
                        "attribute": "(element text)",
                        "value": value,
                    })

        return trace

    def _revision_breakdown(self, revisions):

        counts = {}

        for revision in revisions:

            revision_type = revision.get("type", "unknown")
            counts[revision_type] = counts.get(revision_type, 0) + 1

        return ", ".join(
            f"{count} {revision_type.replace('_', ' ')}"
            for revision_type, count in counts.items()
        )

    # =====================================================
    # General helpers
    # =====================================================

    def _scope_description(self):

        if self.rsid_scope == "document":
            return "RSIDs referenced in word/document.xml"

        if self.rsid_scope == "content":
            return (
                "RSIDs referenced on content elements in "
                "word/document.xml, excluding w:sectPr"
            )

        return (
            "rsidRoot, settings RSID table and document RSID "
            "attributes combined"
        )

    def _counted_rsids(self, rsid_root, rsid_table, document_rsids):

        if self.rsid_scope == "document":
            return self._referenced_rsids(document_rsids)

        if self.rsid_scope == "content":
            return self._referenced_rsids([
                item for item in (document_rsids or [])
                if self._local(item.get("element", ""))
                not in SECTION_ELEMENTS
            ])

        return self._collect_unique_rsids(
            rsid_root, rsid_table, document_rsids
        )

    def _local(self, tag):

        return tag.split("}", 1)[1] if "}" in tag else tag

    def _referenced_rsids(self, document_rsids):

        return {
            item.get("value")
            for item in (document_rsids or [])
            if item.get("value")
        }

    def _clean(self, value):

        if value is None:
            return None

        value = value.strip()

        return value or None

    def _parse_timestamp(self, value):

        value = self._clean(value)

        if not value:
            return None

        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _label_for_score(self, score):

        return {
            0: "None observed",
            1: "Minimal",
            2: "Moderate",
            3: "Extensive",
        }.get(score, "Unknown")

    def _collect_unique_rsids(self, rsid_root, rsid_table, document_rsids):
        """Distinct RSID values from all selected RSID sources."""

        unique_rsids = set()

        if rsid_root:
            unique_rsids.add(rsid_root)

        for rsid in rsid_table or []:
            if rsid:
                unique_rsids.add(rsid)

        unique_rsids |= self._referenced_rsids(document_rsids)

        return unique_rsids

    def _metadata_present(self, core_properties, app_properties):
        """True when any selected metadata value is present."""

        for values in (core_properties, app_properties):

            for value in (values or {}).values():
                if value:
                    return True

        return False
