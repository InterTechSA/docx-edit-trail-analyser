import os
import tempfile
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st

from package_reader import DocxPackageReader
from xml_parser import TargetXmlParser
from artifact_extractor import ArtifactExtractor
from correlation_engine import CorrelationEngine


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


def analyse_docx(file_path):
    """
    Run the existing forensic extraction pipeline against
    a DOCX file and return all observed evidence.
    """

    reader = DocxPackageReader(file_path)

    parts = reader.read_selected_parts()

    parser = TargetXmlParser()

    extractor = ArtifactExtractor()

    correlation_engine = CorrelationEngine()

    parsed_parts = {}

    missing_parts = []

    # -----------------------------------------------------
    # Parse package parts
    # -----------------------------------------------------

    for part_name, content in parts.items():

        if content is None:

            missing_parts.append(part_name)

            continue

        parsed_parts[part_name] = parser.parse(content)

    # -----------------------------------------------------
    # Prepare evidence containers
    # -----------------------------------------------------

    rsid_root = None

    rsid_table = []

    document_rsids = []

    revisions = []

    core_properties = {}

    app_properties = {}

    # -----------------------------------------------------
    # RSID evidence
    # -----------------------------------------------------

    settings_root = parsed_parts.get(
        "word/settings.xml"
    )

    if settings_root is not None:

        rsid_root = extractor.extract_rsid_root(
            settings_root
        )

        rsid_table = extractor.extract_rsid_table(
            settings_root
        )

    # -----------------------------------------------------
    # Document evidence
    # -----------------------------------------------------

    document_root = parsed_parts.get(
        "word/document.xml"
    )

    if document_root is not None:

        document_rsids = (
            extractor.extract_document_rsids(
                document_root
            )
        )

        revisions = extractor.extract_revisions(
            document_root
        )

    # -----------------------------------------------------
    # Core metadata
    # -----------------------------------------------------

    core_root = parsed_parts.get(
        "docProps/core.xml"
    )

    if core_root is not None:

        core_properties = (
            extractor.extract_core_properties(
                core_root
            )
        )

    # -----------------------------------------------------
    # Application metadata
    # -----------------------------------------------------

    app_root = parsed_parts.get(
        "docProps/app.xml"
    )

    if app_root is not None:

        app_properties = (
            extractor.extract_application_properties(
                app_root
            )
        )

    # -----------------------------------------------------
    # Evidence classification
    # -----------------------------------------------------

    classification = correlation_engine.classify(
        rsid_root=rsid_root,
        rsid_table=rsid_table,
        document_rsids=document_rsids,
        revisions=revisions,
        core_properties=core_properties,
        app_properties=app_properties,
    )

    # -----------------------------------------------------
    # Unique RSIDs
    # -----------------------------------------------------

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

    return {
        "parts": parts,
        "missing_parts": missing_parts,
        "rsid_root": rsid_root,
        "rsid_table": rsid_table,
        "document_rsids": document_rsids,
        "unique_rsids": sorted(unique_rsids),
        "revisions": revisions,
        "core_properties": core_properties,
        "app_properties": app_properties,
        "classification": classification,
    }


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
        rsid for rsid in rsid_table if rsid
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
# ---------------------------------------------------------
# Dashboard heading
# ---------------------------------------------------------

st.title("🔎 DOCX Edit-Trail Analyser")

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
# File upload
# ---------------------------------------------------------

uploaded_file = st.file_uploader(
    "Select a DOCX file to analyse",
    type=["docx"],
)


if uploaded_file is None:

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

        Upload one of the controlled corpus files to begin.
        """
    )

    st.stop()


# ---------------------------------------------------------
# Save uploaded file temporarily
# ---------------------------------------------------------

temporary_path = None

try:

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".docx"
    ) as temporary_file:

        temporary_file.write(
            uploaded_file.getvalue()
        )

        temporary_path = temporary_file.name

    evidence = analyse_docx(
        temporary_path
    )

except (FileNotFoundError, ValueError) as error:

    st.error(
        f"Unable to analyse DOCX file: {error}"
    )

    st.stop()

finally:

    if (
        temporary_path
        and Path(temporary_path).exists()
    ):

        os.remove(
            temporary_path
        )


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

st.header("Evidence Overview")

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

with metric_4:

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

    st.metric(
        "Metadata Values",
        metadata_count,
    )


# ---------------------------------------------------------
# Evidence profile chart
# ---------------------------------------------------------

st.subheader("Artifact Profile")

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

    st.header("RSID Evidence")

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

    st.subheader("RSID Root")

    if evidence["rsid_root"]:

        st.code(
            evidence["rsid_root"]
        )

    else:

        st.warning(
            "No rsidRoot value was observed."
        )

    st.subheader("RSID Table")

    if evidence["rsid_table"]:

        rsid_table_data = pd.DataFrame(
            {
                "RSID": (
                    evidence[
                        "rsid_table"
                    ]
                )
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
        This view shows where each distinct RSID was
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
        structures found as `w:ins` and `w:del`.

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
                "Declared Author":
                    revision["author"],
                "Declared Date":
                    revision["date"],
                "Retained Text":
                    revision["text"],
            })

        revision_metric_1, revision_metric_2 = (
            st.columns(2)
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

        revision_chart = pd.DataFrame(
            {
                "Revision Type": [
                    "Insertion",
                    "Deletion",
                ],
                "Observed": [
                    insertion_count,
                    deletion_count,
                ],
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
            "Value": core.get(
                "creator"
            ),
        },
        {
            "Property":
                "Last modified by",
            "Value": core.get(
                "last_modified_by"
            ),
        },
        {
            "Property":
                "Created",
            "Value": core.get(
                "created"
            ),
        },
        {
            "Property":
                "Modified",
            "Value": core.get(
                "modified"
            ),
        },
        {
            "Property":
                "Application",
            "Value": app.get(
                "application"
            ),
        },
        {
            "Property":
                "Application version",
            "Value": app.get(
                "app_version"
            ),
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

    st.header(
        "Evidence Interpretation"
    )

    st.subheader(
        "Strongest Observed Evidence Pattern"
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
        "Interpretive Limitations"
    )

    for item in classification[
        "limitations"
    ]:

        st.warning(
            item
        )

    st.info(
        "The classification describes the selected "
        "artifacts observed in the final DOCX package. "
        "It is not a binary determination that the "
        "document is authentic, forged, edited, or "
        "unedited."
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
    "DOCX Edit-Trail Analyser — Digital Authenticity "
    "research prototype"
)