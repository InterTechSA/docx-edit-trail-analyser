"""
Batch corpus evaluation: analyse every DOCX in one or more
folders, compare with ground truth, and export the tables and
figures used in the research report.

Usage (from the project root):

    python src/batch_evaluate.py
    python src/batch_evaluate.py --samples samples/word_native
    python src/batch_evaluate.py --samples samples/controlled \
        samples/word_native --out results --rsid-scope document

Outputs (in --out, default "results/"):

    evidence_summary.csv        one row per sample: counts, profile
                                scores, category under every RSID scope
    artifact_presence.csv       RQ1 presence table
    ground_truth_results.csv    expected vs observed, per check
    survival.csv                RQ3 parent -> child survival rows
    metrics.json                every metric, ablation and confusion
    summary.md                  the key tables, ready to paste
    fig1_evidence_profile.png   evidence profile heatmap
    fig2_artifact_presence.png  RQ1 artifact presence heatmap
    fig3_survival.png           RQ3 survival heatmap
    fig4_confusion.png          RQ2 confusion matrices
    fig5_rsid_ablation.png      RQ2 accuracy by rule / baseline
    fig6_ground_truth.png       ground-truth agreement per sample
"""

import argparse
import csv
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent

sys.path.insert(0, str(SRC_DIR))

from correlation_engine import RSID_SCOPES  # noqa: E402
from corpus_evaluation import evaluate_corpus  # noqa: E402
from evidence_pipeline import analyse_docx, correlate  # noqa: E402


SHORT_CATEGORY = {
    "retained tracked-revision evidence": "Tracked revisions",
    "multiple-RSID-pattern evidence": "Multiple RSIDs",
    "metadata-only evidence": "Metadata only",
    "no selected edit artifact observed": "None observed",
}


# =========================================================
# Loading
# =========================================================

def load_corpus(sample_dirs, ground_truth_dir, rsid_scope):

    analysed = {}
    ground_truth = {}
    errors = {}

    for directory in sample_dirs:

        for path in sorted(Path(directory).glob("*.docx")):

            if path.name.startswith("~$"):
                continue  # Word lock files

            try:
                analysed[path.name] = analyse_docx(path, rsid_scope)
            except (FileNotFoundError, ValueError) as error:
                errors[path.name] = str(error)
                continue

            json_path = Path(ground_truth_dir) / f"{path.stem}.json"

            if json_path.exists():
                with open(json_path, encoding="utf-8") as handle:
                    ground_truth[path.name] = json.load(handle)

    return analysed, ground_truth, errors


# =========================================================
# Tables
# =========================================================

def evidence_summary_rows(analysed):

    rows = []

    for name, evidence in analysed.items():

        profile = evidence["evidence_profile"]
        revisions = evidence["revisions"]

        row = {
            "sample": name,
            "rsid_root": evidence["rsid_root"] or "",
            "settings_table_rsids": len(evidence["rsid_table"]),
            "referenced_rsids": len(evidence["referenced_rsids"]),
            "rsid_attributes": len(evidence["document_rsids"]),
            "insertions": sum(
                1 for r in revisions if r["type"] == "insertion"
            ),
            "deletions": sum(
                1 for r in revisions if r["type"] == "deletion"
            ),
            "other_revision_markers": sum(
                1 for r in revisions
                if r["type"] not in ("insertion", "deletion")
            ),
            "creator": evidence["core_properties"].get("creator"),
            "last_modified_by": evidence["core_properties"].get(
                "last_modified_by"
            ),
            "created": evidence["core_properties"].get("created"),
            "modified": evidence["core_properties"].get("modified"),
            "application": evidence["app_properties"].get(
                "application"
            ),
            "app_version": evidence["app_properties"].get(
                "app_version"
            ),
            "profile_revisions": profile["revision_evidence"]["score"],
            "profile_rsids": profile["rsid_evidence"]["score"],
            "profile_metadata": profile["metadata_evidence"]["score"],
        }

        for scope in RSID_SCOPES:
            row[f"category_{scope}"] = correlate(
                evidence, scope
            )["classification"]["category"]

        rows.append(row)

    return rows


