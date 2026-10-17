# Cross-domain qualification: Ask-before-Plan

The original EGPR plan names Ask-before-Plan as a possible secondary domain.
This bounded inspection checks its available inputs before committing API budget.
It is not a completed cross-domain experiment. FoodPath remains the main task.

The [paper](https://aclanthology.org/2024.findings-emnlp.636/) studies clarification
and travel planning. The [dataset card](https://huggingface.co/datasets/magicgh/Ask-before-Plan/blob/4ff2b9fa7c2e4f924b0536170a33e8261090b950/README.md)
identifies TravelPlanner as its basis and declares CC BY 4.0. The
[author repository](https://github.com/magicgh/Ask-before-Plan/tree/37576b24a2aeb82753e7b4cdfce7fbb36583b1f4)
declares MIT for its code. These declarations do not establish the provenance
and licensing of the separately hosted travel database.

Only the pinned training CSV and its card were downloaded for schema inspection.
No held-out test rows were loaded, no author agent was run, and no model API was
called. The 1,000 training rows have 1,800 stored disclosures: 1,204 ADD and 596
REPLACE operations over nine attributes. There are 999 distinct initial query
strings. Neither count is a count of independent source groups.
The [aggregate qualification report](../reports/ask_before_plan_qualification_v0_9/qualification.json)
also records 111 null stored values and 59 rows with repeated disclosure
attributes; a later adapter must respect ordering and unresolved values.

Each disclosure records an attribute, value, question, answer, operation and
priority. This supports a possible field-limited clarification adapter. The
author loader applies stored values to successive task states. Its declared
schema contains `task_id`, but the pinned CSV does not; compatibility must be
resolved explicitly rather than inventing a source identity from the row index.

Full planning also needs the author's separate flights, accommodations,
restaurants, attractions and distance data. That environment has not been
downloaded or qualified. Missing preference fields have benchmark-specific
semantics in the author prompts; they must not change FoodPath's treatment of
unknown eligibility or service capabilities.

Before an efficacy run, qualify the separate environment and task provenance,
implement scoped disclosure with immutable source references, validate the full
plan checker, and freeze a paired subset and common observation assumptions.
Travel rows must not be added to the FoodPath denominator. Reconstructing full
plans and valid utility bounds remains work, not a property proven by the CSV.

Reproduce this zero-API inspection with `scripts/qualify_ask_before_plan.py`,
passing the pinned local dataset directory and a new output directory. The
published report contains hashes and aggregates; raw rows remain ignored.
