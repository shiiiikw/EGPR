"""Aggregate exact B2 request failures without publishing raw API responses."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from egpr.api import ModelResponseError, parse_completion


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", type=Path, nargs="+", required=True)
    ap.add_argument("--ledger", type=Path, default=ROOT / "results/api_campaign/calls.jsonl")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    keys, configurations, terminal_counts = defaultdict(set), {}, defaultdict(Counter)
    seen = set()
    inputs = []
    for folder in args.inputs:
        if json.loads((folder / "summary.json").read_text())["status"] != "complete":
            raise ValueError("Audit completed model queues only")
        manifest = json.loads((folder / "manifest.json").read_text())
        configurations.update(manifest["models"])
        path = folder / "traces.jsonl"
        inputs.append({"run": folder.name, "trace_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row["policy"] != "B2":
                continue
            identity = (row["model"], tuple(row["setting"]), manifest["replicate_id"])
            if identity in seen:
                raise ValueError("Replay duplicates are not independent model/state pairs")
            seen.add(identity)
            for terminal in row["terminal_traces"]:
                trace = terminal["trace"]
                keys[row["model"]].update(trace["request_hashes"])
                terminal_counts[row["model"]]["terminal_evaluations"] += 1
                terminal_counts[row["model"]]["model_response_errors"] += bool(trace.get("error_type"))
                terminal_counts[row["model"]]["no_delivery"] += trace["delivered_plan_id"] is None
    wanted = set().union(*keys.values())
    receipts = {}
    for line in args.ledger.read_text().splitlines():
        row = json.loads(line)
        if row["status"] == "received" and row["request_hash"] in wanted and not row.get("access_blocked"):
            receipts[row["request_hash"]] = row
    result = {"scope": "unique requests used by complete B2 development evaluations; not online task success rates",
              "source_runs": inputs, "ledger_sha256": hashlib.sha256(args.ledger.read_bytes()).hexdigest(),
              "models": {}, "raw_responses_published": False,
              "parser_note": "A parsed object is not necessarily a valid role output or supported plan; terminal errors and no-delivery are separate."}
    for model, request_keys in sorted(keys.items()):
        finish, outcomes, tokens = Counter(), Counter(), Counter()
        max_output = 0
        for key in request_keys:
            if key not in receipts:
                outcomes["missing_receipt"] += 1
                continue
            envelope = receipts[key]["response"]
            try:
                body = json.loads(envelope["raw_body"])
                choice = body["choices"][0]
                finish[str(choice.get("finish_reason"))] += 1
                if choice.get("message", {}).get("refusal"):
                    outcomes["refusal"] += 1
            except (ValueError, KeyError, TypeError, IndexError):
                outcomes["malformed_envelope"] += 1
            try:
                parse_completion(envelope)
                outcomes["parsed_object"] += 1
            except ModelResponseError:
                outcomes["completion_parse_error"] += 1
            usage = receipts[key].get("usage") or {}
            for field in ("prompt_tokens", "completion_tokens"):
                value = usage.get(field)
                if type(value) is int:
                    tokens[field] += value
                    tokens[field + "_receipts"] += 1
                    if field == "completion_tokens":
                        max_output = max(max_output, value)
            details = usage.get("completion_tokens_details") or {}
            reasoning = details.get("reasoning_tokens") if isinstance(details, dict) else None
            if reasoning is None:
                reasoning = usage.get("reasoning_tokens")
            if type(reasoning) is int:
                tokens["reasoning_tokens_reported"] += reasoning
                tokens["reasoning_token_receipts"] += 1
        generation = configurations[model]["generation"]
        result["models"][model] = {"unique_B2_requests": len(request_keys),
            "configured_output_cap": generation.get("max_completion_tokens", generation.get("max_tokens")),
            "finish_reasons": dict(finish), "completion_parse_outcomes": dict(outcomes),
            "reported_tokens": dict(tokens), "maximum_reported_completion_tokens": max_output,
            "terminal_counts": dict(terminal_counts[model])}
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "output_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({model: {"requests": row["unique_B2_requests"], "finish_reasons": row["finish_reasons"],
                            "terminal_counts": row["terminal_counts"]} for model, row in result["models"].items()}, indent=2))


if __name__ == "__main__":
    main()
