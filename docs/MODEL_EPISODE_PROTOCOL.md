# Sequential model development gate

The first model VOI pilot compares one-step choices at identical fixed states.
This gate injects the same guarded model evaluator into `run_episode`, including
its final recommendation. The controller must not silently substitute the exact
finite solver for a fallible model at termination. Finalization work is recorded
separately and also included in the evaluator's total work.

Search recovery also uses the model evaluator's actual proposal. A structural
solver's ability to find an admissible plan must not suppress search when the
model abstained. The recovery probe is included in the evaluator's work counts.
Tests reproduced this failure for all five methods before the first paid
sequential run; the shared implementation was then corrected. Empty string
plan identifiers enter the ordinary unknown-plan guard and bounded recovery,
rather than crashing before the final checker.

Before inspecting DeepSeek's model-VOI results, GPT-6 Luna and DeepSeek V4 Pro
0813 were selected as two accessible families for this integration stage. This
is a development choice, not a frozen paper model roster. The initial run uses
the existing two controlled instances with seeds 13 and 37, with all five
B1/B2/B3/A1/P methods. Further instances must be listed as a separate extension.

The fixed generator supplies eight candidate plans, four Boolean conditions,
correlated joint probabilities and truthful-or-unresolved queries. A separate
environment draws one world and one resolution indicator per query, using
`model-episode-v1:<instance seed>`. Every model and method receives the same
environment for an instance. The hidden world and resolution indicators are not
included in model messages. Each policy discloses its own selected observations.

The shared development budget is 16 decision steps, 8 information actions,
200 expanded counterfactual branches and 1 controlled search. Here information
actions include Ask and Verify together; the runner also reports them separately.
This is not the paper's eventual user-only information-item budget. Outputs keep
their configured token caps; no hard episode token-budget guarantee is claimed.
The campaign still enforces its US$10 development ceiling within US$200 total.

The request/replicate identity is shared with the same-state development pilot.
Exact matching prior responses can therefore be reused, including failed model
outputs. Report each policy's full unique request set, undiscounted logical token
cost, final reward, evidence support, user/source actions, expanded branches,
structural work, failures and observed action sequence. New network calls are a
separate campaign accounting metric. Shared provider cache and artificial request
pacing make replay latency unsuitable as an efficiency endpoint.

The generator includes an already supported low-reward fallback. Completion
alone is consequently a weak integration endpoint; reward and model failure
must accompany it. This is not native FoodPath, a user study, or a claim about
current service access. It tests sequential plumbing, common failure handling,
and recalculation after actual observations. Local exact choices do not imply
multi-step optimality. P remains identical to B3.

```sh
uv run python scripts/run_model_episodes.py --allow-paid --cases 2 \
  --output results/model-episodes-dev
# The same mapping can be replayed without new paid calls.
uv run python scripts/run_model_episodes.py --cases 2 \
  --output results/model-episodes-replay
```
