"""Synchronous JSON bridge used by the OpenClaw plugin."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .policy import (
    append_audit,
    assess_unit,
    check_tool,
    digest,
    project_memory,
    rank_candidates,
    record_origin,
    render_context,
    verify_audit,
)


def contained(path: Path, root: Path) -> Path:
    value = path.resolve()
    if not value.is_relative_to(root.resolve()):
        raise ValueError("memory path escapes the configured workspace")
    return value


def memory_files(workspace: Path) -> list[Path]:
    memory_dir = workspace / "memory"
    paths = [workspace / "MEMORY.md"]
    if memory_dir.is_dir():
        paths.extend(sorted(memory_dir.glob("*.md")))
    return [contained(path, workspace) for path in paths if path.is_file()]


def _load_record(payload: dict[str, Any]) -> dict[str, str]:
    source: dict[str, Any]
    if isinstance(payload.get("record"), dict):
        source = payload["record"]
    else:
        record_path = Path(str(payload.get("record_file", ""))).resolve()
        if not record_path.is_file():
            raise ValueError("record or record_file is required")
        source = json.loads(record_path.read_text(encoding="utf-8"))
    return {
        "user_query": str(source.get("user_query", "")),
        "context": str(source.get("context", "")),
        "retrieval_query": str(source.get("retrieval_query", "")),
    }


def _remember_decisions(
    state: Path,
    stage: str,
    file: Path | None,
    decisions: list[dict[str, Any]],
    origin_id: str,
) -> None:
    for row in decisions:
        append_audit(
            state,
            {
                "stage": stage,
                "event": "claim_decision",
                "claim_id": row["claim_id"],
                "parent_origin_id": origin_id,
                "memory_file": str(file) if file else None,
                "claim_type": row["type"],
                "speech_act": row["speech_act"],
                "decision": row["decision"],
                "source_type": row["source_type"],
                "signals": row.get("signals", {}),
                "text_sha256": digest(row["text"]),
            },
        )


def execute(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    workspace = Path(str(payload["workspace"])).resolve()
    state = Path(str(payload["state_dir"])).resolve()
    if not workspace.is_dir():
        raise ValueError("workspace must be an existing directory")
    record = _load_record(payload)
    origin = record_origin(record)
    origin_id = digest(origin["user_query_sha256"] + origin["external_context_sha256"])[:20]

    if action == "bind_origin":
        state.mkdir(parents=True, exist_ok=True)
        origin_path = state / "origin.json"
        origin_blob = {"origin_id": origin_id, **origin}
        if origin_path.is_file():
            if json.loads(origin_path.read_text(encoding="utf-8")) != origin_blob:
                raise ValueError("record origin changed during a guarded run")
        else:
            origin_path.write_text(
                json.dumps(origin_blob, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            append_audit(
                state,
                {"stage": "ingress", "event": "origin_bound", "origin_id": origin_id, **origin},
            )
        return origin_blob

    if action == "preflight":
        content = str(payload.get("content", ""))
        projected, decisions = project_memory(content, record)
        _remember_decisions(state, "pre_write", None, decisions, origin_id)
        quarantined = [
            row["claim_id"]
            for row in decisions
            if row["decision"] == "quarantine_external_authority"
        ]
        neutralized = [
            row["claim_id"]
            for row in decisions
            if row["decision"] == "neutralize_external_destination"
        ]
        append_audit(
            state,
            {
                "stage": "pre_write",
                "event": "preflight_projection",
                "origin_id": origin_id,
                "candidate_count": len(decisions),
                "quarantined_claim_ids": quarantined,
                "neutralized_claim_ids": neutralized,
                "projection_sha256": digest(projected),
            },
        )
        return {
            "projected": projected,
            "candidate_count": len(decisions),
            "quarantined_claim_ids": quarantined,
            "neutralized_claim_ids": neutralized,
            "changed": projected != content,
            "projection_sha256": digest(projected),
        }

    if action == "admit":
        before = payload.get("before", {})
        if not isinstance(before, dict):
            before = {}
        changed = {
            str(contained(Path(str(path)), workspace))
            for path in payload.get("changed", [])
        }
        totals = {"candidate_count": 0, "quarantine_count": 0, "neutralized_count": 0}
        rewritten = 0
        files = []
        for file in memory_files(workspace):
            if str(file) not in changed:
                continue
            raw = file.read_text(encoding="utf-8", errors="replace")
            if len(raw.encode("utf-8")) > 2_000_000:
                raise ValueError("memory file exceeds 2 MB limit")
            projected, decisions = project_memory(raw, record)
            denied = [
                row["claim_id"]
                for row in decisions
                if row["decision"] == "quarantine_external_authority"
            ]
            neutralized = [
                row["claim_id"]
                for row in decisions
                if row["decision"] == "neutralize_external_destination"
            ]
            totals["candidate_count"] += len(decisions)
            totals["quarantine_count"] += len(denied)
            totals["neutralized_count"] += len(neutralized)
            _remember_decisions(state, "post_write", file, decisions, origin_id)
            if projected != raw:
                file.write_text(projected, encoding="utf-8")
                rewritten += 1
            files.append(
                {
                    "file": str(file),
                    "before_sha256": digest(str(before.get(str(file), ""))),
                    "raw_sha256": digest(raw),
                    "final_sha256": digest(projected),
                    "quarantined_claim_ids": denied,
                    "neutralized_claim_ids": neutralized,
                }
            )
        append_audit(
            state,
            {
                "stage": "post_write",
                "event": "memory_admission",
                "origin_id": origin_id,
                **totals,
                "rewritten_files": rewritten,
                "files": files,
            },
        )
        return {**totals, "rewritten_files": rewritten, "files": files}

    if action == "prepare_retrieval":
        if not verify_audit(state / "audit.jsonl"):
            raise ValueError("audit chain invalid before retrieval")
        selected: list[dict[str, Any]] = []
        rejected: list[str] = []
        changed_files = 0
        for file in memory_files(workspace):
            raw = file.read_text(encoding="utf-8", errors="replace")
            projected, decisions = project_memory(raw, record)
            denied = [
                row["claim_id"]
                for row in decisions
                if row["decision"] == "quarantine_external_authority"
            ]
            rejected.extend(denied)
            safe = [
                row
                for row in decisions
                if row["decision"]
                not in {"quarantine_external_authority", "rewrite_as_external_heading"}
            ]
            selected.extend({**row, "file": str(file)} for row in safe)
            if projected != raw:
                file.write_text(projected, encoding="utf-8")
                changed_files += 1
            append_audit(
                state,
                {
                    "stage": "retrieval",
                    "event": "memory_projection",
                    "origin_id": origin_id,
                    "file": str(file),
                    "before_sha256": digest(raw),
                    "after_sha256": digest(projected),
                    "selected_claim_ids": [row["claim_id"] for row in safe],
                    "rejected_claim_ids": denied,
                },
            )
        query = record["retrieval_query"]
        ranked = rank_candidates(selected, query)
        allowed_ids = {row["claim_id"] for row in ranked}
        filtered_ids = [row["claim_id"] for row in selected if row["claim_id"] not in allowed_ids]
        append_audit(
            state,
            {
                "stage": "retrieval",
                "event": "retrieval_filter",
                "origin_id": origin_id,
                "query_sha256": digest(query),
                "selected_claim_ids": [row["claim_id"] for row in ranked],
                "filtered_claim_ids": filtered_ids,
            },
        )
        return {
            "context": render_context(query, ranked),
            "selected_claim_ids": [row["claim_id"] for row in ranked],
            "rejected_claim_ids": rejected,
            "selected_candidates": len(ranked),
            "filtered_candidates": len(rejected) + len(filtered_ids),
            "file_changes": changed_files,
            "audit_valid": verify_audit(state / "audit.jsonl"),
        }

    if action == "tool_gate":
        tool = str(payload.get("tool", ""))
        params = payload.get("params", {})
        if not isinstance(params, dict):
            params = {}
        phase = str(payload.get("phase", "unknown"))
        verdict = check_tool(tool, params, record, phase, workspace)
        append_audit(
            state,
            {
                "stage": phase,
                "event": "action_gate",
                "origin_id": origin_id,
                "tool": tool,
                "params_sha256": digest(json.dumps(params, ensure_ascii=False, sort_keys=True)),
                **verdict,
            },
        )
        return verdict

    if action == "final_audit":
        phase = str(payload.get("phase", "unknown"))
        answer = str(payload.get("answer", ""))
        verdict = assess_unit(answer, record)
        revise = phase == "retrieval" and verdict["decision"] == "quarantine_external_authority"
        append_audit(
            state,
            {
                "stage": phase,
                "event": "final_answer_gate",
                "origin_id": origin_id,
                "answer_sha256": digest(answer),
                "claim_type": verdict["type"],
                "speech_act": verdict["speech_act"],
                "revise_requested": revise,
            },
        )
        return {
            "revise": revise,
            "claim_type": verdict["type"],
            "speech_act": verdict["speech_act"],
        }

    if action == "verify":
        return {
            "audit_valid": verify_audit(state / "audit.jsonl"),
            "origin_id": origin_id,
            "origin_file_exists": (state / "origin.json").is_file(),
        }
    raise ValueError(f"unknown bridge action: {action}")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: scmg-bridge ACTION")
    payload = json.load(sys.stdin)
    result = execute(sys.argv[1], payload)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
