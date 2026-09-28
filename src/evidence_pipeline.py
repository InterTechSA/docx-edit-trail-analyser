"""
Single end-to-end analysis pipeline for one DOCX file.

    DOCX -> Package Reader -> Target XML Parser
         -> Artifact Extractor -> Correlation Engine -> evidence dict

The dashboard, the command-line tool (main.py) and the batch
evaluator (batch_evaluate.py) all call analyse_docx(), so every
interface reports exactly the same evidence for the same file.
"""

from package_reader import DocxPackageReader
from xml_parser import TargetXmlParser
from artifact_extractor import ArtifactExtractor
from correlation_engine import CorrelationEngine


def analyse_docx(file_path, rsid_scope="document"):
    """
    Run the forensic extraction pipeline against a DOCX file.

    Only the final DOCX is examined. The pipeline is never given
    the document's known history (ground truth is compared
    afterwards, by a separate evaluator).

    Returns:
        dict with keys:
            parts, missing_parts,
            rsid_root, rsid_table, document_rsids, unique_rsids,
            referenced_rsids, revisions,
            core_properties, app_properties,
            classification, evidence_profile, rsid_scope
    """

    reader = DocxPackageReader(file_path)
    parts = reader.read_selected_parts()

    parser = TargetXmlParser()
    extractor = ArtifactExtractor()

    parsed_parts = {}
    missing_parts = []

    for part_name, content in parts.items():

        if content is None:
            missing_parts.append(part_name)
            continue

        parsed_parts[part_name] = parser.parse(content)

    rsid_root = None
    rsid_table = []
    document_rsids = []
    revisions = []
    core_properties = {}
    app_properties = {}

    settings_root = parsed_parts.get("word/settings.xml")

    if settings_root is not None:
        rsid_root = extractor.extract_rsid_root(settings_root)
        rsid_table = extractor.extract_rsid_table(settings_root)

    document_root = parsed_parts.get("word/document.xml")

    if document_root is not None:
        document_rsids = extractor.extract_document_rsids(document_root)
        revisions = extractor.extract_revisions(document_root)

    core_root = parsed_parts.get("docProps/core.xml")

    if core_root is not None:
        core_properties = extractor.extract_core_properties(core_root)

    app_root = parsed_parts.get("docProps/app.xml")

    if app_root is not None:
        app_properties = extractor.extract_application_properties(
            app_root
        )

    evidence = {
        "parts": parts,
        "missing_parts": missing_parts,
        "rsid_root": rsid_root,
        "rsid_table": rsid_table,
        "document_rsids": document_rsids,
        "revisions": revisions,
        "core_properties": core_properties,
        "app_properties": app_properties,
    }

    evidence["unique_rsids"] = sorted(
        ({rsid_root} if rsid_root else set())
        | {r for r in rsid_table if r}
        | {i["value"] for i in document_rsids if i.get("value")}
    )

    evidence["referenced_rsids"] = sorted(
        {i["value"] for i in document_rsids if i.get("value")}
    )

    return correlate(evidence, rsid_scope)


def correlate(evidence, rsid_scope="document"):
    """
    (Re)run the correlation engine on already-extracted evidence.

    Used by analyse_docx() and by the RSID-scope ablation, which
    re-classifies the same extracted artifacts under a different
    rule without re-reading the file.
    """

    engine = CorrelationEngine(rsid_scope=rsid_scope)

    arguments = dict(
        rsid_root=evidence["rsid_root"],
        rsid_table=evidence["rsid_table"],
        document_rsids=evidence["document_rsids"],
        revisions=evidence["revisions"],
        core_properties=evidence["core_properties"],
        app_properties=evidence["app_properties"],
    )

    result = dict(evidence)
    result["classification"] = engine.classify(**arguments)
    result["evidence_profile"] = engine.score_evidence_dimensions(
        **arguments
    )
    result["rsid_scope"] = rsid_scope

    return result
