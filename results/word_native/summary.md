# Corpus evaluation summary

Generated 2026-09-28T20:09:25.281171+00:00 - 12 samples analysed, 12 with ground truth, 12 with a classification label.

Extraction correctness: 53/54 evaluated ground-truth checks matched (98%).

## Evidence per sample (RQ1)

| sample | referenced_rsids | settings_table_rsids | insertions | deletions | other_revision_markers | profile_revisions | profile_rsids | profile_metadata | category_document |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| W01_baseline.docx | 1 | 2 | 0 | 0 | 0 | 0 | 1 | 1 | metadata-only evidence |
| W02_save_as_no_edit.docx | 1 | 4 | 0 | 0 | 0 | 0 | 1 | 0 | metadata-only evidence |
| W03_direct_edit.docx | 2 | 4 | 0 | 0 | 0 | 0 | 2 | 1 | multiple-RSID-pattern evidence |
| W04_second_edit_session.docx | 3 | 6 | 0 | 0 | 0 | 0 | 2 | 1 | multiple-RSID-pattern evidence |
| W05_tracked_retained.docx | 2 | 4 | 2 | 1 | 0 | 2 | 2 | 1 | retained tracked-revision evidence |
| W06_tracked_accepted.docx | 2 | 6 | 0 | 0 | 0 | 0 | 2 | 1 | multiple-RSID-pattern evidence |
| W07_tracked_rejected.docx | 1 | 6 | 0 | 0 | 0 | 0 | 1 | 1 | metadata-only evidence |
| W08_template_control_A.docx | 1 | 2 | 0 | 0 | 0 | 0 | 1 | 1 | metadata-only evidence |
| W09_template_control_B.docx | 1 | 2 | 0 | 0 | 0 | 0 | 1 | 0 | metadata-only evidence |
| W10_inspected.docx | 2 | 6 | 0 | 0 | 0 | 0 | 2 | 0 | multiple-RSID-pattern evidence |
| W11_file_copy.docx | 2 | 4 | 0 | 0 | 0 | 0 | 2 | 1 | multiple-RSID-pattern evidence |
| W12_paste_into_new.docx | 1 | 2 | 0 | 0 | 0 | 0 | 1 | 1 | metadata-only evidence |

## Classification: RSID rules vs metadata-only baseline (RQ2)

| rule | accuracy | macro precision | macro recall | template FP |
| --- | --- | --- | --- | --- |
| document | 0.92 | 0.94 | 0.94 | 0/2 |
| content | 0.92 | 0.94 | 0.94 | 0/2 |
| all | 0.58 | 0.77 | 0.67 | 2/2 |
| metadata-only baseline | 0.42 | n/a | n/a | n/a |

## Revision artifact detection and survival

| artifact | samples | precision | recall | false_positive_rate | survival_rate |
| --- | --- | --- | --- | --- | --- |
| Retained insertions | 12 | 1.00 | 1.00 | 0.00 | 1.00 |
| Retained deletions | 12 | 1.00 | 1.00 | 0.00 | 1.00 |

## Artifact survival after transformations (RQ3)

