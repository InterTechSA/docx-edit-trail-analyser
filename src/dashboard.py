import json
import os
import tempfile
from collections import Counter
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from correlation_engine import RSID_SCOPES
from corpus_comparison import CorpusComparison
from corpus_evaluation import evaluate_corpus, resolve_baseline
from evidence_pipeline import analyse_docx
from ground_truth_evaluator import GroundTruthEvaluator
from research_metrics import ResearchMetrics


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="DOCX Edit-Trail Analyser",
    page_icon="🔎",
    layout="wide",
)


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def simplify_element_name(element_tag):
    """
    Convert an ElementTree namespace tag such as:

    {http://schemas.../main}p

    into:

    p
    """

    if "}" in element_tag:
        return element_tag.split("}", 1)[1]

    return element_tag


def create_rsid_occurrence_table(
    rsid_root,
    rsid_table,
    document_rsids
):
    """
    Count where each RSID was observed.
    """

    occurrences = Counter()

    if rsid_root:
        occurrences[rsid_root] += 1

    for rsid in rsid_table:
        occurrences[rsid] += 1

    for item in document_rsids:

        value = item.get("value")

        if value:
            occurrences[value] += 1

    rows = []

    for rsid, count in sorted(
        occurrences.items()
    ):

        rows.append({
            "RSID": rsid,
            "Occurrences": count,
        })

    return pd.DataFrame(rows)


def create_rsid_relationship_table(
    rsid_root,
    rsid_table,
    document_rsids
):
    """
    Describe where each distinct RSID was observed.

    This does not imply chronology, authorship,
    or a causal relationship between RSIDs.
    """

    all_rsids = set()

    if rsid_root:
        all_rsids.add(rsid_root)

    all_rsids.update(
        rsid
        for rsid in rsid_table
        if rsid
    )

    all_rsids.update(
        item["value"]
        for item in document_rsids
        if item.get("value")
    )

    rows = []

    for rsid in sorted(all_rsids):

        document_matches = [
            item
            for item in document_rsids
            if item.get("value") == rsid
        ]

        document_locations = []

        for item in document_matches:

            element = simplify_element_name(
                item["element"]
            )

            document_locations.append(
                f"{element} / {item['attribute']}"
            )

        rows.append({
            "RSID": rsid,
            "Root": (
                "Yes"
                if rsid == rsid_root
                else "No"
            ),
            "Settings Table": (
                "Yes"
                if rsid in rsid_table
                else "No"
            ),
            "Document": (
                "Yes"
                if document_matches
                else "No"
            ),
            "Document Location": (
                ", ".join(document_locations)
                if document_locations
                else "—"
            ),
        })

    return pd.DataFrame(rows)


def analyse_uploaded_file(uploaded_file):
    """
    Save an uploaded Streamlit DOCX temporarily,
    analyse it, then safely remove the temporary file.
    """

    temporary_path = None

    try:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".docx"
        ) as temporary_file:

            temporary_file.write(
                uploaded_file.getvalue()
            )

            temporary_path = (
                temporary_file.name
            )

        return analyse_docx(
            temporary_path,
            st.session_state.get("rsid_scope", "document"),
        )

    finally:

        if (
            temporary_path
            and Path(
                temporary_path
            ).exists()
        ):

            os.remove(
                temporary_path
            )


def get_project_root():
    """
    Return the project root directory.
    """

    return (
        Path(__file__)
        .resolve()
        .parent
        .parent
    )


def get_ground_truth_directory():
    """
    Return the controlled-corpus ground-truth directory.
    """

    return (
        get_project_root()
        / "samples"
        / "ground_truth"
    )


