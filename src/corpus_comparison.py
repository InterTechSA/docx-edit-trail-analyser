from collections import Counter


class CorpusComparison:
    """
    Converts evidence extracted from multiple DOCX samples
    into comparable research records.

    This class does not determine authenticity or whether
    a document was edited. It summarizes observed artifacts
    for comparison across controlled samples.
    """

    def create_sample_record(
        self,
        sample_name,
        evidence
    ):
        """
        Create a normalized comparison record for one
        analysed DOCX sample.
        """

        revisions = evidence.get(
            "revisions",
            []
        )

        document_rsids = evidence.get(
            "document_rsids",
            []
        )

        unique_rsids = evidence.get(
            "unique_rsids",
            []
        )

        core_properties = evidence.get(
            "core_properties",
            {}
        )

        app_properties = evidence.get(
            "app_properties",
            {}
        )

        classification = evidence.get(
            "classification",
            {}
        )

        revision_types = Counter(
            revision.get("type")
            for revision in revisions
        )

        return {
            "sample": sample_name,

            "distinct_rsids":
                len(unique_rsids),

            "document_rsid_attributes":
                len(document_rsids),

            "retained_revisions":
                len(revisions),

            "insertions":
                revision_types.get(
                    "insertion",
                    0
                ),

            "deletions":
                revision_types.get(
                    "deletion",
                    0
                ),

            "creator":
                core_properties.get(
                    "creator"
                ),

            "last_modified_by":
                core_properties.get(
                    "last_modified_by"
                ),

            "created":
                core_properties.get(
                    "created"
                ),

            "modified":
                core_properties.get(
                    "modified"
                ),

            "application":
                app_properties.get(
                    "application"
                ),

            "application_version":
                app_properties.get(
                    "app_version"
                ),

            "classification":
                classification.get(
                    "category"
                ),
        }

    def create_comparison_records(
        self,
        analysed_samples
    ):
        """
        Create comparison records for multiple samples.

        analysed_samples format:

        {
            "01_baseline.docx": evidence,
            "02_edited.docx": evidence,
            ...
        }
        """

        records = []

        for sample_name, evidence in (
            analysed_samples.items()
        ):

            record = self.create_sample_record(
                sample_name,
                evidence
            )

            records.append(
                record
            )

        return records

    def create_artifact_matrix(
        self,
        records
    ):
        """
        Create a simple presence/absence matrix describing
        selected observed artifacts.

        Returns:
            list[dict]
        """

        matrix = []

        for record in records:

            matrix.append({
                "sample":
                    record["sample"],

                "rsid_evidence":
                    (
                        record[
                            "distinct_rsids"
                        ] > 0
                    ),

                "document_rsid_attributes":
                    (
                        record[
                            "document_rsid_attributes"
                        ] > 0
                    ),

                "retained_insertion":
                    (
                        record[
                            "insertions"
                        ] > 0
                    ),

                "retained_deletion":
                    (
                        record[
                            "deletions"
                        ] > 0
                    ),

                "creator_metadata":
                    bool(
                        record[
                            "creator"
                        ]
                    ),

                "modified_metadata":
                    bool(
                        record[
                            "modified"
                        ]
                    ),

                "application_metadata":
                    bool(
                        record[
                            "application"
                        ]
                    ),
            })

        return matrix