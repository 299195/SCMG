# Usage

## Bridge protocol

Install the package with `python -m pip install -e .`. The bridge reads one JSON
object from standard input and writes one JSON object to standard output.

Every action requires:

```json
{
  "workspace": "absolute path to the agent workspace",
  "state_dir": "absolute path for SCMG audit state",
  "record_file": "absolute path to a JSON record"
}
```

The record contains `user_query`, `context`, and `retrieval_query`. Applications
may instead pass the same object in the `record` field. Evaluation labels and
expected outputs are not policy inputs.

Supported actions are `bind_origin`, `preflight`, `admit`,
`prepare_retrieval`, `tool_gate`, `final_audit`, and `verify`. Action-specific
fields are documented by the corresponding branch in `src/scmg/bridge.py`.

## OpenClaw plugin

Copy or link `plugins/openclaw` into the OpenClaw extension directory, then set:

```text
SCMG_WORKSPACE   absolute agent workspace path
SCMG_RECORD      JSON record used for the guarded run
SCMG_STATE       directory for origin and audit records
SCMG_EVENTS      optional plugin event JSONL
SCMG_PYTHON      Python executable with the scmg package installed
SCMG_BRIDGE      optional direct path to bridge.py
```

Session keys containing `-write` and `-retrieval` select the two lifecycle
phases. Integrations using another naming scheme should adapt the `phase`
function in the plugin.

Managed persistent files are `MEMORY.md` and Markdown files directly under
`memory/`. Extend `memoryFiles` and `memory_files` together if an agent uses a
different store.

## Evaluation helper

`scmg.evaluation.summarize` accepts rows with `category`, `write_positive`,
`reuse_positive`, and optional `error`. It reports attempted, valid, and error
counts explicitly. Conditional reuse uses write-positive rows as its
denominator.