def load_ground_truth_for_docx(
    docx_name
):
    """
    Load the JSON ground-truth record matching an uploaded
    DOCX filename.

    Example:

        01_baseline.docx
        ->
        01_baseline.json
    """

    json_name = (
        Path(docx_name)
        .with_suffix(".json")
        .name
    )

    json_path = (
        get_ground_truth_directory()
        / json_name
    )

    if not json_path.exists():
        return None

    try:

        with open(
            json_path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (
        OSError,
        json.JSONDecodeError
    ):
        return None

def create_evaluation_dataframe(
    evaluation
):
    """
    Convert one ground-truth evaluation into a
    presentation-friendly DataFrame.

    Values are converted to strings so Streamlit /
    PyArrow receives consistent column types.
    """

    rows = []

    for result in evaluation[
        "results"
    ]:

        status = result[
            "status"
        ]

        if status == "Match":
            status_display = "✓ Match"

        elif status == "Mismatch":
            status_display = "✗ Mismatch"

        else:
            status_display = "— Not evaluated"

        expected = result.get(
            "expected"
        )

        observed = result.get(
            "observed"
        )

        note = (
            result.get(
                "note"
            )
            or ""
        )

        rows.append({
            "Artifact":
                str(
                    result.get(
                        "artifact",
                        ""
                    )
                ),

            "Expected":
                (
                    "None"
                    if expected is None
                    else str(expected)
                ),

            "Observed":
                (
                    "None"
                    if observed is None
                    else str(observed)
                ),

            "Status":
                status_display,

            "Note":
                str(note),
        })

    dataframe = pd.DataFrame(
        rows
    )

    return dataframe.astype(
        {
            "Artifact": "string",
            "Expected": "string",
            "Observed": "string",
            "Status": "string",
            "Note": "string",
        }
    )


def create_evidence_profile_dataframe(evidence_profile):
    """
    Convert an evidence profile (as returned by
    CorrelationEngine.score_evidence_dimensions) into a
    presentation-friendly DataFrame for charting.

    This is deliberately dimension-based rather than a single
    verdict column, so the chart it feeds shows a *profile*
    (e.g. moderate revision evidence + minimal RSID evidence +
    extensive metadata evidence) rather than one label.
    """

    display_names = {
        "revision_evidence": "Retained Revisions",
        "rsid_evidence": "RSID Pattern",
        "metadata_evidence": "Context Metadata",
    }

    rows = []

    for key, display_name in display_names.items():

        dimension = evidence_profile.get(key, {})

        rows.append({
            "Evidence Dimension": display_name,
            "Strength (0-3)": dimension.get("score", 0),
            "Label": dimension.get("label", "Unknown"),
            "Basis": dimension.get("basis", ""),
        })

    return pd.DataFrame(rows)



def format_metric(value):
    """Format a ratio for display; undefined metrics show n/a."""

    if value is None:
        return "n/a"

    return f"{value:.2f}"


PROFILE_SCALE = alt.Scale(domain=[0, 3])


def single_profile_chart(profile_dataframe):
    """
    Horizontal bar chart of one sample's evidence profile with
    a fixed 0-3 axis so charts are comparable across samples.
    """

    return (
        alt.Chart(profile_dataframe)
        .mark_bar()
        .encode(
            x=alt.X(
                "Strength (0-3):Q",
                scale=PROFILE_SCALE,
                axis=alt.Axis(tickCount=4, format="d"),
            ),
            y=alt.Y(
                "Evidence Dimension:N",
                sort=None,
                title=None,
                axis=alt.Axis(
                    labelLimit=200,
                    labelOverlap=False,
                ),
            ),
            tooltip=["Evidence Dimension", "Label", "Basis"],
        )
        .properties(height=180)
    )


def corpus_profile_chart(profile_rows):
    """
    Grouped bar chart of every sample's evidence profile with a
    fixed 0-3 axis.
    """

    long_dataframe = pd.DataFrame(profile_rows).melt(
        id_vars="sample",
        var_name="Dimension",
        value_name="Strength",
    )

    return (
        alt.Chart(long_dataframe)
        .mark_bar()
        .encode(
            x=alt.X("sample:N", title=None),
            xOffset="Dimension:N",
            y=alt.Y(
                "Strength:Q",
                scale=PROFILE_SCALE,
                axis=alt.Axis(tickCount=4, format="d"),
            ),
            color="Dimension:N",
            tooltip=["sample", "Dimension", "Strength"],
        )
    )


SHORT_CATEGORY = {
    "retained tracked-revision evidence": "Tracked revisions",
    "multiple-RSID-pattern evidence": "Multiple RSIDs",
    "metadata-only evidence": "Metadata only",
    "no selected edit artifact observed": "None observed",
}


def profile_heatmap_chart(profile_rows):
    """
    Heatmap "evidence fingerprint": one row per sample, one column
    per evidence dimension, colour = 0-3 strength. Samples with the
    same history should show the same fingerprint.
    """

    long_dataframe = pd.DataFrame(profile_rows).melt(
        id_vars="sample",
        var_name="Dimension",
        value_name="Strength",
    )

    base = alt.Chart(long_dataframe).encode(
        x=alt.X("Dimension:N", title=None, sort=None,
                axis=alt.Axis(labelAngle=0)),
        y=alt.Y("sample:N", title=None, sort=None),
    )

    cells = base.mark_rect().encode(
        color=alt.Color(
            "Strength:Q",
            scale=alt.Scale(domain=[0, 3], scheme="blues"),
            legend=alt.Legend(title="0 none - 3 extensive"),
        ),
        tooltip=["sample", "Dimension", "Strength"],
    )

    labels = base.mark_text(fontSize=13).encode(
        text="Strength:Q",
        color=alt.condition(
            alt.datum.Strength >= 2,
            alt.value("white"),
            alt.value("black"),
        ),
    )

    return (cells + labels).properties(
        height=max(120, 34 * len(profile_rows))
    )


def presence_heatmap_chart(presence_rows):
    """
    RQ1 heatmap: artifact counts present in each final DOCX.
    """

    long_dataframe = pd.DataFrame(presence_rows).melt(
        id_vars="sample",
        var_name="Artifact",
        value_name="Count",
    )

    base = alt.Chart(long_dataframe).encode(
        x=alt.X("Artifact:N", title=None, sort=None,
                axis=alt.Axis(labelAngle=-30)),
        y=alt.Y("sample:N", title=None, sort=None),
    )

    cells = base.mark_rect().encode(
        color=alt.Color(
            "Count:Q",
            scale=alt.Scale(scheme="greens"),
        ),
        tooltip=["sample", "Artifact", "Count"],
    )

    labels = base.mark_text(fontSize=12).encode(text="Count:Q")

    return (cells + labels).properties(
        height=max(120, 34 * len(presence_rows))
    )


def survival_heatmap_chart(survival_rows):
    """
    RQ3 heatmap: share of each parent artifact group still present
    after the transformation (red = lost, green = survived).
    """

    dataframe = pd.DataFrame(survival_rows).copy()

    dataframe["Transformation"] = (
        dataframe["transformation"] + "  (" + dataframe["sample"] + ")"
    )

    dataframe["Label"] = dataframe["survival_rate"].apply(
        lambda v: "-" if pd.isna(v) else f"{v:.0%}"
    )

    base = alt.Chart(dataframe).encode(
        x=alt.X("artifact:N", title=None, sort=None,
                axis=alt.Axis(labelAngle=-30)),
        y=alt.Y("Transformation:N", title=None, sort=None),
    )

    cells = base.mark_rect().encode(
        color=alt.Color(
            "survival_rate:Q",
            scale=alt.Scale(domain=[0, 1], scheme="redyellowgreen"),
            legend=alt.Legend(title="survival", format="%"),
        ),
        tooltip=[
            "Transformation", "artifact", "parent_count",
            "child_count", "retained", "introduced",
            alt.Tooltip("survival_rate:Q", format=".0%"),
        ],
    )

    labels = base.mark_text(fontSize=12).encode(text="Label:N")

    return (cells + labels).properties(
        height=max(120, 36 * dataframe["Transformation"].nunique())
    )


def confusion_heatmap_chart(title, confusion):
    """Confusion matrix (rows = ground truth, columns = predicted)."""

    labels = [SHORT_CATEGORY.get(c, c) for c in confusion["labels"]]

    rows = []

    for i, truth in enumerate(labels):
        for j, predicted in enumerate(labels):
            rows.append({
                "Ground truth": truth,
                "Predicted": predicted,
                "Samples": confusion["matrix"][i][j],
            })

    base = alt.Chart(pd.DataFrame(rows)).encode(
        x=alt.X("Predicted:N", sort=labels,
                axis=alt.Axis(labelAngle=-30)),
        y=alt.Y("Ground truth:N", sort=labels),
    )

    cells = base.mark_rect().encode(
        color=alt.Color("Samples:Q", scale=alt.Scale(scheme="purples"),
                        legend=None),
        tooltip=["Ground truth", "Predicted", "Samples"],
    )

    text = base.mark_text(fontSize=13).encode(text="Samples:Q")

    return (cells + text).properties(title=title, height=220)


# ---------------------------------------------------------
# Dashboard heading
# ---------------------------------------------------------

st.title(
    "🔎 DOCX Edit-Trail Analyser"
)

st.caption(
    "Visual investigation of selected edit-related "
    "artifacts retained within DOCX files."
)

st.info(
    "This tool reports observed OOXML artifacts and "
    "contextual metadata. It does not determine whether "
    "a document is authentic, forged, or identify the "
    "physical person who edited it."
)


# ---------------------------------------------------------
# Analysis mode
# ---------------------------------------------------------

st.sidebar.header("Analysis settings")

st.sidebar.selectbox(
    "RSID counting rule",
    RSID_SCOPES,
    index=0,
    key="rsid_scope",
    help=(
        "document: count RSIDs referenced in word/document.xml "
        "(default).\n\n"
        "content: as document, but ignore RSIDs on section "
        "properties (w:sectPr), which templates copy into new "
        "files.\n\n"
        "all: also count RSIDs that appear only in the settings "
        "table (prototype rule)."
    ),
)

st.sidebar.caption(
    "The rule changes which RSIDs count towards the "
    "multiple-RSID category and the RSID score. The corpus view "
    "always reports all three rules side by side."
)

analysis_mode = st.radio(
    "Analysis mode",
    [
        "Single Document",
        "Corpus Comparison",
    ],
    horizontal=True,
)


# ---------------------------------------------------------
# File upload
# ---------------------------------------------------------

uploaded_files = st.file_uploader(
    "Select one or more DOCX files to analyse",
    type=["docx"],
    accept_multiple_files=True,
)


if not uploaded_files:

    st.markdown(
        """
        ### Evidence currently examined

        The analyser currently examines:

        - RSID root and RSID table values
        - RSID attributes retained in `word/document.xml`
        - retained insertions and deletions
        - revision author and date metadata where present
        - creator and last-modifier metadata
        - package creation and modification timestamps
        - declared editing application information

        Upload one or more DOCX files to begin.
        """
    )

    st.stop()


# =========================================================
# CORPUS COMPARISON MODE
# =========================================================

if analysis_mode == "Corpus Comparison":

    if len(uploaded_files) < 2:

        st.warning(
            "Upload at least two DOCX files "
            "for corpus comparison."
        )

        st.stop()

    comparison_engine = (
        CorpusComparison()
    )

    ground_truth_evaluator = (
        GroundTruthEvaluator()
    )

    analysed_samples = {}

    ground_truth_records = {}

    # -----------------------------------------------------
    # Analyse uploaded corpus
    # -----------------------------------------------------

    for uploaded_file in uploaded_files:

        try:

            evidence = analyse_uploaded_file(
                uploaded_file
            )

            analysed_samples[
                uploaded_file.name
            ] = evidence

            ground_truth = (
                load_ground_truth_for_docx(
                    uploaded_file.name
                )
            )

            if ground_truth is not None:

                ground_truth_records[
                    uploaded_file.name
                ] = ground_truth

        except (
            FileNotFoundError,
            ValueError
        ) as error:

            st.error(
                f"{uploaded_file.name}: "
                f"{error}"
            )

    if not analysed_samples:

        st.error(
            "No uploaded DOCX files could "
            "be analysed."
        )

        st.stop()

    # -----------------------------------------------------
    # Create comparison data
    # -----------------------------------------------------

    records = (
        comparison_engine
        .create_comparison_records(
            analysed_samples
        )
    )

    artifact_matrix = (
        comparison_engine
        .create_artifact_matrix(
            records
        )
    )

    comparison_dataframe = (
        pd.DataFrame(
            records
        )
    )

    matrix_dataframe = (
        pd.DataFrame(
            artifact_matrix
        )
    )

    # -----------------------------------------------------
    # Heading
    # -----------------------------------------------------

    st.divider()

    st.header(
        "Controlled Corpus Comparison"
    )

    st.caption(
        "Comparison of observed edit-related "
        "artifacts across the selected DOCX samples."
    )

    st.info(
        "The comparison view highlights observable "
        "differences between samples. These differences "
        "must be interpreted against known ground truth "
        "when the files belong to a controlled corpus."
    )

    # -----------------------------------------------------
    # Corpus metrics
    # -----------------------------------------------------

    total_samples = len(
        comparison_dataframe
    )

    total_revisions = (
        comparison_dataframe[
            "retained_revisions"
        ].sum()
    )

    samples_with_revisions = (
        comparison_dataframe[
            "retained_revisions"
        ] > 0
    ).sum()

    total_distinct_rsid_observations = (
        comparison_dataframe[
            "distinct_rsids"
        ].sum()
    )

    metric_1, metric_2, metric_3, metric_4 = (
        st.columns(4)
    )

    metric_1.metric(
        "Samples Analysed",
        total_samples,
    )

    metric_2.metric(
        "Retained Revisions",
        int(total_revisions),
    )

    metric_3.metric(
        "Samples With Revisions",
        int(samples_with_revisions),
    )

    metric_4.metric(
        "Combined Distinct-RSID Counts",
        int(
            total_distinct_rsid_observations
        ),
    )

    # -----------------------------------------------------
    # Evidence comparison table
    # -----------------------------------------------------

    st.subheader(
        "Evidence Comparison"
    )

    display_columns = [
        "sample",
        "distinct_rsids",
        "document_rsid_attributes",
        "retained_revisions",
        "insertions",
        "deletions",
        "modified",
        "classification",
    ]

    st.dataframe(
        comparison_dataframe[
            display_columns
        ],
        width="stretch",
        hide_index=True,
    )

    # -----------------------------------------------------
    # Artifact count chart
    # -----------------------------------------------------

    st.subheader(
        "Observed Artifact Counts"
    )

    st.markdown(
        """
        This chart compares quantities of selected
        artifacts observed in each final DOCX package.
        """
    )

    chart_dataframe = (
        comparison_dataframe[
            [
                "sample",
                "distinct_rsids",
                "document_rsid_attributes",
                "retained_revisions",
                "insertions",
                "deletions",
            ]
        ]
        .set_index(
            "sample"
        )
    )

    st.bar_chart(
        chart_dataframe
    )

    # -----------------------------------------------------
    # Revision comparison
    # -----------------------------------------------------

    st.subheader(
        "Retained Revision Comparison"
    )

    revision_chart = (
        comparison_dataframe[
            [
                "sample",
                "insertions",
                "deletions",
            ]
        ]
        .set_index(
            "sample"
        )
    )

    st.bar_chart(
        revision_chart
    )

    # -----------------------------------------------------
    # Evidence profile comparison (non-binary view)
    # -----------------------------------------------------

    st.subheader(
        "Evidence Profile Comparison"
    )

    st.markdown(
        """
        Each sample is scored independently across three
        evidence dimensions (0 = none observed, 3 = extensive).
        A sample can score on more than one dimension at once —
        this view is deliberately **not** a single "edited" /
        "not edited" verdict, but a profile of what was
        observed across all selected artifact types.
        """
    )

    profile_rows = []

    for sample_name, evidence in analysed_samples.items():

        profile = evidence.get("evidence_profile", {})

        profile_rows.append({
            "sample": sample_name,
            "Retained Revisions": profile.get(
                "revision_evidence", {}
            ).get("score", 0),
            "RSID Pattern": profile.get(
                "rsid_evidence", {}
            ).get("score", 0),
            "Context Metadata": profile.get(
                "metadata_evidence", {}
            ).get("score", 0),
        })

    st.altair_chart(
        corpus_profile_chart(profile_rows),
        width="stretch",
    )

    st.markdown(
        "**Evidence fingerprint.** The same scores as a heatmap: "
        "read each row as one document's evidence fingerprint. "
        "Documents with similar histories should look alike, and "
        "a document can be dark in several columns at once."
    )

    st.altair_chart(
        profile_heatmap_chart(profile_rows),
        width="stretch",
    )

    st.dataframe(
        pd.DataFrame(profile_rows),
        width="stretch",
        hide_index=True,
    )

    # -----------------------------------------------------
    # Artifact matrix
    # -----------------------------------------------------

    st.subheader(
        "Artifact Presence Heatmap (RQ1)"
    )

    st.markdown(
        "How many of each selected artifact survive in each final "
        "DOCX. Counts are shown, not a yes/no verdict."
    )

    corpus_results = evaluate_corpus(
        analysed_samples,
        ground_truth_records,
    )

    st.altair_chart(
        presence_heatmap_chart(corpus_results["presence"]),
        width="stretch",
    )

    st.subheader(
        "Artifact Detection Matrix"
    )

    st.markdown(
        """
        The matrix shows whether selected artifact
        categories were observed in each sample.

        A ✓ indicates that the selected artifact was
        observed. A — indicates that it was not observed.
        """
    )

    readable_matrix = (
        matrix_dataframe.rename(
            columns={
                "sample":
                    "Sample",

                "rsid_evidence":
                    "RSID Evidence",

                "document_rsid_attributes":
                    "Document RSID Attributes",

                "retained_insertion":
                    "Retained Insertion",

                "retained_deletion":
                    "Retained Deletion",

                "creator_metadata":
                    "Creator Metadata",

                "modified_metadata":
                    "Modified Metadata",

                "application_metadata":
                    "Application Metadata",
            }
        )
    )

    readable_matrix = (
        readable_matrix.replace(
            {
                True: "✓",
                False: "—",
            }
        )
    )

    st.dataframe(
        readable_matrix,
        width="stretch",
        hide_index=True,
    )

    # -----------------------------------------------------
    # Metadata timestamp comparison
    # -----------------------------------------------------

    st.subheader(
        "Metadata Timestamp Comparison"
    )

    st.markdown(
        """
        Package timestamps are displayed as contextual
        metadata only. They should not be treated as a
        complete or independently verified chronology.
        """
    )

    timestamp_dataframe = (
        comparison_dataframe[
            [
                "sample",
                "created",
                "modified",
                "creator",
                "last_modified_by",
                "application",
            ]
        ]
    )

    st.dataframe(
        timestamp_dataframe,
        width="stretch",
        hide_index=True,
    )

    # -----------------------------------------------------
    # Classification comparison
    # -----------------------------------------------------

    st.subheader(
        "Evidence Pattern Comparison"
    )

    classification_dataframe = (
        comparison_dataframe[
            [
                "sample",
                "classification",
            ]
        ]
    )

    st.dataframe(
        classification_dataframe,
        width="stretch",
        hide_index=True,
    )

    # =====================================================
    # GROUND-TRUTH EVALUATION
    # =====================================================

    st.divider()

    st.header(
        "Ground-Truth Evaluation"
    )

    st.caption(
        "Comparison of extracted artifacts against "
        "the known controlled actions and expectations "
        "recorded for the research corpus."
    )

    if not ground_truth_records:

        st.warning(
            "No matching ground-truth JSON records "
            "were found in samples/ground_truth."
        )

    else:

        # -------------------------------------------------
        # Evaluate all matched samples
        # -------------------------------------------------

        evaluations = {}

        total_evaluated = 0
        total_matched = 0
        total_mismatched = 0
        total_not_evaluated = 0

        summary_rows = []

        for sample_name, ground_truth in (
            ground_truth_records.items()
        ):

            evidence = analysed_samples[
                sample_name
            ]

            evaluation = (
                ground_truth_evaluator
                .evaluate_sample(
                    ground_truth,
                    evidence,
                    resolve_baseline(
                        sample_name,
                        ground_truth,
                        analysed_samples,
                        ground_truth_records,
                    )
                )
            )

            evaluations[
                sample_name
            ] = evaluation

            total_evaluated += (
                evaluation[
                    "evaluated_count"
                ]
            )

            total_matched += (
                evaluation[
                    "matched_count"
                ]
            )

            total_mismatched += (
                evaluation[
                    "mismatched_count"
                ]
            )

            total_not_evaluated += (
                evaluation[
                    "not_evaluated_count"
                ]
            )

            summary_rows.append({
                "Sample":
                    sample_name,

                "Evaluated":
                    evaluation[
                        "evaluated_count"
                    ],

                "Matched":
                    evaluation[
                        "matched_count"
                    ],

                "Mismatched":
                    evaluation[
                        "mismatched_count"
                    ],

                "Not Evaluated":
                    evaluation[
                        "not_evaluated_count"
                    ],
            })

        # -------------------------------------------------
        # Evaluation metrics
        # -------------------------------------------------

        eval_metric_1, \
        eval_metric_2, \
        eval_metric_3, \
        eval_metric_4 = st.columns(4)

        eval_metric_1.metric(
            "Evaluated Expectations",
            total_evaluated,
        )

        eval_metric_2.metric(
            "Matched",
            total_matched,
        )

        eval_metric_3.metric(
            "Mismatched",
            total_mismatched,
        )

        eval_metric_4.metric(
            "Not Evaluated",
            total_not_evaluated,
        )

        # -------------------------------------------------
        # Evaluation summary
        # -------------------------------------------------

        st.subheader(
            "Evaluation Summary"
        )

        evaluation_summary_df = (
            pd.DataFrame(
                summary_rows
            )
        )

        st.dataframe(
            evaluation_summary_df,
            width="stretch",
            hide_index=True,
        )

        # -------------------------------------------------
        # Match / mismatch chart
        # -------------------------------------------------

        st.subheader(
            "Ground-Truth Agreement"
        )

        agreement_chart = (
            evaluation_summary_df[
                [
                    "Sample",
                    "Matched",
                    "Mismatched",
                    "Not Evaluated",
                ]
            ]
            .set_index(
                "Sample"
            )
        )

        st.bar_chart(
            agreement_chart
        )

        # -------------------------------------------------
        # Research metrics (proposal evaluation measures)
        # -------------------------------------------------

        st.subheader(
            "Research Metrics"
        )

        st.caption(
            "Precision, recall, false-positive rate, artifact "
            "survival rate and correlation benefit, computed only "
            "from expectations stated in the ground-truth JSON."
        )

        research_metrics = (
            ResearchMetrics().evaluate_corpus(
                analysed_samples,
                ground_truth_records
            )
        )

        labelled = research_metrics["labelled_samples"]

        if labelled < 10:

            st.warning(
                f"Only {labelled} sample(s) have a ground-truth "
                f"classification label. Classification metrics "
                f"and correlation benefit rest on this few "
                f"samples and are illustrative only; a larger "
                f"controlled corpus is required before drawing "
                f"conclusions about research question 2."
            )

        benefit = research_metrics["correlation_benefit"]

        if benefit is not None:

            benefit_col_1, benefit_col_2, benefit_col_3 = (
                st.columns(3)
            )

            benefit_col_1.metric(
                "Rule-based accuracy",
                format_metric(benefit["rule_accuracy"]),
            )

            benefit_col_2.metric(
                "Metadata-only baseline accuracy",
                format_metric(benefit["baseline_accuracy"]),
            )

            benefit_col_3.metric(
                "Correlation benefit",
                format_metric(benefit["benefit"]),
            )

            st.caption(
                "The baseline sees only core/application "
                "metadata, so it can predict only two of the "
                "four categories. Benefit = rule-based accuracy "
                "minus baseline accuracy on the same "
                f"{benefit['samples']} labelled sample(s)."
            )

            class_rows = []

            report = research_metrics["classification"]

            for label, values in report["per_class"].items():

                class_rows.append({
                    "Category": label,
                    "Support": values["support"],
                    "Precision": format_metric(values["precision"]),
                    "Recall": format_metric(values["recall"]),
                    "False-positive rate": format_metric(
                        values["false_positive_rate"]
                    ),
                })

            st.write("**Per-category results (rule-based):**")

            st.dataframe(
                pd.DataFrame(class_rows),
                width="stretch",
                hide_index=True,
            )

        else:

            st.info(
                "No ground-truth record states an expected "
                "classification, so classification metrics and "
                "correlation benefit are not available."
            )

        artifact_metric_rows = []

        for name, values in research_metrics["artifacts"].items():

            artifact_metric_rows.append({
                "Artifact": name,
                "Samples": values["samples"],
                "Precision": format_metric(values["precision"]),
                "Recall": format_metric(values["recall"]),
                "False-positive rate": format_metric(
                    values["false_positive_rate"]
                ),
                "Survival rate": format_metric(
                    values["survival_rate"]
                ),
            })

        if artifact_metric_rows:

            st.write("**Artifact detection and survival:**")

            st.dataframe(
                pd.DataFrame(artifact_metric_rows),
                width="stretch",
                hide_index=True,
            )

            st.caption(
                "Survival rate = fraction of the artifacts the "
                "controlled actions should have left that were "
                "observed in the final DOCX. RSID and metadata "
                "survival are not computed because the current "
                "ground truth states no expectations for them."
            )

        # -------------------------------------------------
        # RSID rule ablation and confusion matrices (RQ2)
        # -------------------------------------------------

        if corpus_results["labelled_samples"]:

            st.subheader(
                "Classification by Rule (RQ2 Ablation)"
            )

            st.markdown(
                "Accuracy of the rule-based correlation under each "
                "RSID counting rule, against the metadata-only "
                "baseline, on the same labelled samples. *Template "
                "FP* counts negative-control samples (independent "
                "documents from the same template) that a rule "
                "wrongly placed in the multiple-RSID category."
            )

            ablation_rows = []

            for rule, values in corpus_results["ablation"].items():

                ablation_rows.append({
                    "Rule": rule,
                    "Accuracy": format_metric(values.get("accuracy")),
                    "Accuracy value": values.get("accuracy") or 0,
                    "Template FP": (
                        f"{values['negative_control_rsid_false_positives']}"
                        f" / {values['negative_controls']}"
                        if "negative_controls" in values else "n/a"
                    ),
                })

            ablation_dataframe = pd.DataFrame(ablation_rows)

            st.altair_chart(
                alt.Chart(ablation_dataframe).mark_bar().encode(
                    x=alt.X("Rule:N", sort=None, title=None,
                            axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("Accuracy value:Q",
                            scale=alt.Scale(domain=[0, 1]),
                            title="Accuracy"),
                    color=alt.condition(
                        alt.datum.Rule == "metadata-only baseline",
                        alt.value("#BBBBBB"),
                        alt.value("#4C72B0"),
                    ),
                    tooltip=["Rule", "Accuracy", "Template FP"],
                ).properties(height=220),
                width="stretch",
            )

            st.dataframe(
                ablation_dataframe.drop(columns=["Accuracy value"]),
                width="stretch",
                hide_index=True,
            )

            st.subheader("Confusion Matrices")

            st.caption(
                "Rows are the category the controlled history "
                "justifies; columns are what the tool reported. "
                "Everything on the diagonal is correct."
            )

            confusion_items = list(
                corpus_results["confusion"].items()
            )

            for start in range(0, len(confusion_items), 2):

                columns = st.columns(2)

                for column, (title, confusion) in zip(
                    columns, confusion_items[start:start + 2]
                ):
                    column.altair_chart(
                        confusion_heatmap_chart(title, confusion),
                        width="stretch",
                    )

        # -------------------------------------------------
        # Artifact survival after transformations (RQ3)
        # -------------------------------------------------

        st.subheader(
            "Artifact Survival After Transformations (RQ3)"
        )

        if corpus_results["survival"]:

            st.markdown(
                "Each row compares a sample with the parent it was "
                "derived from (`derived_from` in its ground truth). "
                "A cell shows what share of the parent's artifacts "
                "of that type are still present, unchanged, after "
                "the transformation. Green = survived, red = lost, "
                "'-' = the parent had none to lose."
            )

            st.altair_chart(
                survival_heatmap_chart(corpus_results["survival"]),
                width="stretch",
            )

            with st.expander("Survival table"):

                st.dataframe(
                    pd.DataFrame(corpus_results["survival"]),
                    width="stretch",
                    hide_index=True,
                )

        else:

            st.info(
                "No uploaded sample names a parent (derived_from) "
                "that was also uploaded, so survival cannot be "
                "computed. Upload each transformed sample together "
                "with its parent."
            )

        # -------------------------------------------------
        # Important methodological interpretation
        # -------------------------------------------------

        st.subheader(
            "Controlled Experiment Interpretation"
        )

        st.info(
            "A successful ground-truth match means "
            "that the analyser correctly observed the "
            "artifact that the controlled corpus expected. "
            "It does not mean that the analyser has "
            "reconstructed the complete editing history."
        )

        edited_ground_truth = None

        for ground_truth in (
            ground_truth_records.values()
        ):

            if (
                ground_truth.get(
                    "sample_id"
                )
                == "02_edited"
            ):

                edited_ground_truth = (
                    ground_truth
                )

                break

        if edited_ground_truth is not None:

            st.warning(
                "The 02_edited sample contains known "
                "controlled editing actions while its "
                "ground truth expects zero retained "
                "insertions and zero retained deletions. "
                "This demonstrates why the absence of "
                "retained tracked-change markup cannot "
                "be interpreted as proof that a document "
                "was never edited."
            )

        st.warning(
            "RSID observations are not scored where "
            "the controlled ground truth explicitly "
            "makes no claim about RSID behaviour."
        )

        # -------------------------------------------------
        # Detailed evaluations
        # -------------------------------------------------

        st.subheader(
            "Per-Sample Ground-Truth Results"
        )

        for sample_name, evaluation in (
            evaluations.items()
        ):

            with st.expander(
                sample_name
            ):

                st.write(
                    "**Creation method:**"
                )

                st.write(
                    evaluation.get(
                        "creation_method"
                    )
                    or "Not recorded"
                )

                controlled_actions = (
                    evaluation.get(
                        "controlled_actions",
                        []
                    )
                )

                if controlled_actions:

                    st.write(
                        "**Controlled actions:**"
                    )

                    for action in (
                        controlled_actions
                    ):

                        st.write(
                            f"• {action}"
                        )

                st.write(
                    "**Expected vs observed:**"
                )

                evaluation_df = (
                    create_evaluation_dataframe(
                        evaluation
                    )
                )

                st.dataframe(
                    evaluation_df,
                    width="stretch",
                    hide_index=True,
                )

                limitations = (
                    evaluation.get(
                        "research_limitations",
                        []
                    )
                )

                if limitations:

                    st.write(
                        "**Research limitations:**"
                    )

                    for limitation in limitations:

                        st.warning(
                            limitation
                        )

        # -------------------------------------------------
        # Coverage note
        # -------------------------------------------------

        unmatched_samples = [
            sample_name
            for sample_name
            in analysed_samples
            if sample_name
            not in ground_truth_records
        ]

        if unmatched_samples:

            st.warning(
                "The following uploaded sample(s) "
                "did not have matching ground-truth "
                "JSON files and were therefore not "
                "ground-truth evaluated: "
                + ", ".join(
                    unmatched_samples
                )
            )

    # -----------------------------------------------------
    # Comparative interpretation
    # -----------------------------------------------------

    st.divider()

    st.subheader(
        "Comparative Interpretation"
    )

    st.info(
        "This comparison displays differences "
        "between observed artifacts in the selected "
        "samples. It does not establish that one "
        "sample is authentic, forged, edited, or "
        "unedited."
    )

    st.warning(
        "RSID counts must not be interpreted as "
        "direct counts of edits, editing sessions, "
        "or editors."
    )

    st.warning(
        "The absence of retained revision markup "
        "does not establish that a document was "
        "never edited."
    )

    # -----------------------------------------------------
    # Per-sample evidence details
    # -----------------------------------------------------

    st.subheader(
        "Individual Sample Evidence Details"
    )

    for sample_name, evidence in (
        analysed_samples.items()
    ):

        with st.expander(
            sample_name
        ):

            classification = evidence[
                "classification"
            ]

            st.write(
                "**Strongest observed evidence pattern:**"
            )

            st.code(
                classification[
                    "category"
                ]
            )

            st.write(
                "**Distinct RSIDs:** "
                f"{len(evidence['unique_rsids'])}"
            )

            st.write(
                "**Document RSID attributes:** "
                f"{len(evidence['document_rsids'])}"
            )

            st.write(
                "**Retained revisions:** "
                f"{len(evidence['revisions'])}"
            )

            st.write(
                "**Basis:**"
            )

            for item in classification[
                "basis"
            ]:

                st.write(
                    f"• {item}"
                )

            st.write(
                "**Interpretive limitations:**"
            )

            for item in classification[
                "limitations"
            ]:

                st.write(
                    f"• {item}"
                )

    st.divider()

    st.caption(
        "DOCX Edit-Trail Analyser — "
        "Controlled Corpus Comparison"
    )

    st.stop()


# =========================================================
# SINGLE DOCUMENT MODE
# =========================================================

uploaded_file = uploaded_files[0]


try:

    evidence = analyse_uploaded_file(
        uploaded_file
    )

except (
    FileNotFoundError,
    ValueError
) as error:

    st.error(
        f"Unable to analyse DOCX file: {error}"
    )

    st.stop()


# ---------------------------------------------------------
# File heading
# ---------------------------------------------------------

st.divider()

st.subheader(
    uploaded_file.name
)

st.caption(
    "Observed evidence from the uploaded DOCX package."
)


# ---------------------------------------------------------
# Main evidence overview
# ---------------------------------------------------------

st.header(
    "Evidence Overview"
)

metric_1, metric_2, metric_3, metric_4 = (
    st.columns(4)
)

with metric_1:

    st.metric(
        "Distinct RSIDs",
        len(
            evidence["unique_rsids"]
        ),
    )

with metric_2:

    st.metric(
        "RSID Attributes",
        len(
            evidence["document_rsids"]
        ),
    )

with metric_3:

    st.metric(
        "Retained Revisions",
        len(
            evidence["revisions"]
        ),
    )

metadata_count = sum(
    1
    for value in (
        list(
            evidence[
                "core_properties"
            ].values()
        )
        +
        list(
            evidence[
                "app_properties"
            ].values()
        )
    )
    if value
)

with metric_4:

    st.metric(
        "Metadata Values",
        metadata_count,
    )


# ---------------------------------------------------------
# Evidence profile
# ---------------------------------------------------------

st.subheader(
    "Artifact Profile"
)

artifact_profile = pd.DataFrame(
    {
        "Artifact": [
            "Distinct RSIDs",
            "RSID attributes",
            "Retained revisions",
            "Metadata values",
        ],
        "Observed": [
            len(
                evidence[
                    "unique_rsids"
                ]
            ),
            len(
                evidence[
                    "document_rsids"
                ]
            ),
            len(
                evidence[
                    "revisions"
                ]
            ),
            metadata_count,
        ],
    }
)

st.bar_chart(
    artifact_profile,
    x="Artifact",
    y="Observed",
    horizontal=True,
)


# ---------------------------------------------------------
# Tabs
# ---------------------------------------------------------

(
    rsid_tab,
    revision_tab,
    metadata_tab,
    interpretation_tab,
    package_tab,
) = st.tabs(
    [
        "RSID Evidence",
        "Revision Evidence",
        "Metadata",
        "Interpretation",
        "Package Details",
    ]
)


# =========================================================
# RSID TAB
# =========================================================

with rsid_tab:

    st.header(
        "RSID Evidence"
    )

    st.markdown(
        """
        RSIDs are revision save identifiers retained
        within parts of the WordprocessingML package.

        They can provide useful relationship and editing
        context, but they are **not a complete chronological
        history** and should not be interpreted as a direct
        count of editors or editing sessions.
        """
    )

    st.subheader(
        "RSID Root"
    )

    if evidence["rsid_root"]:

        st.code(
            evidence["rsid_root"]
        )

    else:

        st.warning(
            "No rsidRoot value was observed."
        )

    st.subheader(
        "RSID Table"
    )

    if evidence["rsid_table"]:

        rsid_table_data = pd.DataFrame(
            {
                "RSID":
                    evidence[
                        "rsid_table"
                    ]
            }
        )

        st.dataframe(
            rsid_table_data,
            width="stretch",
            hide_index=True,
        )

    else:

        st.info(
            "No RSID table entries were observed."
        )

    st.subheader(
        "Document RSID Attributes"
    )

    if evidence["document_rsids"]:

        document_rsid_rows = []

        for item in evidence[
            "document_rsids"
        ]:

            document_rsid_rows.append({
                "Element":
                    simplify_element_name(
                        item["element"]
                    ),

                "Attribute":
                    item["attribute"],

                "RSID":
                    item["value"],
            })

        st.dataframe(
            pd.DataFrame(
                document_rsid_rows
            ),
            width="stretch",
            hide_index=True,
        )

    else:

        st.info(
            "No selected RSID attributes were "
            "observed in word/document.xml."
        )

    # -----------------------------------------------------
    # RSID occurrence map
    # -----------------------------------------------------

    st.subheader(
        "RSID Occurrence Map"
    )

    rsid_occurrences = (
        create_rsid_occurrence_table(
            evidence["rsid_root"],
            evidence["rsid_table"],
            evidence[
                "document_rsids"
            ],
        )
    )

    if not rsid_occurrences.empty:

        st.bar_chart(
            rsid_occurrences,
            x="RSID",
            y="Occurrences",
        )

        st.dataframe(
            rsid_occurrences,
            width="stretch",
            hide_index=True,
        )

    # -----------------------------------------------------
    # RSID relationship view
    # -----------------------------------------------------

    st.subheader(
        "RSID Relationship View"
    )

    st.markdown(
        """
        This view shows where each distinct RSID is
        observed across the selected OOXML artifacts.

        It distinguishes identifiers recorded in the
        settings RSID table from identifiers actually
        referenced by the selected attributes in
        `word/document.xml`.
        """
    )

    relationship_table = (
        create_rsid_relationship_table(
            evidence["rsid_root"],
            evidence["rsid_table"],
            evidence["document_rsids"],
        )
    )

    if not relationship_table.empty:

        settings_only_count = len(
            relationship_table[
                (
                    relationship_table[
                        "Settings Table"
                    ] == "Yes"
                )
                &
                (
                    relationship_table[
                        "Document"
                    ] == "No"
                )
            ]
        )

        document_count = len(
            relationship_table[
                relationship_table[
                    "Document"
                ] == "Yes"
            ]
        )

        root_count = len(
            relationship_table[
                relationship_table[
                    "Root"
                ] == "Yes"
            ]
        )

        relationship_col_1, \
        relationship_col_2, \
        relationship_col_3 = st.columns(3)

        relationship_col_1.metric(
            "Root Identifiers",
            root_count,
        )

        relationship_col_2.metric(
            "Referenced in Document",
            document_count,
        )

        relationship_col_3.metric(
            "Settings Only",
            settings_only_count,
        )

        st.dataframe(
            relationship_table,
            width="stretch",
            hide_index=True,
        )

        if settings_only_count > 0:

            st.info(
                f"{settings_only_count} RSID value(s) "
                f"were present in the settings table "
                f"but were not referenced by the "
                f"selected RSID attributes examined "
                f"in word/document.xml."
            )

        st.warning(
            "These relationships describe observed "
            "locations only. They do not establish "
            "chronological order, the number of edit "
            "sessions, or the identity of an editor."
        )


# =========================================================
# REVISION TAB
# =========================================================

with revision_tab:

    st.header(
        "Retained Revision Evidence"
    )

    st.markdown(
        """
        This section displays retained tracked-change
        structures: content insertions and deletions
        (`w:ins`, `w:del`), plus the other markers Word writes
        when Track Changes is on: paragraph-mark revisions
        (`w:ins`/`w:del` inside `w:rPr`), moves (`w:moveFrom`,
        `w:moveTo`) and formatting changes (`w:rPrChange`,
        `w:pPrChange`, ...).

        Their presence provides stronger direct evidence
        of retained revision markup than RSID counts alone,
        but they still do not reconstruct every historical
        edit performed on the document.
        """
    )

    if evidence["revisions"]:

        revision_rows = []

        insertion_count = 0
        deletion_count = 0

        for index, revision in enumerate(
            evidence["revisions"],
            start=1
        ):

            if (
                revision["type"]
                == "insertion"
            ):

                insertion_count += 1

            elif (
                revision["type"]
                == "deletion"
            ):

                deletion_count += 1

            revision_rows.append({
                "Observed Record":
                    index,

                "Type":
                    revision["type"],

                "Element":
                    revision.get("element"),

                "Revision ID":
                    revision.get("revision_id"),

                "Declared Author":
                    revision["author"],

                "Declared Date":
                    revision["date"],

                "Retained Text":
                    revision["text"],
            })

        other_count = (
            len(evidence["revisions"])
            - insertion_count
            - deletion_count
        )

        revision_metric_1, revision_metric_2, revision_metric_3 = (
            st.columns(3)
        )

        revision_metric_3.metric(
            "Other tracked markers",
            other_count,
            help=(
                "Paragraph-mark, table-row, move and formatting "
                "revisions. Not counted as insertions/deletions."
            ),
        )

        revision_metric_1.metric(
            "Insertions",
            insertion_count,
        )

        revision_metric_2.metric(
            "Deletions",
            deletion_count,
        )

        st.dataframe(
            pd.DataFrame(
                revision_rows
            ),
            width="stretch",
            hide_index=True,
        )

        type_counts = Counter(
            revision["type"]
            for revision in evidence["revisions"]
        )

        revision_chart = pd.DataFrame(
            {
                "Revision Type": [
                    name.replace("_", " ")
                    for name in type_counts
                ],
                "Observed": list(type_counts.values()),
            }
        )

        st.bar_chart(
            revision_chart,
            x="Revision Type",
            y="Observed",
        )

        st.warning(
            "The displayed revision records should "
            "not be treated as a complete historical "
            "timeline. Revision dates are metadata "
            "retained in the final package."
        )

    else:

        st.info(
            "No retained w:ins or w:del revision "
            "markup was observed."
        )

        st.warning(
            "The absence of retained tracked-change "
            "markup does not prove that the document "
            "was never edited."
        )


# =========================================================
# METADATA TAB
# =========================================================

with metadata_tab:

    st.header(
        "Document Context Metadata"
    )

    st.markdown(
        """
        Metadata is displayed as contextual evidence.
        These values may be editable and must not be
        treated as proof of the identity of an editor
        or as a complete editing chronology.
        """
    )

    core = evidence[
        "core_properties"
    ]

    app = evidence[
        "app_properties"
    ]

    metadata_rows = [
        {
            "Property": "Creator",
            "Value": core.get("creator"),
        },
        {
            "Property": "Last modified by",
            "Value": core.get("last_modified_by"),
        },
        {
            "Property": "Created",
            "Value": core.get("created"),
        },
        {
            "Property": "Modified",
            "Value": core.get("modified"),
        },
        {
            "Property": "Application",
            "Value": app.get("application"),
        },
        {
            "Property": "Application version",
            "Value": app.get("app_version"),
        },
    ]

    st.dataframe(
        pd.DataFrame(
            metadata_rows
        ),
        width="stretch",
        hide_index=True,
    )


# =========================================================
# INTERPRETATION TAB
# =========================================================

with interpretation_tab:

    classification = evidence[
        "classification"
    ]

    evidence_profile = evidence[
        "evidence_profile"
    ]

    st.header(
        "Evidence Interpretation"
    )

    # -------------------------------------------------
    # Evidence profile chart (non-binary, primary view)
    # -------------------------------------------------

    st.subheader(
        "Evidence Profile"
    )

    st.markdown(
        """
        The chart below scores each evidence dimension
        **independently**, from 0 (none observed) to 3
        (extensive). A document is not reduced to a single
        "edited" / "not edited" verdict — it can register on
        more than one dimension simultaneously, and the
        profile below reflects that.
        """
    )

    profile_dataframe = (
        create_evidence_profile_dataframe(
            evidence_profile
        )
    )

    st.altair_chart(
        single_profile_chart(profile_dataframe),
        width="stretch",
    )

    st.caption(
        "RSIDs are scored only when referenced in "
        "word/document.xml; settings-table-only RSIDs are "
        "noted but not scored. Metadata is scored on "
        "later-save and different-modifier signals (max 2), "
        "not on how many fields are populated."
    )

    st.table(
        profile_dataframe[
            ["Evidence Dimension", "Label", "Basis"]
        ].set_index("Evidence Dimension")
    )

    st.divider()

    # -------------------------------------------------
    # Existing categorical classification, reframed as
    # one signal among several rather than the verdict
    # -------------------------------------------------

    st.subheader(
        "Strongest Individual Evidence Pattern"
    )

    st.caption(
        "This names the single highest-priority pattern "
        "observed, for continuity with the evidence-profile "
        "chart above. It is one signal among several, not a "
        "standalone determination."
    )

    st.success(
        classification[
            "category"
        ]
    )

    st.subheader(
        "Basis"
    )

    for item in classification[
        "basis"
    ]:

        st.write(
            f"• {item}"
        )

    st.subheader(
        "Supporting Evidence Trace"
    )

    st.caption(
        "Every item behind the pattern above, located by OOXML "
        "part, XML element and attribute, so the finding can be "
        f"checked by hand. RSID rule in use: "
        f"{classification.get('rsid_scope', 'document')}."
    )

    if classification.get("evidence"):

        st.dataframe(
            pd.DataFrame(classification["evidence"]).rename(
                columns={
                    "evidence_group": "Evidence group",
                    "part": "Part",
                    "element": "Element",
                    "attribute": "Attribute",
                    "value": "Value",
                }
            ),
            width="stretch",
            hide_index=True,
        )

    else:

        st.info("No supporting artifact was observed.")

    st.subheader(
        "Interpretive Limitations"
    )

    for item in classification[
        "limitations"
    ]:

        st.warning(
            item
        )

    st.info(
        "Neither the evidence profile nor the classification "
        "above is a binary determination that the document is "
        "authentic, forged, edited, or unedited. They describe "
        "the selected artifacts observed in the final DOCX "
        "package only."
    )


# =========================================================
# PACKAGE DETAILS TAB
# =========================================================

with package_tab:

    st.header(
        "OOXML Package Details"
    )

    package_rows = []

    for part_name, content in evidence[
        "parts"
    ].items():

        package_rows.append({
            "Package Part":
                part_name,

            "Status":
                (
                    "Present"
                    if content is not None
                    else "Missing"
                ),

            "Size (bytes)":
                (
                    len(content)
                    if content is not None
                    else None
                ),
        })

    st.dataframe(
        pd.DataFrame(
            package_rows
        ),
        width="stretch",
        hide_index=True,
    )

    if evidence[
        "missing_parts"
    ]:

        st.warning(
            "One or more selected OOXML "
            "package parts were not present."
        )

    else:

        st.success(
            "All selected OOXML package "
            "parts were present."
        )


# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------

st.divider()

st.caption(
    "DOCX Edit-Trail Analyser — "
    "Digital Authenticity research prototype"
)