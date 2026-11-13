#!/usr/bin/env python3
# Copyright 2026 Antigravity for Science Community Contributors
# Licensed under the Apache License, Version 2.0.

"""Deterministic SHA-256 manifest hashing for preprint hard-gate verification."""

# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

IGNORED_DIRS = {
    ".git",
    ".preprint_gate",
    ".agents",
    ".agent",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "node_modules",
    "dist",
    "build",
}

IGNORED_FILENAMES = {
    ".DS_Store",
    "SUBMISSION_COMPLIANCE_CERTIFICATE.md",
}

IGNORED_SUFFIXES = {
    ".aux",
    ".log",
    ".out",
    ".fls",
    ".fdb_latexmk",
    ".synctex.gz",
    ".blg",
    ".toc",
    ".lof",
    ".lot",
    ".tar.gz",
    ".tgz",
    ".zip",
    ".pyc",
}


def _is_ignored_file(filename: str) -> bool:
    if filename in IGNORED_FILENAMES or filename.startswith("."):
        return True
    lower = filename.lower()
    return any(lower.endswith(suffix) for suffix in IGNORED_SUFFIXES)


def _resolve_single_file_dependencies(manuscript_file: Path) -> list[tuple[str, Path]]:
    """Collects a target manuscript file plus its referenced .bib/.bbl and figure files."""
    target = manuscript_file.resolve()
    parent = target.parent
    collected: dict[str, Path] = {target.name: target}

    text = target.read_text(encoding="utf-8", errors="replace")
    clean = re.sub(r"(?<!\\)%.*$", "", text, flags=re.MULTILINE) if target.suffix.lower() == ".tex" else text

    # Sibling .bbl matching stem
    bbl = target.with_suffix(".bbl")
    if bbl.exists() and bbl.is_file():
        collected[bbl.name] = bbl

    # Referenced \bibliography{...} files
    for m_bib in re.finditer(r"\\bibliography\{([^}]+)\}", clean):
        for raw_name in m_bib.group(1).split(","):
            bname = raw_name.strip()
            if not bname:
                continue
            cand = (parent / (bname if bname.endswith(".bib") else f"{bname}.bib")).resolve()
            if cand.exists() and cand.is_file():
                rel_key = cand.name if cand.parent == parent else f"bib/{cand.name}"
                collected[rel_key] = cand

    # Fallback: sibling .bib if Markdown
    if target.suffix.lower() in (".md", ".qmd", ".rmd"):
        for bf in sorted(parent.glob("*.bib")):
            collected[bf.name] = bf.resolve()

    # Referenced \includegraphics{...} figures
    for m_img in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", clean):
        raw_img = m_img.group(1).strip()
        cand = (parent / raw_img).resolve()
        if not cand.exists():
            for ext in (".pdf", ".png", ".jpg", ".eps", ".svg"):
                if (parent / f"{raw_img}{ext}").exists():
                    cand = (parent / f"{raw_img}{ext}").resolve()
                    break
        if cand.exists() and cand.is_file():
            try:
                rel_key = cand.relative_to(parent).as_posix()
            except ValueError:
                rel_key = f"figures/{cand.name}"
            collected[rel_key] = cand

    return sorted(collected.items(), key=lambda kv: kv[0])


def compute_manuscript_manifest(
    manuscript_dir: str | Path,
    manuscript_file: str | Path | None = None,
) -> dict:
    """Computes per-file SHA-256 hashes and an aggregate Merkle-style digest."""
    if manuscript_file is not None:
        mfile = Path(manuscript_file).resolve()
        if not mfile.exists() or not mfile.is_file():
            raise FileNotFoundError(f"Manuscript file does not exist: {mfile}")
        files_map: dict[str, str] = {}
        for rel_key, fpath in _resolve_single_file_dependencies(mfile):
            files_map[rel_key] = hashlib.sha256(fpath.read_bytes()).hexdigest()
        root = mfile.parent
    else:
        root = Path(manuscript_dir).resolve()
        if root.is_file():
            return compute_manuscript_manifest(root.parent, manuscript_file=root)
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"Manuscript directory does not exist: {root}")

        files_map = {}
        for current_root, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS and not d.startswith("."))
            for fname in sorted(files):
                if _is_ignored_file(fname):
                    continue
                fpath = Path(current_root) / fname
                if fpath.is_symlink():
                    continue
                rel = fpath.relative_to(root).as_posix()
                files_map[rel] = hashlib.sha256(fpath.read_bytes()).hexdigest()

    aggregate = hashlib.sha256()
    for rel in sorted(files_map):
        aggregate.update(f"{rel}\0{files_map[rel]}\n".encode("utf-8"))

    return {
        "manuscript_dir": str(root),
        "manuscript_file": str(Path(manuscript_file).resolve()) if manuscript_file else None,
        "file_count": len(files_map),
        "files": files_map,
        "manuscript_sha256": aggregate.hexdigest(),
    }
