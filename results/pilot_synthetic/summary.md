# Corpus evaluation summary

Generated 2026-09-29T08:09:54.242696+00:00 - 3 samples analysed, 3 with ground truth, 1 with a classification label.

Extraction correctness: 14/14 evaluated ground-truth checks matched (100%).

## Evidence per sample (RQ1)

| sample | referenced_rsids | settings_table_rsids | insertions | deletions | other_revision_markers | profile_revisions | profile_rsids | profile_metadata | category_document |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01_baseline.docx | 3 | 9 | 0 | 0 | 0 | 0 | 2 | 2 | multiple-RSID-pattern evidence |
| 02_edited.docx | 3 | 9 | 0 | 0 | 0 | 0 | 2 | 2 | multiple-RSID-pattern evidence |
| 03_tracked_changes.docx | 3 | 9 | 1 | 1 | 0 | 2 | 2 | 2 | retained tracked-revision evidence |

## Classification: RSID rules vs metadata-only baseline (RQ2)

| rule | accuracy | macro precision | macro recall | template FP |
| --- | --- | --- | --- | --- |
| document | 1.00 | 1.00 | 1.00 | 0/0 |
| content | 1.00 | 1.00 | 1.00 | 0/0 |
| all | 1.00 | 1.00 | 1.00 | 0/0 |
| metadata-only baseline | 0.00 | n/a | n/a | n/a |

## Revision artifact detection and survival

| artifact | samples | precision | recall | false_positive_rate | survival_rate |
| --- | --- | --- | --- | --- | --- |
| Retained insertions | 3 | 1.00 | 1.00 | 0.00 | 1.00 |
| Retained deletions | 3 | 1.00 | 1.00 | 0.00 | 1.00 |

## Artifact survival after transformations (RQ3)

| transformation | sample | artifact | parent_count | child_count | retained | introduced | survival_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 02_edited | 02_edited.docx | rsidRoot | 1 | 1 | 1 | 0 | 1.00 |
| 02_edited | 02_edited.docx | Settings RSID table | 9 | 9 | 9 | 0 | 1.00 |
| 02_edited | 02_edited.docx | Referenced RSIDs | 3 | 3 | 3 | 0 | 1.00 |
| 02_edited | 02_edited.docx | Content revisions | 0 | 0 | 0 | 0 | n/a |
| 02_edited | 02_edited.docx | Other revision markers | 0 | 0 | 0 | 0 | n/a |
| 02_edited | 02_edited.docx | Author metadata | 2 | 2 | 2 | 0 | 1.00 |
| 02_edited | 02_edited.docx | Timestamp metadata | 2 | 2 | 1 | 1 | 0.50 |
| 02_edited | 02_edited.docx | Application metadata | 2 | 2 | 2 | 0 | 1.00 |