| transformation | sample | artifact | parent_count | child_count | retained | introduced | survival_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| save as without editing | W02_save_as_no_edit.docx | rsidRoot | 1 | 1 | 1 | 0 | 1.00 |
| save as without editing | W02_save_as_no_edit.docx | Settings RSID table | 2 | 4 | 2 | 2 | 1.00 |
| save as without editing | W02_save_as_no_edit.docx | Referenced RSIDs | 1 | 1 | 1 | 0 | 1.00 |
| save as without editing | W02_save_as_no_edit.docx | Content revisions | 0 | 0 | 0 | 0 | n/a |
| save as without editing | W02_save_as_no_edit.docx | Other revision markers | 0 | 0 | 0 | 0 | n/a |
| save as without editing | W02_save_as_no_edit.docx | Author metadata | 2 | 2 | 2 | 0 | 1.00 |
| save as without editing | W02_save_as_no_edit.docx | Timestamp metadata | 2 | 2 | 0 | 2 | 0.00 |
| save as without editing | W02_save_as_no_edit.docx | Application metadata | 2 | 2 | 2 | 0 | 1.00 |
| direct edit (Track Changes off) | W03_direct_edit.docx | rsidRoot | 1 | 1 | 1 | 0 | 1.00 |
| direct edit (Track Changes off) | W03_direct_edit.docx | Settings RSID table | 2 | 4 | 2 | 2 | 1.00 |
| direct edit (Track Changes off) | W03_direct_edit.docx | Referenced RSIDs | 1 | 2 | 1 | 1 | 1.00 |
| direct edit (Track Changes off) | W03_direct_edit.docx | Content revisions | 0 | 0 | 0 | 0 | n/a |
| direct edit (Track Changes off) | W03_direct_edit.docx | Other revision markers | 0 | 0 | 0 | 0 | n/a |
| direct edit (Track Changes off) | W03_direct_edit.docx | Author metadata | 2 | 2 | 2 | 0 | 1.00 |
| direct edit (Track Changes off) | W03_direct_edit.docx | Timestamp metadata | 2 | 2 | 1 | 1 | 0.50 |
| direct edit (Track Changes off) | W03_direct_edit.docx | Application metadata | 2 | 2 | 2 | 0 | 1.00 |
| further direct edit in a third session | W04_second_edit_session.docx | rsidRoot | 1 | 1 | 1 | 0 | 1.00 |
| further direct edit in a third session | W04_second_edit_session.docx | Settings RSID table | 4 | 6 | 4 | 2 | 1.00 |
| further direct edit in a third session | W04_second_edit_session.docx | Referenced RSIDs | 2 | 3 | 2 | 1 | 1.00 |
| further direct edit in a third session | W04_second_edit_session.docx | Content revisions | 0 | 0 | 0 | 0 | n/a |
| further direct edit in a third session | W04_second_edit_session.docx | Other revision markers | 0 | 0 | 0 | 0 | n/a |
| further direct edit in a third session | W04_second_edit_session.docx | Author metadata | 2 | 2 | 2 | 0 | 1.00 |
| further direct edit in a third session | W04_second_edit_session.docx | Timestamp metadata | 2 | 2 | 1 | 1 | 0.50 |
| further direct edit in a third session | W04_second_edit_session.docx | Application metadata | 2 | 2 | 2 | 0 | 1.00 |
| tracked changes left pending | W05_tracked_retained.docx | rsidRoot | 1 | 1 | 1 | 0 | 1.00 |
| tracked changes left pending | W05_tracked_retained.docx | Settings RSID table | 2 | 4 | 2 | 2 | 1.00 |
| tracked changes left pending | W05_tracked_retained.docx | Referenced RSIDs | 1 | 2 | 1 | 1 | 1.00 |
| tracked changes left pending | W05_tracked_retained.docx | Content revisions | 0 | 3 | 0 | 3 | n/a |
| tracked changes left pending | W05_tracked_retained.docx | Other revision markers | 0 | 0 | 0 | 0 | n/a |
| tracked changes left pending | W05_tracked_retained.docx | Author metadata | 2 | 2 | 2 | 0 | 1.00 |
| tracked changes left pending | W05_tracked_retained.docx | Timestamp metadata | 2 | 2 | 1 | 1 | 0.50 |
| tracked changes left pending | W05_tracked_retained.docx | Application metadata | 2 | 2 | 2 | 0 | 1.00 |
| accept all tracked changes | W06_tracked_accepted.docx | rsidRoot | 1 | 1 | 1 | 0 | 1.00 |
| accept all tracked changes | W06_tracked_accepted.docx | Settings RSID table | 4 | 6 | 4 | 2 | 1.00 |
| accept all tracked changes | W06_tracked_accepted.docx | Referenced RSIDs | 2 | 2 | 2 | 0 | 1.00 |
| accept all tracked changes | W06_tracked_accepted.docx | Content revisions | 3 | 0 | 0 | 0 | 0.00 |
| accept all tracked changes | W06_tracked_accepted.docx | Other revision markers | 0 | 0 | 0 | 0 | n/a |
| accept all tracked changes | W06_tracked_accepted.docx | Author metadata | 2 | 2 | 2 | 0 | 1.00 |
| accept all tracked changes | W06_tracked_accepted.docx | Timestamp metadata | 2 | 2 | 1 | 1 | 0.50 |
| accept all tracked changes | W06_tracked_accepted.docx | Application metadata | 2 | 2 | 2 | 0 | 1.00 |
| reject all tracked changes | W07_tracked_rejected.docx | rsidRoot | 1 | 1 | 1 | 0 | 1.00 |
| reject all tracked changes | W07_tracked_rejected.docx | Settings RSID table | 4 | 6 | 4 | 2 | 1.00 |
| reject all tracked changes | W07_tracked_rejected.docx | Referenced RSIDs | 2 | 1 | 1 | 0 | 0.50 |
| reject all tracked changes | W07_tracked_rejected.docx | Content revisions | 3 | 0 | 0 | 0 | 0.00 |
| reject all tracked changes | W07_tracked_rejected.docx | Other revision markers | 0 | 0 | 0 | 0 | n/a |
| reject all tracked changes | W07_tracked_rejected.docx | Author metadata | 2 | 2 | 2 | 0 | 1.00 |
| reject all tracked changes | W07_tracked_rejected.docx | Timestamp metadata | 2 | 2 | 1 | 1 | 0.50 |
| reject all tracked changes | W07_tracked_rejected.docx | Application metadata | 2 | 2 | 2 | 0 | 1.00 |
| independent document (same Normal template) | W09_template_control_B.docx | rsidRoot | 1 | 1 | 0 | 1 | 0.00 |
| independent document (same Normal template) | W09_template_control_B.docx | Settings RSID table | 2 | 2 | 0 | 2 | 0.00 |
| independent document (same Normal template) | W09_template_control_B.docx | Referenced RSIDs | 1 | 1 | 0 | 1 | 0.00 |
| independent document (same Normal template) | W09_template_control_B.docx | Content revisions | 0 | 0 | 0 | 0 | n/a |
| independent document (same Normal template) | W09_template_control_B.docx | Other revision markers | 0 | 0 | 0 | 0 | n/a |
| independent document (same Normal template) | W09_template_control_B.docx | Author metadata | 2 | 2 | 2 | 0 | 1.00 |
| independent document (same Normal template) | W09_template_control_B.docx | Timestamp metadata | 2 | 2 | 0 | 2 | 0.00 |
| independent document (same Normal template) | W09_template_control_B.docx | Application metadata | 2 | 2 | 2 | 0 | 1.00 |
| Document Inspector: remove properties and personal information | W10_inspected.docx | rsidRoot | 1 | 1 | 1 | 0 | 1.00 |
| Document Inspector: remove properties and personal information | W10_inspected.docx | Settings RSID table | 4 | 6 | 4 | 2 | 1.00 |
| Document Inspector: remove properties and personal information | W10_inspected.docx | Referenced RSIDs | 2 | 2 | 2 | 0 | 1.00 |
| Document Inspector: remove properties and personal information | W10_inspected.docx | Content revisions | 0 | 0 | 0 | 0 | n/a |
| Document Inspector: remove properties and personal information | W10_inspected.docx | Other revision markers | 0 | 0 | 0 | 0 | n/a |
| Document Inspector: remove properties and personal information | W10_inspected.docx | Author metadata | 2 | 0 | 0 | 0 | 0.00 |
| Document Inspector: remove properties and personal information | W10_inspected.docx | Timestamp metadata | 2 | 2 | 0 | 2 | 0.00 |
| Document Inspector: remove properties and personal information | W10_inspected.docx | Application metadata | 2 | 2 | 2 | 0 | 1.00 |
| file-system copy (not opened in Word) | W11_file_copy.docx | rsidRoot | 1 | 1 | 1 | 0 | 1.00 |
| file-system copy (not opened in Word) | W11_file_copy.docx | Settings RSID table | 4 | 4 | 4 | 0 | 1.00 |
| file-system copy (not opened in Word) | W11_file_copy.docx | Referenced RSIDs | 2 | 2 | 2 | 0 | 1.00 |
| file-system copy (not opened in Word) | W11_file_copy.docx | Content revisions | 0 | 0 | 0 | 0 | n/a |
| file-system copy (not opened in Word) | W11_file_copy.docx | Other revision markers | 0 | 0 | 0 | 0 | n/a |
| file-system copy (not opened in Word) | W11_file_copy.docx | Author metadata | 2 | 2 | 2 | 0 | 1.00 |
| file-system copy (not opened in Word) | W11_file_copy.docx | Timestamp metadata | 2 | 2 | 2 | 0 | 1.00 |
| file-system copy (not opened in Word) | W11_file_copy.docx | Application metadata | 2 | 2 | 2 | 0 | 1.00 |
| copy text and paste into a new document | W12_paste_into_new.docx | rsidRoot | 1 | 1 | 0 | 1 | 0.00 |
| copy text and paste into a new document | W12_paste_into_new.docx | Settings RSID table | 4 | 2 | 0 | 2 | 0.00 |
| copy text and paste into a new document | W12_paste_into_new.docx | Referenced RSIDs | 2 | 1 | 0 | 1 | 0.00 |
| copy text and paste into a new document | W12_paste_into_new.docx | Content revisions | 0 | 0 | 0 | 0 | n/a |
| copy text and paste into a new document | W12_paste_into_new.docx | Other revision markers | 0 | 0 | 0 | 0 | n/a |
| copy text and paste into a new document | W12_paste_into_new.docx | Author metadata | 2 | 2 | 2 | 0 | 1.00 |
| copy text and paste into a new document | W12_paste_into_new.docx | Timestamp metadata | 2 | 2 | 0 | 2 | 0.00 |
| copy text and paste into a new document | W12_paste_into_new.docx | Application metadata | 2 | 2 | 2 | 0 | 1.00 |