def ground_truth_rows(evaluations):

    rows = []

    for name, evaluation in evaluations.items():

        for result in evaluation["results"]:

            rows.append({
                "sample": name,
                "check": result.get("artifact"),
                "expected": result.get("expected"),
                "observed": result.get("observed"),
                "status": result.get("status"),
                "note": result.get("note") or "",
            })

    return rows


def write_csv(path, rows):

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def fmt(value):

    if value is None:
        return "n/a"

    if isinstance(value, float):
        return f"{value:.2f}"

    return str(value)


def markdown_table(rows, columns):

    if not rows:
        return "_No rows._\n"

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]

    for row in rows:
        lines.append(
            "| " + " | ".join(fmt(row.get(c)) for c in columns) + " |"
        )

    return "\n".join(lines) + "\n"


# =========================================================
# Figures
# =========================================================

def short_label(row):
    """Compact row label for the survival heatmap: 'W06  accept all ...'."""

    sample = Path(row["sample"]).stem.split("_")[0]
    transformation = row["transformation"]

    if len(transformation) > 38:
        transformation = transformation[:36].rstrip() + "..."

    return f"{sample}  {transformation}"


def make_figures(out_dir, analysed, results, summary_rows):

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[WARN] matplotlib not installed; figures skipped.")
        return []

    written = []

    def heatmap(ax, data, row_labels, col_labels, vmax, fmt_cell,
                cmap="Blues"):

        image = ax.imshow(
            [[(v if v is not None else float("nan")) for v in row]
             for row in data],
            cmap=cmap, vmin=0, vmax=vmax, aspect="auto",
        )

        ax.set_xticks(range(len(col_labels)))
        ax.set_xticklabels(col_labels, rotation=35, ha="right")
        ax.set_yticks(range(len(row_labels)))
        ax.set_yticklabels(row_labels)

        for i, row in enumerate(data):
            for j, value in enumerate(row):
                text = fmt_cell(value)
                shade = (
                    value is not None and vmax and value > vmax * 0.6
                )
                ax.text(
                    j, i, text, ha="center", va="center",
                    color="white" if shade else "black", fontsize=8,
                )

        return image

    def save(fig, name):
        path = out_dir / name
        fig.tight_layout()
        fig.savefig(path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        written.append(path)

    samples = [row["sample"] for row in summary_rows]

    # Fig 1: evidence profile heatmap -----------------------------
    data = [
        [row["profile_revisions"], row["profile_rsids"],
         row["profile_metadata"]]
        for row in summary_rows
    ]
    fig, ax = plt.subplots(figsize=(6.5, 0.45 * len(samples) + 1.8))
    image = heatmap(
        ax, data, samples,
        ["Retained revisions", "RSID pattern", "Context metadata"],
        3, lambda v: "" if v is None else str(v),
    )
    fig.colorbar(image, ax=ax, ticks=[0, 1, 2, 3],
                 label="0 none - 3 extensive")
    ax.set_title("Evidence profile per sample (0-3)")
    save(fig, "fig1_evidence_profile.png")

    # Fig 2: artifact presence heatmap (RQ1) ---------------------
    presence = results["presence"]
    if presence:
        groups = [k for k in presence[0] if k != "sample"]
        data = [[row[g] for g in groups] for row in presence]
        vmax = max(max(r) for r in data) or 1
        fig, ax = plt.subplots(
            figsize=(9, 0.45 * len(presence) + 2.2)
        )
        heatmap(ax, data, [r["sample"] for r in presence], groups,
                vmax, lambda v: str(v), cmap="Greens")
        ax.set_title("Selected artifacts present in each final DOCX "
                     "(counts)")
        save(fig, "fig2_artifact_presence.png")

    # Fig 3: survival heatmap (RQ3) ------------------------------
    survival = results["survival"]
    if survival:
        pairs = []
        for row in survival:
            label = short_label(row)
            if label not in pairs:
                pairs.append(label)
        groups = []
        for row in survival:
            if row["artifact"] not in groups:
                groups.append(row["artifact"])
        lookup = {
            (short_label(r), r["artifact"]):
                r["survival_rate"]
            for r in survival
        }
        data = [[lookup.get((p, g)) for g in groups] for p in pairs]
        fig, ax = plt.subplots(figsize=(12, 0.55 * len(pairs) + 2.6))
        image = heatmap(
            ax, data, pairs, groups, 1,
            lambda v: "-" if v is None else f"{v:.0%}",
            cmap="RdYlGn",
        )
        fig.colorbar(image, ax=ax, label="survival rate")
        ax.set_title("Artifact survival after each transformation "
                     "(parent -> child)")
        save(fig, "fig3_survival.png")

    # Fig 4: confusion matrices (RQ2) ----------------------------
    confusion = results["confusion"]
    labelled = results["labelled_samples"]
    if labelled:
        keys = list(confusion.keys())
        fig, axes = plt.subplots(
            1, len(keys), figsize=(4.2 * len(keys), 4.4)
        )
        if len(keys) == 1:
            axes = [axes]
        short = [SHORT_CATEGORY[c] for c in results["categories"]]
        for ax, key in zip(axes, keys):
            matrix = confusion[key]["matrix"]
            vmax = max(max(r) for r in matrix) or 1
            heatmap(ax, matrix, short, short, vmax, lambda v: str(v),
                    cmap="Purples")
            ax.set_title(key, fontsize=10)
            ax.set_xlabel("predicted")
            ax.set_ylabel("ground truth")
        save(fig, "fig4_confusion.png")

        # Fig 5: ablation accuracy ------------------------------
        ablation = results["ablation"]
        names = list(ablation.keys())
        values = [ablation[n]["accuracy"] or 0 for n in names]
        fig, ax = plt.subplots(figsize=(7, 3.6))
        bars = ax.bar(
            [n.replace("metadata-only baseline", "baseline")
             for n in names],
            values,
            color=["#4C72B0"] * len(RSID_SCOPES) + ["#BBBBBB"],
        )
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, value + 0.02,
                    f"{value:.2f}", ha="center")
        ax.set_ylim(0, 1.1)
        ax.set_ylabel("accuracy")
        ax.set_title(
            f"Category accuracy by RSID rule vs metadata-only "
            f"baseline (n={labelled})"
        )
        save(fig, "fig5_rsid_ablation.png")

    # Fig 6: ground-truth agreement ------------------------------
    evaluations = results["evaluations"]
    if evaluations:
        names = list(evaluations.keys())
        matched = [evaluations[n]["matched_count"] for n in names]
        mismatched = [evaluations[n]["mismatched_count"] for n in names]
        skipped = [evaluations[n]["not_evaluated_count"] for n in names]
        fig, ax = plt.subplots(figsize=(8, 0.45 * len(names) + 1.8))
        ax.barh(names, matched, color="#55A868", label="match")
        ax.barh(names, mismatched, left=matched, color="#C44E52",
                label="mismatch")
        ax.barh(names, skipped,
                left=[a + b for a, b in zip(matched, mismatched)],
                color="#CCCCCC", label="not evaluated")
        ax.invert_yaxis()
        ax.set_xlabel("ground-truth checks")
        ax.legend(loc="lower right")
        ax.set_title("Extraction correctness against ground truth")
        save(fig, "fig6_ground_truth.png")

    return written


