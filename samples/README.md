# Controlled DOCX Corpus - Initial 3 Samples

This corpus supports early development and deterministic testing of the DOCX Edit-Trail Analyser.

## Samples

1. `01_baseline.docx` - baseline content, controlled metadata, no deliberate retained revisions.
2. `02_edited.docx` - derived from the baseline with known content changes and a later controlled modified timestamp.
3. `03_tracked_changes.docx` - deterministic OOXML fixture containing one retained deletion (`brown`) and one retained insertion (`red`).

Each DOCX has a matching JSON file in `ground_truth/`. The JSON is the authoritative record of what was deliberately done to that sample.

## Important research limitation

These initial files are programmatically generated. In particular, sample 03 contains synthetic tracked-change OOXML. They are suitable for deterministic extraction/correlation tests, but they must not be used to claim how Microsoft Word naturally generates RSIDs or all revision artifacts. For the formal evaluation, add at least one Word-native sample created by following a recorded manual protocol in Microsoft Word.

## Recommended project placement

Copy the three DOCX files into a subfolder such as `samples/controlled/` and the JSON records into `samples/ground_truth/`. Keep the JSON files unchanged so the experimental ground truth remains auditable.
