class GroundTruthEvaluator:
    """
    Evaluates extracted DOCX evidence against the known
    ground truth recorded for a controlled sample.

    The evaluator measures agreement between expected and
    observed artifacts. It does not determine authenticity,
    forgery, or whether an undocumented editing event
    occurred.
    """

    def evaluate_sample(
        self,
        ground_truth,
        evidence,
        baseline_evidence=None
    ):
        """
        Evaluate one controlled sample.

        baseline_evidence is optional and is only required
        for expectations that explicitly compare a sample
        with the baseline.
        """

        expected = ground_truth.get(
            "expected_selected_evidence",
            {}
        )

        results = []

        # -------------------------------------------------
        # Retained insertion count
        # -------------------------------------------------

        if "retained_insertions" in expected:

            observed_count = self._count_revisions(
                evidence,
                "insertion"
            )

            expected_count = expected[
                "retained_insertions"
            ]

            results.append(
                self._result(
                    "Retained insertions",
                    expected_count,
                    observed_count,
                    expected_count == observed_count
                )
            )

        # -------------------------------------------------
        # Retained deletion count
        # -------------------------------------------------

        if "retained_deletions" in expected:

            observed_count = self._count_revisions(
                evidence,
                "deletion"
            )

            expected_count = expected[
                "retained_deletions"
            ]

            results.append(
                self._result(
                    "Retained deletions",
                    expected_count,
                    observed_count,
                    expected_count == observed_count
                )
            )

        # -------------------------------------------------
        # Insertion text
        # -------------------------------------------------

        if "insertion_text" in expected:

            observed_texts = (
                self._revision_values(
                    evidence,
                    "insertion",
                    "text"
                )
            )

            expected_text = expected[
                "insertion_text"
            ]

            results.append(
                self._result(
                    "Insertion text",
                    expected_text,
                    self._display_values(
                        observed_texts
                    ),
                    expected_text
                    in observed_texts
                )
            )

        # -------------------------------------------------
        # Deletion text
        # -------------------------------------------------

        if "deletion_text" in expected:

            observed_texts = (
                self._revision_values(
                    evidence,
                    "deletion",
                    "text"
                )
            )

            expected_text = expected[
                "deletion_text"
            ]

            results.append(
                self._result(
                    "Deletion text",
                    expected_text,
                    self._display_values(
                        observed_texts
                    ),
                    expected_text
                    in observed_texts
                )
            )

        # -------------------------------------------------
        # Revision author
        # -------------------------------------------------

        if "revision_author" in expected:

            observed_authors = (
                self._all_revision_values(
                    evidence,
                    "author"
                )
            )

            expected_author = expected[
                "revision_author"
            ]

            results.append(
                self._result(
                    "Revision author",
                    expected_author,
                    self._display_values(
                        observed_authors
                    ),
                    expected_author
                    in observed_authors
                )
            )

        # -------------------------------------------------
        # Revision dates
        # -------------------------------------------------

        if "revision_dates" in expected:

            expected_dates = expected[
                "revision_dates"
            ]

            observed_dates = (
                self._all_revision_values(
                    evidence,
                    "date"
                )
            )

            matched = (
                set(expected_dates)
                == set(observed_dates)
            )

            results.append(
                self._result(
                    "Revision dates",
                    self._display_values(
                        expected_dates
                    ),
                    self._display_values(
                        observed_dates
                    ),
                    matched
                )
            )

        # -------------------------------------------------
        # Classification
        # -------------------------------------------------

        if "classification" in expected:

            expected_classification = (
                expected[
                    "classification"
                ]
            )

            observed_classification = (
                evidence.get(
                    "classification",
                    {}
                ).get(
                    "category"
                )
            )

            results.append(
                self._result(
                    "Evidence classification",
                    expected_classification,
                    observed_classification,
                    (
                        expected_classification
                        == observed_classification
                    )
                )
            )

        # -------------------------------------------------
        # Context metadata presence
        # -------------------------------------------------

        if (
            "context_metadata_present"
            in expected
        ):

            expected_present = expected[
                "context_metadata_present"
            ]

            observed_present = (
                self._context_metadata_present(
                    evidence
                )
            )

            results.append(
                self._result(
                    "Context metadata present",
                    expected_present,
                    observed_present,
                    (
                        expected_present
                        == observed_present
                    )
                )
            )

        # -------------------------------------------------
        # Modified timestamp later than baseline
        # -------------------------------------------------

        if (
            "modified_timestamp_later_than_baseline"
            in expected
        ):

            expected_later = expected[
                "modified_timestamp_later_than_baseline"
            ]

            observed_later = None

            if baseline_evidence is not None:

                observed_later = (
                    self._modified_later_than_baseline(
                        evidence,
                        baseline_evidence
                    )
                )

            results.append(
                self._result(
                    (
                        "Modified timestamp later "
                        "than baseline"
                    ),
                    expected_later,
                    observed_later,
                    (
                        observed_later is not None
                        and
                        expected_later
                        == observed_later
                    ),
                    (
                        "Baseline evidence required."
                        if observed_later is None
                        else None
                    )
                )
            )

        # -------------------------------------------------
        # RSID expectation
        # -------------------------------------------------

        if "rsid_expectation" in expected:

            results.append({
                "artifact":
                    "RSID expectation",

                "expected":
                    expected[
                        "rsid_expectation"
                    ],

                "observed":
                    (
                        f"{len(evidence.get('unique_rsids', []))} "
                        f"distinct RSID value(s) observed"
                    ),

                "matched":
                    None,

                "status":
                    "Not evaluated",

                "note":
                    (
                        "The ground truth explicitly "
                        "makes no validation claim about "
                        "generator RSID behaviour."
                    ),
            })

        # -------------------------------------------------
        # Summary
        # -------------------------------------------------

        evaluated_results = [
            result
            for result in results
            if result["matched"] is not None
        ]

        matched_count = sum(
            1
            for result in evaluated_results
            if result["matched"]
        )

        mismatched_count = sum(
            1
            for result in evaluated_results
            if not result["matched"]
        )

        not_evaluated_count = (
            len(results)
            - len(evaluated_results)
        )

        return {
            "sample_id":
                ground_truth.get(
                    "sample_id"
                ),

            "file":
                ground_truth.get(
                    "file"
                ),

            "creation_method":
                ground_truth.get(
                    "creation_method"
                ),

            "controlled_actions":
                ground_truth.get(
                    "controlled_actions",
                    []
                ),

            "deliberate_deviations":
                ground_truth.get(
                    "deliberate_deviations",
                    []
                ),

            "research_limitations":
                ground_truth.get(
                    "research_limitations",
                    []
                ),

            "results":
                results,

            "evaluated_count":
                len(evaluated_results),

            "matched_count":
                matched_count,

            "mismatched_count":
                mismatched_count,

            "not_evaluated_count":
                not_evaluated_count,
        }

    def _count_revisions(
        self,
        evidence,
        revision_type
    ):
        return sum(
            1
            for revision in evidence.get(
                "revisions",
                []
            )
            if revision.get("type")
            == revision_type
        )

    def _revision_values(
        self,
        evidence,
        revision_type,
        field
    ):
        values = []

        for revision in evidence.get(
            "revisions",
            []
        ):

            if (
                revision.get("type")
                != revision_type
            ):
                continue

            value = revision.get(
                field
            )

            if value is not None:
                values.append(
                    value
                )

        return values

    def _all_revision_values(
        self,
        evidence,
        field
    ):
        values = []

        for revision in evidence.get(
            "revisions",
            []
        ):

            value = revision.get(
                field
            )

            if (
                value is not None
                and value not in values
            ):
                values.append(
                    value
                )

        return values

    def _context_metadata_present(
        self,
        evidence
    ):
        core = evidence.get(
            "core_properties",
            {}
        )

        app = evidence.get(
            "app_properties",
            {}
        )

        return any(
            value
            for value in (
                list(core.values())
                + list(app.values())
            )
        )

    def _modified_later_than_baseline(
        self,
        evidence,
        baseline_evidence
    ):
        modified = (
            evidence.get(
                "core_properties",
                {}
            ).get(
                "modified"
            )
        )

        baseline_modified = (
            baseline_evidence.get(
                "core_properties",
                {}
            ).get(
                "modified"
            )
        )

        if (
            modified is None
            or baseline_modified is None
        ):
            return None

        return (
            modified
            > baseline_modified
        )

    def _display_values(
        self,
        values
    ):
        if not values:
            return "None observed"

        return ", ".join(
            str(value)
            for value in values
        )

    def _result(
        self,
        artifact,
        expected,
        observed,
        matched,
        note=None
    ):
        return {
            "artifact":
                artifact,

            "expected":
                expected,

            "observed":
                observed,

            "matched":
                matched,

            "status":
                (
                    "Match"
                    if matched
                    else "Mismatch"
                ),

            "note":
                note,
        }