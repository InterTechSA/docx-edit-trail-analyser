"""
Artifact survival analysis (research question 3).

RQ3 asks how controlled transformations (save without editing,
direct editing, accepting / rejecting tracked changes, copying,
metadata cleaning) affect which selected artifacts survive.

A transformation always has a *parent* (the file before) and a
*child* (the file after). The ground-truth JSON of the child names
its parent in "derived_from" and the operation in
"transformation". For every parent/child pair this module compares
the artifacts extracted from both files and reports, per artifact
group:

    parent_count   artifacts present in the parent
    child_count    artifacts present in the child
    retained       parent artifacts still present in the child
    introduced     child artifacts that were not in the parent
    survival_rate  retained / parent_count   (None if parent_count 0)

Survival is measured by identity where the artifact has one
(an RSID value, a revision's type+text+author, a metadata field's
value), so an artifact that was replaced by a different value is
counted as lost, not survived.
"""

from pathlib import Path


CONTENT_REVISION_TYPES = {"insertion", "deletion", "move_from", "move_to"}

METADATA_FIELDS = (
    ("creator", "core_properties"),
    ("last_modified_by", "core_properties"),
    ("created", "core_properties"),
    ("modified", "core_properties"),
    ("application", "app_properties"),
    ("app_version", "app_properties"),
)

ARTIFACT_GROUPS = (
    "rsidRoot",
    "Settings RSID table",
    "Referenced RSIDs",
    "Content revisions",
    "Other revision markers",
    "Author metadata",
    "Timestamp metadata",
    "Application metadata",
)


def _ratio(numerator, denominator):

    if denominator == 0:
        return None

    return numerator / denominator


def _revision_signature(revision):

    return (
        revision.get("type"),
        revision.get("text"),
        revision.get("author"),
    )


def artifact_sets(evidence):
    """
    Convert one evidence dict into comparable sets, one per
    artifact group.
    """

    revisions = evidence.get("revisions", [])

    core = evidence.get("core_properties") or {}
    app = evidence.get("app_properties") or {}

    def field_set(names, source):
        return {
            (name, source.get(name))
            for name in names
            if source.get(name)
        }

    return {
        "rsidRoot": (
            {evidence["rsid_root"]}
            if evidence.get("rsid_root") else set()
        ),
        "Settings RSID table": {
            r for r in evidence.get("rsid_table", []) if r
        },
        "Referenced RSIDs": {
            item["value"]
            for item in evidence.get("document_rsids", [])
            if item.get("value")
        },
        "Content revisions": {
            _revision_signature(r)
            for r in revisions
            if r.get("type") in CONTENT_REVISION_TYPES
        },
        "Other revision markers": {
            _revision_signature(r) + (r.get("revision_id"),)
            for r in revisions
            if r.get("type") not in CONTENT_REVISION_TYPES
        },
        "Author metadata": field_set(
            ("creator", "last_modified_by"), core
        ),
        "Timestamp metadata": field_set(
            ("created", "modified"), core
        ),
        "Application metadata": field_set(
            ("application", "app_version"), app
        ),
    }


def compare_pair(parent_evidence, child_evidence):
    """
    Compare one parent/child pair.

    Returns:
        list[dict]: one row per artifact group.
    """

    parent_sets = artifact_sets(parent_evidence)
    child_sets = artifact_sets(child_evidence)

    rows = []

    for group in ARTIFACT_GROUPS:

        parent = parent_sets[group]
        child = child_sets[group]

        retained = parent & child

        rows.append({
            "artifact": group,
            "parent_count": len(parent),
            "child_count": len(child),
            "retained": len(retained),
            "introduced": len(child - parent),
            "survival_rate": _ratio(len(retained), len(parent)),
        })

    return rows


def _match_sample_name(reference, analysed_samples):
    """
    Resolve a ground-truth "derived_from" value (which may be a
    bare filename or a relative path) to an analysed sample key.
    """

    if not reference:
        return None

    target = Path(reference).name

    for name in analysed_samples:

        if Path(name).name == target:
            return name

    return None


def survival_table(analysed_samples, ground_truth_records):
    """
    Build the full survival table for a corpus.

    analysed_samples:     {sample_name: evidence}
    ground_truth_records: {sample_name: ground-truth dict}

    Only samples whose ground truth names a parent
    ("derived_from") or an independent comparison sample
    ("compare_with") that was also analysed contribute rows.

    Returns:
        list[dict]: rows with sample, parent, transformation,
        and the compare_pair() columns.
    """

    rows = []

    for sample_name, ground_truth in ground_truth_records.items():

        # "derived_from": the sample is a transformation of its
        # parent. "compare_with": the samples are independent (for
        # example two documents made from the same template); the
        # comparison then shows artifacts they share by inheritance
        # rather than by derivation.
        reference = (
            ground_truth.get("derived_from")
            or ground_truth.get("compare_with")
        )

        parent_name = _match_sample_name(
            reference,
            analysed_samples
        )

        if parent_name is None or sample_name not in analysed_samples:
            continue

        transformation = (
            ground_truth.get("transformation")
            or ground_truth.get("sample_id")
            or sample_name
        )

        for row in compare_pair(
            analysed_samples[parent_name],
            analysed_samples[sample_name],
        ):
            rows.append({
                "sample": sample_name,
                "parent": parent_name,
                "transformation": transformation,
                **row,
            })

    return rows
