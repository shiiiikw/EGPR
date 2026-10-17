# Output-style diagnostic

This is a development adjustment to the API role interface, not a change to
EGPR's value objective or pruning rule. The original seven-model comparison
uses the original output style. Its results and failed responses remain fixed.

During the Qwen 1,536-token run, the first three states still had 11 response
errors among 39 B2 terminal evaluations. Inspection of truncated responses
showed repeated self-correction inside the visible `reason` string and, in one
case, a long space suffix. This motivates a concise-output diagnostic rather
than continuing to increase the output cap.

Before its execution, the diagnostic is fixed to the same four development
states, all B1/B2/B3/A1/P methods, Qwen3.5-9B with the original 768-token cap,
and the existing replicate identifier. Add a short common formatting instruction
to every role: at most 25 words for `reason`, at most three short `issues`, and
no step-by-step reasoning, self-revision or padding in these output fields.
This instruction is part of the full request hash. It is a prompt constraint,
not a new parser rule that rejects otherwise valid long answers.

Keep all public state, plan alternatives, evidence, role schemas, recovery,
observation probabilities and failure scoring identical. All arms within the
diagnostic use the same output style. Do not shorten a baseline's context or
relabel an old cached answer as a response to the new prompt.

Report all four states regardless of the first results. Compare truncations,
no-delivery, initial/final guard rejection, logical requests and logical cost
against both previous Qwen settings. One paired development response mapping
per setting cannot identify population effects or isolate output-cap causality
from provider generation variation. The style is not another foundation model.
Any adoption for a formal multi-model study must be frozen and applied equally
to every included model and policy; the original table will not be rewritten.

The already selected Luna/DeepSeek sequential integration retains the original
output style and can reuse its exact prior requests. This targeted diagnostic
does not change that selection or its declared states.
