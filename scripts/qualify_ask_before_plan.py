"""Read-only training-data qualification; never loads test rows or runs agents."""
import argparse
import ast
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path


REVISION = "4ff2b9fa7c2e4f924b0536170a33e8261090b950"
AUTHOR_COMMIT = "37576b24a2aeb82753e7b4cdfce7fbb36583b1f4"
FIELDS = {"org", "dest", "days", "departure_date", "people_number", "housing",
          "cuisine", "transportation", "budget"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    files = {name: args.dataset / name for name in ("README.md", "train.csv")}
    # This is a pinned qualification report, not a parser for arbitrary revisions.
    expected = {"README.md": "fff2fd78a72634685986821e3886691d4497a107831c94b58f062fb676fce515",
                "train.csv": "9ab146755031ea5d32b73d66305c8a5db578abf4212bb161723946a43d411462"}
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()}
    if hashes != expected:
        raise ValueError("Unexpected dataset bytes; qualify a new revision explicitly")
    with files["train.csv"].open(newline="") as stream:
        reader = csv.DictReader(stream)
        rows, columns = list(reader), reader.fieldnames
    if not FIELDS.union({"query", "level", "details"}).issubset(columns):
        raise ValueError("Missing required columns")
    operations, attributes, priorities, detail_counts = Counter(), Counter(), Counter(), Counter()
    missing_answer, null_value, repeated_attribute_rows = 0, 0, 0
    for row in rows:
        details = ast.literal_eval(row["details"])
        if not isinstance(details, list):
            raise ValueError("Details must be a list")
        detail_counts[len(details)] += 1
        per_row = Counter()
        for detail in details:
            required = {"answer", "attribute", "operation", "priority", "question", "value"}
            if not isinstance(detail, dict) or set(detail) != required:
                raise ValueError("Unexpected disclosure schema")
            if detail["attribute"] not in FIELDS or detail["operation"] not in {"ADD", "REPLACE"}:
                raise ValueError("Unsupported disclosure operation")
            operations[detail["operation"]] += 1
            attributes[detail["attribute"]] += 1
            priorities[str(detail["priority"])] += 1
            per_row[detail["attribute"]] += 1
            missing_answer += not isinstance(detail["answer"], str) or not detail["answer"].strip()
            null_value += detail["value"] is None
        repeated_attribute_rows += any(n > 1 for n in per_row.values())
    report = {
        "scope": "Training split schema qualification only; no model evaluation or held-out access",
        "dataset": "magicgh/Ask-before-Plan", "revision": REVISION,
        "dataset_license_as_declared": "cc-by-4.0", "author_code_commit": AUTHOR_COMMIT,
        "author_code_license_as_declared": "MIT", "input_sha256": hashes,
        "rows": len(rows), "columns": columns, "task_id_column_present": "task_id" in columns,
        "distinct_initial_query_strings": len({r["query"] for r in rows}),
        "levels": dict(Counter(r["level"] for r in rows)),
        "details_per_row": dict(sorted(detail_counts.items())),
        "disclosures": sum(operations.values()), "operations": dict(operations),
        "attributes": dict(attributes), "priorities": dict(priorities),
        "missing_or_empty_stored_answers": missing_answer, "null_stored_values": null_value,
        "rows_repeating_a_disclosure_attribute": repeated_attribute_rows,
        "independent_source_groups": None, "heldout_rows_loaded": 0, "api_calls": 0,
        "environment_database_downloaded": False,
        "qualification": "Stored clarification fields available; full travel tools, evaluation and provenance grouping not yet qualified",
        "limits": [
            "Distinct strings or row indices are not independent source-group identifiers.",
            "The upstream loader declares task_id but this pinned CSV does not contain it; direct loader compatibility is not established.",
            "The separate travel database and its provenance/license remain to be checked before a full planning evaluation.",
            "Benchmark-specific empty preference semantics cannot be imported into FoodPath evidence checks.",
            "No cross-domain effectiveness, operational travel success or valid EGPR bounds are inferred from schema availability.",
        ],
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("rows", "disclosures", "operations", "missing_or_empty_stored_answers",
                                           "null_stored_values", "rows_repeating_a_disclosure_attribute", "heldout_rows_loaded", "api_calls")}))


if __name__ == "__main__":
    main()
