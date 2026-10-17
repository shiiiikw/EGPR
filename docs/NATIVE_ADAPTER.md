# Native user disclosure contract

`native_user.NativeUser` is a deterministic adapter over locally stored native
task fields. It is a step toward the FoodPath environment, not a completed
end-to-end policy or a human-validated simulator. The existing task source stays
outside the public repository.

The initial public context contains service categories and opaque within-task
need scopes (`need:0`, etc.). It contains no target resource, source-derived task
ID, answer values, or future alternatives. This declared initial context is an
adapter assumption; free-text opening-message extraction is not implemented.

Each `ask(scope, fields)` discloses only the requested fields under that scope.
Nonempty values must pass the native projection contract. Missing fields, empty
lists/dictionaries, placeholder tags and unsupported shapes remain unknown with
an explicit unresolved reason. They are never inferred to mean false, no
documents, or unrestricted preferences. Source records bind a snapshot hash,
field pointer and value. The audit passes an absolute JSON pointer into the
native source array, so a retained local source can locate every observation.

The user budget counts each requested field as one information item and each
accepted call as one round. Repetition returns the same answer and still consumes
an item and round. Distinct items are counted separately by scope and field.
Multi-field requests are atomic: an over-budget request discloses nothing.
Returned objects are copied so callers cannot mutate undisclosed answers.

When a native task includes a `preferred` profile, that is the initial profile.
Later alternative values are discarded from the adapter's retained answer map.
An empty or malformed preferred profile does not silently expose the alternative.
Accepting an alternative requires a later explicit transition grounded in the
benchmark's user semantics; that transition is not yet implemented. The adapter
does not invent user consent or treat an unsuccessful search as consent.

The development audit exhaustively asks every stored field and repeats one per
need. Its larger inspection budget is declared in the runner and must not be
confused with the eight-item/eight-round policy default. It evaluates only the
qualification split's development groups, preserves unresolved answers and
publishes aggregate counts. Full disclosures remain ignored local artifacts.

```sh
uv run python scripts/audit_native_user.py \
  --foodpath /path/to/local-foodpath \
  --qualification results/foodpath_qualification_v0 \
  --output results/native-user-audit
```

Query valuation for categorical fields, source text extraction, current service
availability, consent to alternatives and cross-service constraints remain to be
integrated. Stored-field coverage is not evidence-supported complete-plan success.
