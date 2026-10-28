# SCMG

English | [中文](README_ZH.md)

SCMG (Source-Constrained Memory Guard) is a research prototype for protecting
persistent memory in LLM agents. It keeps the origin of external material
attached to memory claims, filters unsafe standing rules before they are
persisted, rechecks stored content before reuse, and gates sensitive tool calls
against the current authenticated user request.

The repository contains a standard-library Python policy package, a synchronous
bridge, an OpenClaw plugin, deterministic tests, and synthetic examples. It does
not contain model credentials, local agent state, research logs, private prompts,
or experimental result archives.

## Protection flow

```text
authenticated request + external material
                  |
                  v
        bind source and content hashes
                  |
                  v
        split candidate memory claims
                  |
                  v
   keep facts / quarantine authority claims
                  |
                  v
     verify the persisted memory files
                  |
                  v
     rescan and project memory on reuse
                  |
                  v
 gate sensitive tools using the current request
```

## Quick start

SCMG requires Python 3.10 or later and has no runtime dependencies.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m unittest discover -s tests -v
```

Try the policy with the included synthetic record:

```powershell
$payload = @{
  workspace = (Resolve-Path examples\workspace).Path
  state_dir = (Join-Path (Resolve-Path examples).Path "state")
  record_file = (Resolve-Path examples\record.json).Path
} | ConvertTo-Json
$payload | scmg-bridge bind_origin
```

The bridge normally receives a JSON object on standard input. See
[`docs/usage.md`](docs/usage.md) for the full payload and OpenClaw setup.

## Repository layout

```text
src/scmg/                 Core policy, bridge, and evaluation helpers
plugins/openclaw/         OpenClaw lifecycle hook integration
examples/                 Synthetic, non-experimental inputs
tests/                    Deterministic unit and bridge tests
docs/                     Architecture and deployment notes
```

A detailed Chinese inventory of every uploaded component is available in
[`docs/REPOSITORY_CONTENTS_ZH.md`](docs/REPOSITORY_CONTENTS_ZH.md).

## Security properties

- Runtime policy decisions use the current request and external material, not
  benchmark labels or expected outputs.
- Memory claims from external material cannot become standing authority merely
  because an agent persisted them.
- File projections and policy events are recorded in a hash-chained audit log.
- Network destinations and scheduled actions require a matching request from the
  authenticated user.
- Guard failures block the affected operation instead of silently bypassing the
  policy.

SCMG is a research prototype. Its guarantees cover the hooks and tools that are
actually connected to the guard. Deployments should map every persistent-memory
write path and every sensitive action to an enforcement point.

## License

No open-source license is granted at this time. Copyright is retained by the
repository owner.