# =========================================================
# Main
# =========================================================

def main(argv=None):

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument(
        "--samples", nargs="+",
        default=[str(PROJECT_ROOT / "samples" / "controlled")],
        help="folders containing DOCX samples",
    )
    parser.add_argument(
        "--ground-truth",
        default=str(PROJECT_ROOT / "samples" / "ground_truth"),
    )
    parser.add_argument("--out", default=str(PROJECT_ROOT / "results"))
    parser.add_argument(
        "--rsid-scope", default="document", choices=RSID_SCOPES,
        help="primary RSID rule (all rules are reported in the "
             "ablation regardless)",
    )
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    analysed, ground_truth, errors = load_corpus(
        args.samples, args.ground_truth, args.rsid_scope
    )

    if not analysed:
        print("[ERROR] No DOCX samples could be analysed.")
        return 1

    results = evaluate_corpus(analysed, ground_truth)

    summary_rows = evidence_summary_rows(analysed)
    gt_rows = ground_truth_rows(results["evaluations"])

    write_csv(out_dir / "evidence_summary.csv", summary_rows)
    write_csv(out_dir / "artifact_presence.csv", results["presence"])
    write_csv(out_dir / "ground_truth_results.csv", gt_rows)
    write_csv(out_dir / "survival.csv", results["survival"])

    metadata = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "primary_rsid_scope": args.rsid_scope,
        "sample_folders": args.samples,
        "samples_analysed": len(analysed),
        "samples_with_ground_truth": len(ground_truth),
        "errors": errors,
    }

    serialisable = {
        key: value for key, value in results.items()
        if key != "evaluations"
    }
    serialisable["evaluations"] = {
        name: {k: v for k, v in evaluation.items()}
        for name, evaluation in results["evaluations"].items()
    }

    with open(out_dir / "metrics.json", "w", encoding="utf-8") as handle:
        json.dump(
            {"run": metadata, **serialisable},
            handle, indent=2, default=str,
        )

    # summary.md ----------------------------------------------------
    ablation_rows = [
        {
            "rule": name,
            "accuracy": values.get("accuracy"),
            "macro precision": values.get("macro_precision"),
            "macro recall": values.get("macro_recall"),
            "template FP": (
                f"{values['negative_control_rsid_false_positives']}"
                f"/{values['negative_controls']}"
                if "negative_controls" in values else "n/a"
            ),
        }
        for name, values in results["ablation"].items()
    ]

    artifact_rows = [
        {"artifact": name, **values}
        for name, values in results["metrics"]["artifacts"].items()
    ]

    total_checks = sum(
        e["evaluated_count"] for e in results["evaluations"].values()
    )
    total_matched = sum(
        e["matched_count"] for e in results["evaluations"].values()
    )

    lines = [
        "# Corpus evaluation summary\n",
        f"Generated {metadata['generated_utc']} - "
        f"{len(analysed)} samples analysed, {len(ground_truth)} with "
        f"ground truth, {results['labelled_samples']} with a "
        f"classification label.\n",
        f"Extraction correctness: {total_matched}/{total_checks} "
        f"evaluated ground-truth checks matched"
        + (
            f" ({total_matched / total_checks:.0%})."
            if total_checks else "."
        ) + "\n",
        "## Evidence per sample (RQ1)\n",
        markdown_table(summary_rows, [
            "sample", "referenced_rsids", "settings_table_rsids",
            "insertions", "deletions", "other_revision_markers",
            "profile_revisions", "profile_rsids", "profile_metadata",
            "category_document",
        ]),
        "## Classification: RSID rules vs metadata-only baseline (RQ2)\n",
        markdown_table(ablation_rows, [
            "rule", "accuracy", "macro precision", "macro recall",
            "template FP",
        ]),
        "## Revision artifact detection and survival\n",
        markdown_table(artifact_rows, [
            "artifact", "samples", "precision", "recall",
            "false_positive_rate", "survival_rate",
        ]),
        "## Artifact survival after transformations (RQ3)\n",
        markdown_table(results["survival"], [
            "transformation", "sample", "artifact", "parent_count",
            "child_count", "retained", "introduced", "survival_rate",
        ]),
    ]

    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    figures = make_figures(out_dir, analysed, results, summary_rows)

    print(f"Analysed {len(analysed)} sample(s); "
          f"{len(ground_truth)} with ground truth.")
    for name, error in errors.items():
        print(f"[SKIPPED] {name}: {error}")
    print(f"Results written to {out_dir}")
    for figure in figures:
        print(f"  {figure.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
