# Harness2: default harness improvement workflow

[Google Research's Harness²](https://github.com/google-research/harness2) refines the system around a model: prompts, guardrails, memory, tool guidance, subagents, skills, scripts, and plugins. It proposes changes, probes them on the same task, composes a refinement from execution evidence, and retains evidence-supported lessons. Model weights remain fixed.

Use [prompt 15](../prompts/15-harness-improvement.md) as part of every new-project bootstrap and existing-project setup. Establish the native method adaptation, make its invocation reusable, and run relevant initial smoke cases from the [harness evaluation guide](../07-harness-evaluation.md). An observed failure justifies a bounded improvement comparison; a passing setup needs no invented change. This default workflow requires no new skill, MCP server, or application dependency. The official CLI lab remains optional.

## Choose the integration

| Mode | What runs | Requirements and limits |
|---|---|---|
| Native method adaptation | A bounded comparison performed by the current agent, using existing project checks and disposable cases | Preserves the authorized client, model, authentication, and permissions. Inspired by Harness2; does not execute its framework or reproduce its algorithm/results |
| Official CLI lab | The upstream deterministic demo, or separately authorized model-backed benchmarks | Dedicated checkout and virtual environment outside the application. Benchmark dependencies, authentication, costs, and execution permissions are separate decisions |

For ordinary project setup, use the native method adaptation without requiring a separate component selection. Keep its adaptation label: making this procedure the default does not install or execute the official framework. The current official CLI exposes JobBench, LAB, and WorkBuddy-Bench. It does not provide a generic command that installs an optimized harness into any repository. Connecting arbitrary project tasks to its engine would require an adapter and separately scoped implementation; do not invent a `--project` option or silently build an orchestrator.

## Official CLI: isolated local demo

Upstream recommends Linux and Python 3.12 for benchmark runs; its package supports Python 3.12–3.13. Reuse Git, `uv`, and a compatible Python. On other hosts, record the environment actually tested; a successful demo does not establish benchmark support. Do not install machine prerequisites implicitly during project bootstrap.

Choose a new dedicated directory outside both the toolkit and the target project. The commands below use the source revision reviewed for this guide. Inspect its installation metadata and demo before execution; when updating, review and record the new revision first.

```bash
git clone https://github.com/google-research/harness2.git harness2-lab
cd harness2-lab
git checkout --detach 1cfe254e8d25b15f37048c3730134686abe60335
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e '.[render]'
.venv/bin/harness2-demo --output runs/demo --k 2 --mode both
```

The demo uses deterministic editors and real local Python executions, without model credentials. It writes `runs/demo/demo.json`, task outputs, candidate harnesses, and a lesson library. Use a fresh output directory for a new comparison; record the command, exit status, `done`/`failed` counts, and inspect outputs and retained lessons. Do not interpret successful local arithmetic tasks as evidence that an application's agent improved.

Toolkit verification on 2026-10-18: the pinned demo passed on macOS arm64 with Python 3.12.15, both recursion modes, two tasks completed, and zero failures. It performed 28 local executions and 32 deterministic editor calls. Independent checks confirmed both adopted signed totals and persisted lessons in each mode. Linux benchmarks, model calls, and ChatGPT-login compatibility were not tested.

Keep the checkout, `.venv`, downloaded dependencies, `.env`, and raw `runs/` outside the application and public examples. Reuse an existing reviewed lab rather than cloning or reinstalling it on every setup. Delete only resources created for the evaluation, after recording the useful evidence.

## Model-backed benchmarks are a separate choice

Read the upstream [setup](https://github.com/google-research/harness2/blob/main/docs/SETUP.md), [benchmark](https://github.com/google-research/harness2/blob/main/docs/BENCHMARKS.md), and [experiment](https://github.com/google-research/harness2/blob/main/docs/EXPERIMENTS.md) guides for the selected revision before running them:

- Benchmark runs require additional dependencies, including Node.js 20+, Google Cloud CLI for the documented Vertex configuration, and benchmark-specific tools. LAB needs Pandoc/Poppler; WorkBuddy needs Docker. Review dataset and third-party licenses.
- The documented model-backed route incurs API costs. Its Codex executor connects to a Responses API endpoint; the optional Vertex bridge uses LiteLLM. This does not establish support for inheriting a ChatGPT subscription login or the current session. Do not add the bridge, credentials, provider changes, billing, or a different model without explicit authorization.
- Upstream runs Codex with its sandbox disabled and does not restrict executor network access. Use an explicitly authorized disposable isolated environment with appropriate filesystem/network controls. Protect private data and prevent access to benchmark answers/rubrics; selecting the CLI does not authorize weakening the project's permissions.
- Review setup with `harness2-setup <bench> --dry-run`; use `harness2 --dry-run` with the selected benchmark arguments to preview tasks. Setup preview, dependency checks, and model execution are different evidence. `harness2-check` does not prove model availability. Restrict both domains and tasks: `--max-tasks` caps tasks per domain, not the whole run. Set an explicit experiment budget before model calls.

When the authorized environment cannot meet these requirements, record the CLI as **blocked** or **not selected**, and continue independent project setup. The native method remains available; it must retain its adaptation label.

## Native method: one bounded improvement

1. Identify an observed setup/harness failure and define acceptance checks before editing. Reuse [prompt 14](../prompts/14-harness-evaluation.md) and existing project checks. Keep the evaluator and original inputs outside the trial agent's writable scope.
2. Capture the baseline in a disposable copy, with the actual client/model, permissions, commands, input revision, results, and observable actions. Do not copy credentials or private caches into trials. A missing observation remains **not run**.
3. Propose one small change to project-owned instructions, context routing, memory, or tool guidance. Test the candidate from the same initial task/input state under comparable conditions. Do not change the evaluator, acceptance criteria, or security/permission boundaries to obtain a pass.
4. Inspect the diff and independently rerun acceptance checks. Adopt only a supported improvement within the authorized setup scope; otherwise keep the baseline and record the failure. Preserve customizations and check reapplication for duplicate instructions/configuration.
5. Store a short lesson with its evidence, scope, verification date, and invalidation trigger in the existing canonical document. Update `docs/setup.md` and `docs/quality.md`, or their equivalents, with results and the invocation/source revision for prompt 15.

Default limit: one candidate comparison, then report. Further rounds require a specific unresolved failure and an agreed budget. One successful case is a smoke result, not a reliability rate or a reproduction of Google's benchmark gains. Withhold claims about generalization until separate tasks support them.

## Evidence and maintenance

Record the selected mode, toolkit/upstream revision, host/runtime, actual client/model/authentication mode without secrets, case/input identifiers, checks, observed results, adopted or rejected diff, elapsed time, and remaining limits. Report token/cost measurements only when exposed. Keep sensitive traces private; public setup documentation receives a sanitized summary.

Keep installation, successful demo, benchmark execution, and project behavior results separate. Reapplying setup must preserve the workflow, customizations, and existing lab. Reuse applicable evidence when inputs and settings remain unchanged; rerun relevant smoke cases after material changes to the client, model, instructions, or integration. Do not restart optimization or paid runs automatically. Recheck upstream requirements when updating the official lab.

Sources reviewed on 2026-10-18 at upstream revision `1cfe254e8d25b15f37048c3730134686abe60335`: [README](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/README.md), [setup](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/docs/SETUP.md), [package requirements](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/pyproject.toml), and [deterministic demo](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/demo.py). Harness2 is Apache-2.0 licensed and is not an officially supported Google product.
