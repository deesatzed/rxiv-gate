#!/usr/bin/env python3
# Copyright 2026 Antigravity for Science Community Contributors
# Licensed under the Apache License, Version 2.0.

"""Packages a preprint archive ONLY if a valid, non-drifted Pass-2 Release Seal exists."""

# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

from __future__ import annotations

import argparse
import io
import json
import sys
import tarfile
from pathlib import Path

from gate_runner import resolve_default_gate_dir
from manifest_hash import _resolve_single_file_dependencies, compute_manuscript_manifest


def verify_seal_or_raise(
    manuscript_dir: Path,
    expected_server: str | None = None,
    manuscript_file: Path | None = None,
    state_dir: Path | None = None,
) -> tuple[dict, dict]:
    """Verifies release_seal.json against live manuscript SHA-256."""
    if manuscript_dir.is_file() and manuscript_file is None:
        manuscript_file = manuscript_dir
        manuscript_dir = manuscript_file.parent

    gate_dir = resolve_default_gate_dir(
        manuscript_dir=manuscript_dir,
        manuscript_file=manuscript_file,
        state_dir=state_dir,
    )
    seal_path = gate_dir / "release_seal.json"
    if not seal_path.exists():
        raise PermissionError(
            f"HARD GATE BLOCKED: Missing {seal_path}. "
            "Complete Pass-1 audit, isolated blind review, and Pass-2 '--mode reverify' first."
        )

    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    if seal.get("status") != "SEALED_FOR_SUBMISSION" or not seal.get("reverified"):
        raise PermissionError(
            f"HARD GATE BLOCKED: Invalid release seal status '{seal.get('status')}'."
        )

    if expected_server and seal.get("target_server", "").lower() != expected_server.lower():
        raise PermissionError(
            f"HARD GATE BLOCKED: Release seal is for '{seal.get('target_server')}', "
            f"not '{expected_server}'."
        )

    sealed_mfile = Path(seal["manuscript_file"]) if seal.get("manuscript_file") else manuscript_file
    live_manifest = compute_manuscript_manifest(manuscript_dir, manuscript_file=sealed_mfile)
    if live_manifest["manuscript_sha256"] != seal.get("manuscript_sha256"):
        sealed_files = seal.get("files") or {}
        live_files = live_manifest["files"]
        changed = sorted(
            set(sealed_files.keys()) ^ set(live_files.keys())
            | {k for k in set(sealed_files) & set(live_files) if sealed_files[k] != live_files[k]}
        )
        raise PermissionError(
            "HARD GATE BLOCKED (POST-SEAL DRIFT): Manuscript SHA-256 changed after Pass-2 re-verification! "
            f"Drifted files: {changed}. Re-run blind review and 'gate_runner.py --mode reverify'."
        )

    if seal.get("blind_review_sha256") != live_manifest["manuscript_sha256"]:
        raise PermissionError(
            "HARD GATE BLOCKED: Blind review SHA-256 does not match live manuscript SHA-256."
        )

    return seal, live_manifest


def _render_certificate(seal: dict, live_manifest: dict) -> str:
    lines = [
        "# Preprint Submission Compliance Certificate",
        "",
        f"- **Status**: `{seal['status']}`",
        f"- **Seal ID**: `{seal['seal_id']}`",
        f"- **Target Preprint Server**: `{seal['target_server']}`",
        f"- **Manuscript Merkle SHA-256**: `{live_manifest['manuscript_sha256']}`",
        f"- **Blind Review Attestation SHA-256**: `{seal['blind_review_sha256']}`",
        f"- **Sealed Timestamp (UTC)**: `{seal['sealed_at']}`",
        "",
        "## Verified Hard Gates",
        "",
        "1. `G1_AI_ATTRIBUTION`: PASS (Human authorship only, AI workflow disclosure, Google Science program acknowledgment)",
        "2. `G2_SKILL_LICENSES`: PASS (All detected Science Plugin third-party databases/tools cited per `SKILL_LICENSES.md`)",
        "3. `G3_CITATIONS`: PASS (Identifiers resolved and title-verified; zero placeholders)",
        f"4. `G4_SERVER_SCREENING`: PASS (`{seal['target_server']}` screening & ethics/clinical safety profile)",
        "5. `G5_CLAIM_GROUNDING`: PASS (Computational vs. experimental claim framing verified)",
        "6. `G6_REVERIFICATION_SEAL`: PASS (Two-pass audit + fresh-context blind review SHA-256 lock)",
        "",
        "## Sealed File Manifest",
        "",
        "| File | SHA-256 |",
        "| :--- | :--- |",
    ]
    for rel, sha in sorted(live_manifest["files"].items()):
        lines.append(f"| `{rel}` | `{sha}` |")
    lines.append("")
    return "\n".join(lines)


