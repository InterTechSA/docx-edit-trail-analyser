# DOCX Edit-Trail Analyser

A digital forensics tool for extracting and correlating selected edit-related artifacts retained within Microsoft Word DOCX files.

## Overview

Microsoft Word DOCX files may retain edit-related artifacts that are not visible when viewing the document normally. These artifacts can provide useful evidence when investigating the editing history of a document.

The DOCX Edit-Trail Analyser examines selected components of a DOCX file and presents potentially relevant artifacts in an auditable evidence view.

The tool focuses on three evidence groups:

1. **RSID evidence**

   * Revision Save Identifiers (RSIDs)
   * `rsidRoot`
   * RSID table entries
   * RSID attributes associated with relevant document elements

2. **Retained revision evidence**

   * Insertions
   * Deletions
   * Revision author information where present
   * Revision timestamps where present

3. **Context evidence**

   * Document creator
   * Last modifier
   * Creation timestamp
   * Modification timestamp
   * Declared editing application

The extracted artifacts are correlated using predefined, explainable rules to assist a forensic investigator in identifying edit-related evidence that may require further investigation.

## Research Context

**Research Category:** Digital Authenticity

**Research Theme:** Read hidden edit trails in digital files

The project investigates how effectively artifacts retained within a final DOCX file can be used to identify and characterise aspects of its editing history.

A DOCX file is an Office Open XML (OOXML) package containing document content, properties, relationships, settings, and other XML structures. Some of these structures may retain artifacts associated with document editing even when they are not visible through the normal Microsoft Word interface.

The purpose of this tool is therefore not simply to extract metadata, but to correlate selected edit-related artifacts while clearly communicating the limitations of the resulting forensic inferences.

## Evidence Categories

Based on the selected artifacts observed, the analyser will place a document into one of the following evidence categories:

* **Retained tracked-revision evidence**
* **Multiple-RSID-pattern evidence**
* **Metadata-only evidence**
* **No selected edit artifact observed**

Every classification must be supported by the underlying evidence that caused it.

Where applicable, the analyser will expose information such as:

* OOXML part name
* XML element
* XML attribute
* Extracted value
* Evidence type
* Resulting evidence category

A classification represents an investigative lead or description of the observed evidence. It does not establish the complete editing history of the document.

## Scope

The first version analyses one final `.docx` file.

The following OOXML parts are examined:

```text
word/document.xml
word/settings.xml
docProps/core.xml
docProps/app.xml
```

The project is intentionally restricted to selected artifacts contained within these parts.

## Out of Scope

The DOCX Edit-Trail Analyser does **not**:

* Determine whether a document is authentic or forged
* Identify the person who edited a document
* Reconstruct every historical edit
* Treat RSIDs as a complete chronological edit log
* Determine an exact number of editing sessions from RSIDs
* Recover deleted files
* Analyse disk images
* Recover information that is no longer present in the DOCX package
* Guarantee that metadata or revision artifacts have not been altered or removed

The absence of a selected artifact should not automatically be interpreted as evidence that an event did not occur.

## Architecture

The program is divided into four primary modules:

### 1. Package Reader

Opens the DOCX OOXML package and retrieves the XML parts required by the analyser.

```text
DOCX
  |
  v
Package Reader
```

### 2. Target XML Parser

Parses the selected XML structures and identifies only the elements and attributes required by the defined evidence groups.

```text
Package Reader
      |
      v
Target XML Parser
```

### 3. Artifact Extractor

Extracts the research-defined forensic artifacts, including:

* RSIDs
* Revision markup
* Revision author and date attributes
* Core document properties
* Application properties

```text
Target XML Parser
        |
        v
Artifact Extractor
```

### 4. Correlation Engine

Applies predefined evidence rules to the extracted artifacts and produces a concise evidence view.

```text
Artifact Extractor
        |
        v
Correlation Engine
        |
        v
Evidence View
```

The complete processing flow is therefore:

```text
DOCX File
    |
    v
Package Reader
    |
    v
Target XML Parser
    |
    v
Artifact Extractor
    |
    v
Correlation Engine
    |
    v
Evidence View
```

## Project Structure

```text
docx-edit-trail-analyser/
|
|-- README.md
|-- main.py
|-- package_reader.py
|-- xml_parser.py
|-- artifact_extractor.py
|-- correlation_engine.py
|-- models.py
|
|-- samples/
|
`-- tests/
```

The structure may evolve during implementation while maintaining the four-module architecture defined by the project.

## Testing

Testing will use a controlled, self-created corpus of non-sensitive DOCX documents.

The environment and relevant variables will be recorded, including:

* Operating system
* Microsoft Word version
* Template
* Track Changes configuration
* Save procedure

Test documents will represent controlled actions and transformations such as:

* Baseline document creation
* Save without editing
* Ordinary direct editing
* Copying documents
* Tracked changes
* Accepting tracked changes
* Rejecting tracked changes
* Independent documents created from the same template
* Metadata-cleaning variants

Each test document will have separate ground-truth information describing the actions used to create it.

The analyser will process only the final DOCX file and will not be provided with the document's known history during analysis.

## Evaluation

The project will evaluate:

* Extraction correctness
* Precision
* Recall
* False-positive rate
* Artifact survival rate
* Correlation benefit

The evaluation is intended to determine both the usefulness and limitations of the selected artifacts for forensic analysis.

## Forensic Interpretation

RSIDs, revision markup, and document metadata must be interpreted cautiously.

For example, the presence of multiple RSIDs may provide an investigative lead, but it does not prove that multiple people edited the document or establish an exact number of editing sessions.

Similarly, creator names, last-modifier values, and timestamps are contextual artifacts rather than independent proof of authorship or authenticity.

The analyser therefore prioritises **evidence transparency and explainability**. Where the tool makes a classification, the investigator should be able to inspect the artifacts responsible for that result.

## Status

**Current status:** Initial development

Planned implementation sequence:

* [ ] Package Reader
* [ ] Target XML Parser
* [ ] Artifact Extractor
* [ ] RSID extraction
* [ ] Retained revision extraction
* [ ] Context metadata extraction
* [ ] Correlation Engine
* [ ] Evidence view
* [ ] Controlled test corpus
* [ ] Evaluation

## Academic Project

This project is being developed as a digital forensics research project investigating the forensic usefulness and limitations of residual edit-related artifacts within Microsoft Word DOCX files.
