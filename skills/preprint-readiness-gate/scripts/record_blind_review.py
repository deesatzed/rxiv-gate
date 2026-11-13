#!/usr/bin/env python3
# Copyright 2026 Antigravity for Science Community Contributors
# Licensed under the Apache License, Version 2.0.

"""Validates and cryptographically binds a preprint-blind-auditor report to the manuscript SHA-256."""

# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

from gate_runner import resolve_default_gate_dir
from manifest_hash import compute_manuscript_manifest


def _extract_json_payload(raw: str) -> dict:
    fenced = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.DOTALL)
    candidate = fenced.group(1) if fenced else raw.strip()
    return json.loads(candidate)


def record_blind_review(
    manuscript_dir: Path,
    review_payload: dict,
    expected_server: str | None = None,
    manuscript_file: Path | None = None,
    state_dir: Path | None = None,
) -> dict:
    if manuscript_dir.is_file() and manuscript_file is None:
        manuscript_file = manuscript_dir
        manuscript_dir = manuscript_file.parent

    required_keys = {"auditor", "target_server", "verdict", "summary", "blockers", "warnings"}
    missing = required_keys - set(review_payload.keys())
    if missing:
        raise ValueError(f"Blind review JSON missing required keys: {sorted(missing)}")

    if review_payload.get("auditor") != "preprint-blind-auditor":
        raise ValueError(
            "Blind review 'auditor' must be 'preprint-blind-auditor' (produced by an isolated blind review subagent)."
        )

    if expected_server and review_payload.get("target_server", "").lower() != expected_server.lower():
        raise ValueError(
            f"Blind review target_server ('{review_payload.get('target_server')}') does not match "
            f"expected server ('{expected_server}')."
        )

    blockers = review_payload.get("blockers") or []
    if not isinstance(blockers, list):
        raise ValueError("Blind review 'blockers' must be a JSON list.")

    verdict = str(review_payload.get("verdict", "")).upper()
    if verdict not in ("PASS", "FAIL"):
        raise ValueError("Blind review 'verdict' must be 'PASS' or 'FAIL'.")

    if blockers and verdict == "PASS":
        verdict = "FAIL"

    manifest = compute_manuscript_manifest(manuscript_dir, manuscript_file=manuscript_file)
    record = {
        "auditor": "preprint-blind-auditor",
        "target_server": str(review_payload["target_server"]).lower(),
        "verdict": verdict,
        "summary": str(review_payload["summary"]).strip(),
        "blockers": blockers,
        "warnings": review_payload.get("warnings") or [],
        "checked_files": review_payload.get("checked_files") or sorted(manifest["files"].keys()),
        "manuscript_file": manifest.get("manuscript_file"),
        "manuscript_sha256": manifest["manuscript_sha256"],
        "file_count": manifest["file_count"],
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }

    gate_dir = resolve_default_gate_dir(
        manuscript_dir=manuscript_dir,
        manuscript_file=manuscript_file,
        state_dir=state_dir,
    )
    gate_dir.mkdir(parents=True, exist_ok=True)
    out_path = gate_dir / "blind_review.json"
    out_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind blind review attestation to current manuscript SHA-256.")
    parser.add_argument("--manuscript-dir", type=Path, default=None)
    parser.add_argument("--manuscript-file", type=Path, default=None)
    parser.add_argument("--state-dir", type=Path, default=None)
    parser.add_argument("--review-file", type=Path, help="Path to JSON or markdown containing ```json ... ``` output.")
    parser.add_argument("--server", type=str, default=None, help="Expected preprint server profile.")
    args = parser.parse_args()

    if not args.manuscript_dir and not args.manuscript_file:
        parser.error("Provide --manuscript-dir and/or --manuscript-file.")

    mfile = args.manuscript_file.resolve() if args.manuscript_file else None
    mdir = args.manuscript_dir.resolve() if args.manuscript_dir else mfile.parent

    raw = args.review_file.read_text(encoding="utf-8") if args.review_file else sys.stdin.read()
    try:
        payload = _extract_json_payload(raw)
        record = record_blind_review(
            mdir,
            payload,
            expected_server=args.server,
            manuscript_file=mfile,
            state_dir=args.state_dir.resolve() if args.state_dir else None,
        )
    except Exception as exc:  # pylint: disable=broad-except
        print(json.dumps({"recorded": False, "error": str(exc)}, indent=2))
        return 2

    print(json.dumps({"recorded": True, "record": record}, indent=2))
    return 0 if record["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