def package_sealed_submission(
    manuscript_dir: Path,
    output_archive: Path,
    expected_server: str | None = None,
    manuscript_file: Path | None = None,
    state_dir: Path | None = None,
) -> dict:
    seal, live_manifest = verify_seal_or_raise(
        manuscript_dir,
        expected_server=expected_server,
        manuscript_file=manuscript_file,
        state_dir=state_dir,
    )
    cert_md = _render_certificate(seal, live_manifest)

    sealed_mfile = Path(seal["manuscript_file"]) if seal.get("manuscript_file") else manuscript_file
    if sealed_mfile is not None:
        file_pairs = _resolve_single_file_dependencies(sealed_mfile)
    else:
        file_pairs = [(rel, manuscript_dir / rel) for rel in sorted(live_manifest["files"].keys())]

    output_archive.parent.mkdir(parents=True, exist_ok=True)
    cert_path = (state_dir or output_archive.parent) / "SUBMISSION_COMPLIANCE_CERTIFICATE.md"
    if sealed_mfile is None and state_dir is None:
        cert_path = manuscript_dir / "SUBMISSION_COMPLIANCE_CERTIFICATE.md"
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    cert_path.write_text(cert_md, encoding="utf-8")

    with tarfile.open(output_archive, "w:gz") as tar:
        for rel, fpath in file_pairs:
            tar.add(fpath, arcname=rel)
        cert_bytes = cert_md.encode("utf-8")
        info = tarfile.TarInfo(name="SUBMISSION_COMPLIANCE_CERTIFICATE.md")
        info.size = len(cert_bytes)
        tar.addfile(info, io.BytesIO(cert_bytes))

    return {
        "packaged": True,
        "archive_path": str(output_archive),
        "certificate_path": str(cert_path),
        "seal_id": seal["seal_id"],
        "manuscript_sha256": live_manifest["manuscript_sha256"],
        "file_count": live_manifest["file_count"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Package a Pass-2 sealed preprint submission bundle.")
    parser.add_argument("--manuscript-dir", type=Path, default=None)
    parser.add_argument("--manuscript-file", type=Path, default=None)
    parser.add_argument("--state-dir", type=Path, default=None)
    parser.add_argument("--output", required=True, type=Path, help="Output .tar.gz path.")
    parser.add_argument("--server", type=str, default=None, help="Optional expected server profile check.")
    args = parser.parse_args()

    if not args.manuscript_dir and not args.manuscript_file:
        parser.error("Provide --manuscript-dir and/or --manuscript-file.")

    mfile = args.manuscript_file.resolve() if args.manuscript_file else None
    mdir = args.manuscript_dir.resolve() if args.manuscript_dir else mfile.parent

    try:
        res = package_sealed_submission(
            manuscript_dir=mdir,
            output_archive=args.output.resolve(),
            expected_server=args.server,
            manuscript_file=mfile,
            state_dir=args.state_dir.resolve() if args.state_dir else None,
        )
    except PermissionError as exc:
        print(json.dumps({"packaged": False, "hard_gate_blocked": True, "error": str(exc)}, indent=2))
        return 2

    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
