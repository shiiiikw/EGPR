# Baseline source audit

Primary sources were checked on 2026-10-17. No author implementation was copied.
The implemented controls must be described by their actual objectives and
interfaces, rather than presented as reproductions of a cited paper.

| Control | Current implementation | Attribution boundary |
|---|---|---|
| B1 | Enumerate the declared finite observation outcomes and evaluate guarded terminal utility | Generic one-step VOI instantiation; not REVOIR reproduction |
| B2 | B1 with valid dependency and full-request reuse | Strong ordinary caching control; not a new contribution |
| B3 | Highest-upper-bound expansion with strict interval dominance | Actual generic branch-and-bound implementation; identical to P here |
| B4 | Not implemented as a full comparator | A parameter-certainty proxy alone must not be labeled the complete SAGE agent |
| B0 | Not yet integrated | Must retain full-context adaptive roles, tools and recovery |

REVOIR updates beliefs over intent, estimates downstream task reward for asking
and acting, and permits information from later user corrections. Its practical
algorithm samples questions and outcomes. Our finite controller shares the
task-value principle but uses enumerated Boolean observations and evidence-bound
terminal outputs; it does not reproduce the paper's language-based belief or
post-action correction policy. “Full plan” and “incremental belief” cannot be
claimed as distinctions by themselves. See [REVOIR, Sections 3.1–3.3](https://arxiv.org/html/2609.37588v1).

SAGE scores questions by the expected increase in maximum tool-candidate
probability, penalizes repeated tool/parameter aspects, and uses a relative
stopping threshold. Section 7 reports lambda 0.5 and alpha 0.1. Its full loop also
generates candidates/questions, updates parameter domains and recovers from tool
errors. A faithful EGPR adaptation needs an explicit mapping from scoped fields
to tool candidates/aspects, the same permitted observations, and the common final
checker. Treating a whole Boolean world as a candidate would be a separate
parameter-completion diagnostic, not automatically that full adaptation.
See [SAGE, Sections 4–5, 7 and Algorithm 1](https://arxiv.org/html/2511.08798v2).

These mappings are our implementation audit. They do not assert that the two
papers make identical modeling assumptions. Additional model names or repeated
API samples do not remove the need for B2/B3 and the remaining substantive
comparators, nor establish a novelty advantage when P and B3 are equal.
