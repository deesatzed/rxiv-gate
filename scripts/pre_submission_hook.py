#!/usr/bin/env python3
# Copyright 2026 Antigravity for Science Community Contributors
# Licensed under the Apache License, Version 2.0.

"""Antigravity PreToolUse Lifecycle Hook enforcing post-reverification SHA-256 seals."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PLUGIN_ROOT / "skills" / "preprint-readiness-gate" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from package_submission import verify_seal_or_raise  # noqa: E402

SUBMISSION_CMD_PAT = re.compile(
    r"(package_submission\.py|"
    r"\b(?:tar|zip)\b[^\n;]*(?:arxiv|biorxiv|medrxiv|chemrxiv|preprint[-_]submission|submission[-_]bundle)|"
    r"\b(?:curl|http|python3?)\b[^\n;]*(?:arxiv\.org/submit|submit\.biorxiv\.org|submit\.medrxiv\.org))",
    re.IGNORECASE,
)

TEST_RUNNER_PAT = re.compile(r"\b(pytest|unittest)\b")


def _extract_flag_path(cmd: str, flag: str, workspace_paths: list[str]) -> Path | None:
    m = re.search(rf"{flag}(?:=|\s+)([^\s\"']+)", cmd)
    if not m:
        return None
    candidate = Path(m.group(1)).expanduser()
    if not candidate.is_absolute() and workspace_paths:
        candidate = Path(workspace_paths[0]) / candidate
    return candidate.resolve()


def _extract_manuscript_dir(cmd: str, workspace_paths: list[str]) -> Path | None:
    explicit = _extract_flag_path(cmd, "--manuscript-dir", workspace_paths)
    if explicit:
        return explicit

    mfile = _extract_flag_path(cmd, "--manuscript-file", workspace_paths)
    if mfile:
        return mfile.parent

    for ws in workspace_paths:
        ws_path = Path(ws)
        if (ws_path / ".preprint_gate").exists():
            return ws_path.resolve()
        if list(ws_path.glob("*.tex")) or (ws_path / "manuscript.md").exists():
            return ws_path.resolve()
    return Path(workspace_paths[0]).resolve() if workspace_paths else None


def evaluate_hook(payload: dict) -> dict:
    tool_call = payload.get("toolCall") or {}
    if tool_call.get("name") != "run_command":
        return {"decision": "allow"}

    args = tool_call.get("args") or {}
    cmd = str(args.get("CommandLine") or "")
    if not cmd or TEST_RUNNER_PAT.search(cmd) or not SUBMISSION_CMD_PAT.search(cmd):
        return {"decision": "allow"}

    workspace_paths = payload.get("workspacePaths") or []
    manuscript_dir = _extract_manuscript_dir(cmd, workspace_paths)
    manuscript_file = _extract_flag_path(cmd, "--manuscript-file", workspace_paths)
    state_dir = _extract_flag_path(cmd, "--state-dir", workspace_paths)

    if manuscript_dir is None or not manuscript_dir.exists():
        return {
            "decision": "deny",
            "reason": (
                "PREPRINT HARD GATE: Could not locate a sealed manuscript directory for submission command. "
                "Run Pass-1 audit, blind review, and Pass-2 re-verification first."
            ),
        }

    try:
        verify_seal_or_raise(
            manuscript_dir,
            manuscript_file=manuscript_file,
            state_dir=state_dir,
        )
    except Exception as exc:  # pylint: disable=broad-except
        return {
            "decision": "deny",
            "reason": str(exc),
        }

    return {"decision": "allow"}


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        decision = evaluate_hook(payload)
    except Exception as exc:  # pylint: disable=broad-except
        decision = {"decision": "allow", "reason": f"Hook parse fallback: {exc}"}

    sys.stdout.write(json.dumps(decision) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
