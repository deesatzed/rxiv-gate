#!/usr/bin/env python3
# Copyright 2026 Antigravity for Science Community Contributors
# Licensed under the Apache License, Version 2.0.

"""Deterministic 6-Gate Preprint Compliance & Two-Pass Re-Verification Engine.

Gates enforced:
  G1_AI_ATTRIBUTION      - No AI authorship, AI workflow disclosure + human verification,
                           Google Antigravity / AI for Science acknowledgment, no unapproved logos.
  G2_SKILL_LICENSES      - Third-party database & tool citations per Science SKILL_LICENSES.md.
  G3_CITATIONS           - Live/mock citation resolution + title similarity + zero placeholders.
  G4_SERVER_SCREENING    - arXiv / bioRxiv / medRxiv / ChemRxiv screening & clinical safety gates.
  G5_CLAIM_GROUNDING     - In-silico vs. wet-lab/clinical claim qualification.
  G6_REVERIFICATION_SEAL - Enforces Pass-1 -> Blind Review -> Pass-2 SHA-256 lock before sealing.
"""

# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

from manifest_hash import compute_manuscript_manifest
from verify_citations import (
    extract_cited_keys_from_text,
    parse_bibtex_file,
    verify_manuscript_citations,
)

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REGISTRY_PATH = SKILL_ROOT / "references" / "skill_license_registry.json"

SUPPORTED_SERVERS = ("arxiv", "biorxiv", "medrxiv", "chemrxiv")

PROHIBITED_AI_AUTHORS = re.compile(
    r"\b(antigravity|gemini|chatgpt|gpt-[345]|claude|copilot|alphafold|deepmind\s+ai|large\s+language\s+model)\b",
    re.IGNORECASE,
)

UNAPPROVED_LOGO_PAT = re.compile(
    r"(google[-_ ]?logo|deepmind[-_ ]?logo|antigravity[-_ ]?(?:logo|badge))",
    re.IGNORECASE,
)

PLACEHOLDER_PAT = re.compile(
    r"(\bTODO\b|\bTBD\b|\bFIXME\b|\bINSERT_CITATION\b|\[\?\]|\bXX+\s*%|\bORG/REPO\b|\bXXXXXXX\b)"
)

COMPUTATIONAL_MARKERS = re.compile(
    r"\b(in\s+silico|docking|autodock|vina|smina|alphafold|boltz|plddt|avi\s+score|alphagenome|"
    r"molecular\s+dynamics|openmm|qsar|co-folding|cofolding|simulated\s+trajectory|computational\s+screen|"
    r"ode\s+model|host-emulated|discrete-adjoint)\b",
    re.IGNORECASE,
)

WETLAB_MARKERS = re.compile(
    r"\b(in\s+vitro\s+assay|in\s+vivo\s+mouse|surface\s+plasmon\s+resonance|isothermal\s+titration|"
    r"western\s+blot|elisa|flow\s+cytometry|crispr\s+knockout|x-ray\s+crystallography|cryo-em\s+density|"
    r"cell\s+viability\s+assay|ic50\s+was\s+measured|biochemical\s+assay\s+performed|"
    r"wet-lab\s+(?:assay|experiments?\s+were\s+performed))\b",
    re.IGNORECASE,
)

OVERSTATED_CLAIMS = re.compile(
    r"\b(experimentally\s+confirmed|experimentally\s+validated|clinically\s+proven|proves\s+clinical\s+efficacy|"
    r"definitive\s+cure|confirms\s+in\s+vivo\s+efficacy|wet-lab\s+confirmed)\b",
    re.IGNORECASE,
)

COMPUTATIONAL_HEDGING = re.compile(
    r"\b(in\s+silico|computational|predicted|predictive|putative|simulated|simulation|modeling|modelling|"
    r"host-emulated|ode\s+model|hypothesis-generating)\b",
    re.IGNORECASE,
)


def _strip_tex_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        cleaned = re.sub(r"(?<!\\)%.*$", "", line)
        lines.append(cleaned)
    return "\n".join(lines)


def _normalize_latex_inline(text: str) -> str:
    """Unwraps inline LaTeX formatting commands (\textbf{...}, ~) for reliable prose matching."""
    out = text.replace("~", " ").replace("\\&", "&")
    for _ in range(3):
        out = re.sub(r"\\(?:textbf|textit|emph|texttt|textrm|textsc)\{([^{}]*)\}", r"\1", out)
    out = re.sub(r"\\LaTeX\{\}", "LaTeX", out)
    return re.sub(r"[ \t]+", " ", out)


def resolve_default_gate_dir(
    manuscript_dir: Path,
    manuscript_file: Path | None = None,
    state_dir: Path | None = None,
) -> Path:
    if state_dir is not None:
        return state_dir.resolve()
    if manuscript_file is not None:
        return (manuscript_file.resolve().parent / ".preprint_gate" / manuscript_file.stem).resolve()
    return (manuscript_dir.resolve() / ".preprint_gate").resolve()


def _collect_manuscript_sources(manuscript_dir: Path, manuscript_file: Path | None = None) -> dict:
    if manuscript_file is not None:
        mfile = manuscript_file.resolve()
        tex_files = [mfile] if mfile.suffix.lower() == ".tex" else []
        md_files = [mfile] if mfile.suffix.lower() in (".md", ".qmd", ".rmd") else []
        bib_files = sorted(mfile.parent.glob("*.bib"))
        code_files: list[Path] = []
    else:
        tex_files = sorted(
            p for p in manuscript_dir.rglob("*.tex") if ".preprint_gate" not in p.parts
        )
        md_files = sorted(
            p
            for p in manuscript_dir.rglob("*.md")
            if ".preprint_gate" not in p.parts
            and p.name not in ("SUBMISSION_COMPLIANCE_CERTIFICATE.md", "README.md")
            and not p.name.startswith("README_")
        )
        bib_files = sorted(
            p for p in manuscript_dir.rglob("*.bib") if ".preprint_gate" not in p.parts
        )
        code_files = sorted(
            p
            for p in manuscript_dir.rglob("*")
            if p.is_file()
            and p.suffix.lower() in (".py", ".r", ".sh")
            and ".preprint_gate" not in p.parts
        )

    manuscript_files = tex_files + md_files
    combined_prose_parts: list[str] = []
    for f in manuscript_files:
        raw = f.read_text(encoding="utf-8", errors="replace")
        combined_prose_parts.append(_strip_tex_comments(raw) if f.suffix.lower() == ".tex" else raw)

    combined_prose = "\n\n".join(combined_prose_parts)
    normalized_prose = _normalize_latex_inline(combined_prose)
    combined_code = "\n\n".join(
        f.read_text(encoding="utf-8", errors="replace") for f in code_files
    )

    bib_entries: list[dict] = []
    raw_bib_text = ""
    for bf in bib_files:
        raw_bib_text += "\n" + bf.read_text(encoding="utf-8", errors="replace")
        parsed_entries, _ = parse_bibtex_file(bf)
        bib_entries.extend(parsed_entries)

    if manuscript_file is not None and bib_entries:
        cited_keys, _ = extract_cited_keys_from_text(manuscript_files)
        scoped_entries = [e for e in bib_entries if e["key"] in cited_keys]
        scoped_bib_text = "\n".join(json.dumps(e) for e in scoped_entries)
    else:
        scoped_entries = bib_entries
        scoped_bib_text = raw_bib_text

    return {
        "manuscript_files": manuscript_files,
        "tex_files": tex_files,
        "md_files": md_files,
        "bib_files": bib_files,
        "bib_entries": scoped_entries,
        "raw_bib_text": scoped_bib_text,
        "combined_prose": combined_prose,
        "normalized_prose": normalized_prose,
        "combined_code": combined_code,
    }


def _extract_balanced_brace_arg(text: str, command: str) -> list[str]:
    results: list[str] = []
    pat = re.compile(rf"\\{command}\*?\s*(?:\[[^\]]*\]\s*)*\{{", re.IGNORECASE)
    pos = 0
    while True:
        m = pat.search(text, pos)
        if not m:
            break
        idx = m.end()
        depth = 1
        while idx < len(text) and depth > 0:
            if text[idx] == "{":
                depth += 1
            elif text[idx] == "}":
                depth -= 1
            idx += 1
        results.append(text[m.end() : max(m.end(), idx - 1)].strip())
        pos = idx
    return results


def _extract_title_abstract_authors_conclusions(sources: dict) -> dict:
    prose = sources["combined_prose"]
    title = ""
    abstract = ""
    authors_block = ""
    conclusions = ""

    titles = _extract_balanced_brace_arg(prose, "title")
    if titles:
        title = titles[0]
    authors = _extract_balanced_brace_arg(prose, "author")
    if authors:
        authors_block = " ; ".join(authors)

    m_abs_tex = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", prose, re.DOTALL | re.I)
    if m_abs_tex:
        abstract = m_abs_tex.group(1).strip()

    if not title:
        m_h1 = re.search(r"^#\s+(.+)$", prose, re.MULTILINE)
        if m_h1:
            title = m_h1.group(1).strip()
        else:
            m_yaml_t = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", prose, re.MULTILINE | re.I)
            if m_yaml_t:
                title = m_yaml_t.group(1).strip()

    if not authors_block:
        m_md_auth = re.search(
            r"(?:^\*\*Authors?:\*\*|^Authors?:)\s*(.+)$", prose, re.MULTILINE | re.I
        )
        if m_md_auth:
            authors_block = m_md_auth.group(1).strip()
        else:
            m_yaml_a = re.search(
                r"^authors?:\s*(.+?)(?:\n[a-zA-Z_]+:|\n---)", prose, re.DOTALL | re.MULTILINE | re.I
            )
            if m_yaml_a:
                authors_block = m_yaml_a.group(1).strip()

    if not abstract:
        m_md_abs = re.search(
            r"^##?\s*Abstract\s*\n+(.*?)(?=\n##?\s+|\Z)", prose, re.DOTALL | re.MULTILINE | re.I
        )
        if m_md_abs:
            abstract = m_md_abs.group(1).strip()

    m_conc_tex = re.search(
        r"\\section\*?\{(?:Conclusion|Conclusions|Discussion(?:,\s*Limitations,)?[^}]*)\}(.*?)(?=\\appendix|\\section|\\bibliography|\\end\{document\}|\Z)",
        prose,
        re.DOTALL | re.I,
    )
    if m_conc_tex:
        conclusions = m_conc_tex.group(1).strip()
    else:
        m_conc_md = re.search(
            r"^##?\s*(?:Conclusion|Conclusions|Discussion and Conclusions)\s*\n+(.*?)(?=\n##?\s+|\Z)",
            prose,
            re.DOTALL | re.MULTILINE | re.I,
        )
        if m_conc_md:
            conclusions = m_conc_md.group(1).strip()

    return {
        "title": title,
        "abstract": abstract,
        "authors_block": authors_block,
        "conclusions": conclusions,
    }


def evaluate_g1_ai_attribution(
    sources: dict,
    sections: dict,
    antigravity_used: bool = True,
    program_member: bool = True,
    brand_approved: bool = False,
) -> dict:
    failures: list[dict] = []
    warnings: list[dict] = []
    prose = sources["combined_prose"]
    norm = sources["normalized_prose"]

    if not sources["manuscript_files"]:
        failures.append(
            {
                "code": "NO_MANUSCRIPT_SOURCE",
                "detail": "No .tex or .md manuscript file found in target scope.",
            }
        )
        return {"gate": "G1_AI_ATTRIBUTION", "passed": False, "failures": failures, "warnings": warnings}

    # 1. Prohibited AI Authorship
    if sections["authors_block"] and PROHIBITED_AI_AUTHORS.search(sections["authors_block"]):
        failures.append(
            {
                "code": "AI_LISTED_AS_AUTHOR",
                "detail": (
                    f"AI system/model detected in author block ('{sections['authors_block'][:120]}'). "
                    "ICMJE, COPE, arXiv, bioRxiv, and medRxiv strictly forbid listing AI tools as authors."
                ),
            }
        )

    # 2. Methods / AI Collaboration Disclosure + Human Verification
    if antigravity_used:
        has_platform = bool(
            re.search(r"(?:google(?:\s+deepmind(?:'s)?)?\s+antigravity|\bantigravity\s+ai\b)", norm, re.I)
        )
        has_model = bool(re.search(r"\bgemini\b", norm, re.I))
        has_human_verif = bool(
            re.search(
                r"(independently\s+(?:executed\s+and\s+)?verified|verified\s+by\s+(?:the\s+)?(?:human\s+)?authors?|"
                r"human[- ]verified|reviewed\s+and\s+validated\s+by\s+(?:the\s+)?authors?|"
                r"audited,\s*verified,\s*and\s+takes\s+full\s+scholarly\s+responsibility|"
                r"takes?\s+full\s+(?:scholarly\s+)?responsibility\s+for\s+the\s+integrity)",
                norm,
                re.I,
            )
        )
        if not (has_platform and has_model and has_human_verif):
            missing_parts = []
            if not has_platform:
                missing_parts.append("'Google Antigravity' platform name")
            if not has_model:
                missing_parts.append("underlying 'Gemini' model identifier")
            if not has_human_verif:
                missing_parts.append("explicit human author verification/responsibility attestation")
            failures.append(
                {
                    "code": "INCOMPLETE_AI_WORKFLOW_DISCLOSURE",
                    "detail": (
                        "Manuscript lacks required AI workflow disclosure: missing "
                        + ", ".join(missing_parts)
                        + "."
                    ),
                }
            )
        else:
            # Check whether exact Gemini model version (e.g. Gemini 4 Argon / Carbon / 2.5 / 3) is named
            if not re.search(r"\bgemini\s+(?:\d+(?:\.\d+)?|argon|carbon|pro|ultra|flash)\b", norm, re.I):
                warnings.append(
                    {
                        "code": "UNSPECIFIED_GEMINI_MODEL_VERSION",
                        "detail": (
                            "Manuscript mentions 'Gemini' generically without specifying the exact model version "
                            "(e.g., 'Gemini 4 Argon' or 'Gemini 4 Carbon') recommended for computational reproducibility."
                        ),
                    }
                )

    # 3. Google Antigravity for Science Program Acknowledgment
    if program_member:
        has_exact_prog = bool(re.search(r"google\s+antigravity\s+(?:for\s+)?science", norm, re.I))
        has_alt_prog = bool(re.search(r"google\s+ai\s+for\s+science", norm, re.I))
        if not (has_exact_prog or has_alt_prog):
            failures.append(
                {
                    "code": "MISSING_SCIENCE_PROGRAM_ACKNOWLEDGMENT",
                    "detail": (
                        "Acknowledgments section does not credit the 'Google Antigravity for Science' program. "
                        "(Pass --no-program-member only if manuscript was produced outside the program)."
                    ),
                }
            )
        elif has_alt_prog and not has_exact_prog:
            warnings.append(
                {
                    "code": "VERIFY_EXACT_PROGRAM_NAME",
                    "detail": (
                        "Acknowledgments credit 'Google AI for Science Researcher Access Program' rather than "
                        "'Google Antigravity for Science'. Verify exact program title against your acceptance letter."
                    ),
                }
            )

    # 4. Unapproved Google / DeepMind Logos
    if not brand_approved:
        img_refs = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", prose) + re.findall(
            r"!\[[^\]]*\]\(([^)]+)\)", prose
        )
        for ref in img_refs:
            if UNAPPROVED_LOGO_PAT.search(ref):
                failures.append(
                    {
                        "code": "UNAPPROVED_BRAND_LOGO",
                        "detail": (
                            f"Embedded logo/badge '{ref}' detected. Do not place Google or DeepMind logos on "
                            "preprints without written brand permission."
                        ),
                    }
                )

    return {
        "gate": "G1_AI_ATTRIBUTION",
        "passed": len(failures) == 0,
        "failures": failures,
        "warnings": warnings,
    }


def evaluate_g2_skill_licenses(
    manuscript_dir: Path,
    sources: dict,
    manuscript_file: Path | None = None,
) -> dict:
    failures: list[dict] = []
    warnings: list[dict] = []
    detected_resources: list[dict] = []

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    searchable_usage = sources["normalized_prose"] + "\n" + sources["combined_code"]

    if manuscript_file is None:
        licenses_dir = manuscript_dir / ".licenses"
        if licenses_dir.exists() and licenses_dir.is_dir():
            for lf in sorted(licenses_dir.glob("*")):
                if lf.is_file():
                    searchable_usage += "\n" + lf.name + "\n" + lf.read_text(encoding="utf-8", errors="replace")

    bib_corpus = sources["raw_bib_text"].lower()
    m_md_refs = re.search(
        r"^##?\s*(?:References|Bibliography)\s*\n+(.*)",
        sources["combined_prose"],
        re.DOTALL | re.MULTILINE | re.I,
    )
    if m_md_refs:
        bib_corpus += "\n" + m_md_refs.group(1).lower()

    for res in registry.get("resources", []):
        matched = any(re.search(pat, searchable_usage, re.I) for pat in res["detect_patterns"])
        if not matched:
            continue
        is_cited = any(tok.lower() in bib_corpus for tok in res["cite_tokens"])
        detected_resources.append(
            {
                "id": res["id"],
                "name": res["name"],
                "cited": is_cited,
                "terms_url": res["terms_url"],
            }
        )
        if not is_cited:
            failures.append(
                {
                    "code": "MISSING_SKILL_DATABASE_CITATION",
                    "resource_id": res["id"],
                    "resource_name": res["name"],
                    "terms_url": res["terms_url"],
                    "recommended_citation": res["recommended_citation"],
                    "detail": (
                        f"Detected use of {res['name']} (skills: {', '.join(res['skills'])}), "
                        f"but no matching citation was found in .bib / References. "
                        f"Required per SKILL_LICENSES.md ({res['terms_url']}). "
                        f"Suggested citation: {res['recommended_citation']}"
                    ),
                }
            )

    return {
        "gate": "G2_SKILL_LICENSES",
        "passed": len(failures) == 0,
        "detected_resources": detected_resources,
        "failures": failures,
        "warnings": warnings,
    }


def evaluate_g3_citations(
    manuscript_dir: Path,
    manuscript_file: Path | None,
    sources: dict,
    mode: str,
    citation_mode: str,
    mock_registry: Path | None,
) -> dict:
    failures: list[dict] = []
    warnings: list[dict] = []

    if mode == "reverify" and citation_mode == "syntax-only":
        failures.append(
            {
                "code": "SYNTAX_ONLY_FORBIDDEN_IN_REVERIFY",
                "detail": "Pass-2 re-verification forbids '--citation-mode syntax-only'; live ('online') or deterministic 'mock' registry verification is required.",
            }
        )
        return {"gate": "G3_CITATIONS", "passed": False, "failures": failures, "warnings": warnings}

    for fpath in sources["manuscript_files"]:
        raw = fpath.read_text(encoding="utf-8", errors="replace")
        for idx, line in enumerate(raw.splitlines(), start=1):
            check_line = re.sub(r"(?<!\\)%.*$", "", line) if fpath.suffix.lower() == ".tex" else line
            m_ph = PLACEHOLDER_PAT.search(check_line)
            if m_ph:
                failures.append(
                    {
                        "code": "UNRESOLVED_PLACEHOLDER",
                        "location": f"{fpath.name}:L{idx}",
                        "token": m_ph.group(1),
                        "detail": f"Unresolved placeholder '{m_ph.group(1)}' found at {fpath.name}:L{idx}.",
                    }
                )

    cit_report = verify_manuscript_citations(
        manuscript_dir=manuscript_dir,
        manuscript_file=manuscript_file,
        mode=citation_mode,
        mock_registry_path=mock_registry,
    )
    failures.extend(cit_report["failures"])
    warnings.extend(cit_report["warnings"])

    if cit_report["bib_entry_count"] == 0 and cit_report["cited_key_count"] == 0:
        failures.append(
            {
                "code": "ZERO_REFERENCES_FOUND",
                "detail": "Scientific preprint contains zero verifiable bibliographic references (.bib entries).",
            }
        )

    return {
        "gate": "G3_CITATIONS",
        "passed": len(failures) == 0,
        "citation_summary": {
            "mode": citation_mode,
            "bib_entry_count": cit_report["bib_entry_count"],
            "cited_key_count": cit_report["cited_key_count"],
            "verified_count": cit_report["verified_count"],
        },
        "failures": failures,
        "warnings": warnings,
    }


def evaluate_g4_server_screening(server: str, sources: dict, sections: dict) -> dict:
    failures: list[dict] = []
    warnings: list[dict] = []
    prose = sources["combined_prose"]
    norm = sources["normalized_prose"]

    # 1. Title & Abstract length + arXiv 1,920-char portal limit
    if not sections["title"].strip():
        failures.append({"code": "MISSING_TITLE", "detail": "Manuscript lacks a detectable Title."})

    clean_abs = re.sub(r"^\\noindent\s*", "", sections["abstract"].strip())
    clean_abs_norm = re.sub(r"\s+", " ", clean_abs)
    abs_words = re.findall(r"\S+", re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", clean_abs_norm))
    if len(abs_words) < 30:
        failures.append(
            {
                "code": "ABSTRACT_TOO_SHORT_OR_MISSING",
                "detail": f"Abstract has {len(abs_words)} words (minimum 30 required for {server} screening).",
            }
        )
    elif len(abs_words) > 500:
        failures.append(
            {
                "code": "ABSTRACT_EXCEEDS_LIMIT",
                "detail": f"Abstract has {len(abs_words)} words (maximum 500 allowed for preprint metadata).",
            }
        )

    if server == "arxiv" and len(clean_abs_norm) > 1920:
        failures.append(
            {
                "code": "ARXIV_ABSTRACT_CHAR_LIMIT_EXCEEDED",
                "char_count": len(clean_abs_norm),
                "detail": f"Abstract length ({len(clean_abs_norm)} chars) exceeds arXiv's hard 1,920-character Step-3 portal limit.",
            }
        )

    if server == "arxiv" and re.search(r"\\(?:cite[a-zA-Z]*|ref|eqref)\s*\{", clean_abs):
        warnings.append(
            {
                "code": "ARXIV_CITE_OR_REF_IN_ABSTRACT",
                "detail": (
                    "Abstract contains LaTeX \\cite{} or \\ref{} commands; arXiv's Step-3 web metadata field "
                    "renders plain text/MathJax only and cannot resolve bibliography keys."
                ),
            }
        )

    # 2. Author Affiliations
    has_affil = bool(
        re.search(
            r"(\\affil|\\affiliation|department\s+of|university|institute|hospital|laboratory|"
            r"school\s+of|center\s+for|centre\s+for|college\s+of)",
            norm,
            re.I,
        )
    )
    if not has_affil:
        failures.append(
            {
                "code": "MISSING_AUTHOR_AFFILIATIONS",
                "detail": "Author institutional affiliations could not be detected (required by all preprint servers).",
            }
        )

    # 3. Data & Code Availability / Reproducibility Statement
    has_data_sec = bool(
        re.search(
            r"(data\s+and\s+code\s+availability|data\s+availability|code\s+availability|"
            r"code\s*&\s*reproducibility|reproducibility\s+manifest)",
            norm,
            re.I,
        )
    )
    has_repo_or_doi = bool(
        re.search(
            r"(https?://(?:github\.com|gitlab\.com|zenodo\.org|figshare\.com|osf\.io|huggingface\.co)/\S+|"
            r"10\.5281/zenodo\.\d+|GSE\d{4,}|PRJNA\d{4,}|PXD\d{5,}|upon\s+reasonable\s+request)",
            norm,
            re.I,
        )
    )
    if not has_data_sec or not has_repo_or_doi:
        failures.append(
            {
                "code": "MISSING_DATA_CODE_AVAILABILITY",
                "detail": (
                    "Manuscript requires a concrete Data/Code Availability or Reproducibility statement "
                    "containing a valid repository URL, Zenodo DOI, or public archive accession."
                ),
            }
        )

    # 4. Competing Interests / COI
    has_coi = bool(
        re.search(
            r"(competing\s+(?:financial\s+or\s+commercial\s+)?interests?|conflicts?\s+of\s+interest|"
            r"declares?\s+no\s+competing)",
            norm,
            re.I,
        )
    )
    if not has_coi:
        if server in ("biorxiv", "medrxiv", "chemrxiv"):
            failures.append(
                {
                    "code": "MISSING_COMPETING_INTERESTS",
                    "detail": f"{server} requires an explicit Competing Interests / Conflict of Interest declaration.",
                }
            )
        else:
            warnings.append(
                {
                    "code": "RECOMMENDED_COMPETING_INTERESTS",
                    "detail": "Adding a Competing Interests statement is recommended for arXiv submissions.",
                }
            )

    # 5. TeX Source Portability (machine-local paths, \write18 shell escape, missing figures, '..' traversal)
    for tf in sources["tex_files"]:
        raw = _strip_tex_comments(tf.read_text(encoding="utf-8", errors="replace"))
        if re.search(r"\\(?:immediate\s*)?\\write18\b", raw):
            failures.append(
                {
                    "code": "FORBIDDEN_TEX_WRITE18",
                    "location": tf.name,
                    "detail": (
                        f"Shell-escape macro '\\write18' detected in {tf.name}. "
                        "arXiv, bioRxiv, and medRxiv AutoTeX strictly disable and reject shell-escape execution."
                    ),
                }
            )
        abs_paths = re.findall(
            r"\\(?:includegraphics|input|include|bibliography)(?:\[[^\]]*\])?\{((?:/Users/|/home/|[A-Za-z]:\\)[^}]+)\}",
            raw,
        )
        for ap in abs_paths:
            failures.append(
                {
                    "code": "NON_PORTABLE_TEX_PATH",
                    "location": tf.name,
                    "detail": f"Machine-local path '{ap}' in {tf.name} will fail server TeX compilation.",
                }
            )
        rel_figs = re.findall(
            r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}",
            raw,
        )
        for fig_ref in rel_figs:
            fig_ref_clean = fig_ref.strip()
            if re.match(r"^(?:/Users/|/home/|[A-Za-z]:\\)", fig_ref_clean):
                continue
            cand = (tf.parent / fig_ref_clean).resolve()
            exists = cand.exists() or any(
                cand.with_suffix(ext).exists()
                for ext in (".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg")
            )
            if not exists:
                failures.append(
                    {
                        "code": "MISSING_REFERENCED_FIGURE",
                        "location": tf.name,
                        "figure": fig_ref_clean,
                        "detail": f"Referenced figure '{fig_ref_clean}' in {tf.name} does not exist on disk.",
                    }
                )
        parent_paths = re.findall(
            r"\\(?:includegraphics|input|include)(?:\[[^\]]*\])?\{(\.\./[^}]+)\}",
            raw,
        )
        if parent_paths and server == "arxiv":
            warnings.append(
                {
                    "code": "PARENT_RELATIVE_TEX_PATHS_NEED_FLAT_BUNDLE",
                    "location": tf.name,
                    "paths": parent_paths,
                    "detail": (
                        f"{tf.name} references parent-directory paths ({parent_paths[:3]}) and \\bibliography{{}}. "
                        "arXiv AutoTeX blocks '..' traversal and BibTeX runs; ensure your upload .tar.gz flattens "
                        "figure paths and inlines a compiled .bbl."
                    ),
                }
            )

    # 6. Bio / Clinical Ethics & medRxiv Clinical Safety Gates
    # Exclude explicit negation disclaimers like "no human participants, clinical trial cohorts, or live vertebrate animals"
    prose_without_negation = re.sub(
        r"no\s+human\s+(?:participants|subjects)[^.\n]*", "", norm, flags=re.I
    )
    mentions_human_animal = bool(
        re.search(
            r"\b(patients?|human\s+subjects?|clinical\s+cohort|biops(?:y|ies)|electronic\s+health\s+records?|"
            r"ehr|mice|murine|animal\s+model|xenograft|participants?)\b",
            prose_without_negation,
            re.I,
        )
    )
    has_ethics = bool(
        re.search(
            r"(institutional\s+review\s+board|\bIRB\b|ethics\s+committee|ethical\s+approval|ethics\s+statement|"
            r"\bIACUC\b|exempt\s+from\s+(?:irb|ethical)|de-identified\s+public(?:ly\s+available)?\s+(?:summary\s+)?data|"
            r"no\s+human\s+participants)",
            norm,
            re.I,
        )
    )

    if server == "medrxiv" or (server == "biorxiv" and mentions_human_animal):
        if not has_ethics:
            failures.append(
                {
                    "code": "MISSING_ETHICS_IRB_STATEMENT",
                    "detail": (
                        f"{server} screening requires an explicit IRB / Ethics Committee approval, waiver, "
                        "or non-human / public de-identified dataset statement."
                    ),
                }
            )

    if server == "medrxiv":
        mentions_trial = bool(
            re.search(
                r"\b(clinical\s+trial|randomized\s+controlled|randomised\s+controlled|phase\s+(?:i|ii|iii|1|2|3)\s+trial|"
                r"interventional\s+trial|placebo-controlled)\b",
                prose_without_negation,
                re.I,
            )
        )
        has_trial_id = bool(
            re.search(
                r"\b(NCT\d{8}|ISRCTN\d{8}|EudraCT\s*[:#]?\s*\d{4}-\d{6}-\d{2}|ACTRN\d{14}|ChiCTR\d+|UMIN\d+)\b",
                norm,
            )
        )
        if mentions_trial and not has_trial_id:
            failures.append(
                {
                    "code": "MEDRXIV_MISSING_TRIAL_REGISTRATION",
                    "detail": (
                        "medRxiv strictly requires a prospective clinical trial registration ID "
                        "(e.g., NCTxxxxxxxx, ISRCTN, EudraCT, WHO ICTRP) for interventional/clinical trial manuscripts."
                    ),
                }
            )

        if mentions_human_animal and not re.search(
            r"(informed\s+consent|de-identified|anonymi[sz]ed|summary[- ]level\s+statistics|no\s+human\s+participants)",
            norm,
            re.I,
        ):
            failures.append(
                {
                    "code": "MEDRXIV_MISSING_CONSENT_OR_DEIDENTIFICATION",
                    "detail": "medRxiv requires explicit confirmation of participant informed consent and/or patient de-identification.",
                }
            )

        rx_advice = re.search(
            r"\b(patients\s+should\s+(?:take|stop\s+taking)|clinicians\s+must\s+prescribe|"
            r"recommended\s+clinical\s+dosage\s+for\s+patients)\b",
            norm,
            re.I,
        )
        if rx_advice:
            failures.append(
                {
                    "code": "MEDRXIV_CLINICAL_TREATMENT_DIRECTIVE",
                    "detail": (
                        f"medRxiv prohibits unpeer-reviewed prescriptive clinical directives ('{rx_advice.group(1)}')."
                    ),
                }
            )

    return {
        "gate": "G4_SERVER_SCREENING",
        "server": server,
        "passed": len(failures) == 0,
        "failures": failures,
        "warnings": warnings,
    }


def evaluate_g5_claim_grounding(sources: dict, sections: dict) -> dict:
    failures: list[dict] = []
    warnings: list[dict] = []
    prose = sources["normalized_prose"]

    has_comp = bool(COMPUTATIONAL_MARKERS.search(prose))
    has_wetlab = bool(WETLAB_MARKERS.search(prose))
    purely_computational = has_comp and not has_wetlab

    high_visibility_text = "\n".join(
        [sections["title"], sections["abstract"], sections["conclusions"]]
    )

    if purely_computational:
        m_over = OVERSTATED_CLAIMS.search(high_visibility_text)
        if m_over:
            failures.append(
                {
                    "code": "UNHEDGED_COMPUTATIONAL_CLAIM",
                    "phrase": m_over.group(1),
                    "detail": (
                        f"Manuscript appears purely computational (no wet-lab assay markers detected), "
                        f"but Title/Abstract/Conclusions assert '{m_over.group(1)}'. Qualify predictions as "
                        "in silico / computational candidates requiring experimental validation."
                    ),
                }
            )
        if sections["abstract"] and not COMPUTATIONAL_HEDGING.search(sections["abstract"]):
            failures.append(
                {
                    "code": "ABSTRACT_MISSING_IN_SILICO_SCOPE",
                    "detail": (
                        "Purely computational study must explicitly state its computational / predictive / "
                        "in silico / simulation scope in the Abstract so preprint screeners do not flag overstated claims."
                    ),
                }
            )

    return {
        "gate": "G5_CLAIM_GROUNDING",
        "purely_computational": purely_computational,
        "passed": len(failures) == 0,
        "failures": failures,
        "warnings": warnings,
    }


def evaluate_g6_reverification_seal(
    gate_dir: Path,
    manifest: dict,
    mode: str,
    server: str,
    prior_gates_passed: bool,
) -> dict:
    gate_dir.mkdir(parents=True, exist_ok=True)
    pass1_path = gate_dir / "audit_pass1.json"
    blind_path = gate_dir / "blind_review.json"
    seal_path = gate_dir / "release_seal.json"

    current_sha = manifest["manuscript_sha256"]

    if mode == "audit":
        if seal_path.exists():
            seal_path.unlink()
        return {
            "gate": "G6_REVERIFICATION_SEAL",
            "mode": "audit",
            "passed": prior_gates_passed,
            "sealed": False,
            "gate_state_dir": str(gate_dir),
            "status": "PASS1_CLEAN_AWAITING_BLIND_REVIEW_AND_REVERIFY" if prior_gates_passed else "PASS1_BLOCKED",
            "failures": []
            if prior_gates_passed
            else [
                {
                    "code": "PASS1_GATES_FAILED",
                    "detail": "Remediate all Gate 1-5 failures before running blind review and Pass-2 re-verification.",
                }
            ],
            "warnings": [
                {
                    "code": "NOT_YET_SEALED",
                    "detail": (
                        "Pass-1 audit does NOT seal the manuscript. Invoke 'preprint-blind-auditor', record its "
                        "SHA-256 attestation via record_blind_review.py, then run gate_runner.py --mode reverify."
                    ),
                }
            ]
            if prior_gates_passed
            else [],
        }

    failures: list[dict] = []
    if not pass1_path.exists():
        failures.append(
            {
                "code": "MISSING_PASS1_AUDIT",
                "detail": "Cannot run '--mode reverify' before completing Pass-1 ('--mode audit').",
            }
        )

    if not prior_gates_passed:
        failures.append(
            {
                "code": "REVERIFY_SUBSTANTIVE_GATE_FAILURE",
                "detail": "One or more substantive hard gates (G1-G5) failed during Pass-2 re-verification.",
            }
        )

    blind_data: dict | None = None
    if not blind_path.exists():
        failures.append(
            {
                "code": "MISSING_BLIND_REVIEW_ATTESTATION",
                "detail": (
                    f"Missing {blind_path}. Run the isolated 'preprint-blind-auditor' "
                    "subagent and bind its output with record_blind_review.py before Pass-2 re-verification."
                ),
            }
        )
    else:
        blind_data = json.loads(blind_path.read_text(encoding="utf-8"))
        if blind_data.get("verdict") != "PASS" or (blind_data.get("blockers") or []):
            failures.append(
                {
                    "code": "BLIND_REVIEW_REJECTED",
                    "blockers": blind_data.get("blockers") or [],
                    "detail": "Blind auditor verdict is FAIL or has unresolved blockers.",
                }
            )
        if blind_data.get("target_server", "").lower() != server.lower():
            failures.append(
                {
                    "code": "BLIND_REVIEW_SERVER_MISMATCH",
                    "detail": (
                        f"Blind review was recorded for '{blind_data.get('target_server')}', "
                        f"but Pass-2 re-verification requested '{server}'."
                    ),
                }
            )
        if blind_data.get("manuscript_sha256") != current_sha:
            failures.append(
                {
                    "code": "STALE_BLIND_REVIEW_HASH_MISMATCH",
                    "blind_review_sha256": blind_data.get("manuscript_sha256"),
                    "current_manuscript_sha256": current_sha,
                    "detail": (
                        "HARD GATE DRIFT DETECTED: Manuscript files were modified after the blind review was "
                        "recorded. Re-run 'preprint-blind-auditor' + record_blind_review.py on the exact final files."
                    ),
                }
            )

    if failures:
        if seal_path.exists():
            seal_path.unlink()
        return {
            "gate": "G6_REVERIFICATION_SEAL",
            "mode": "reverify",
            "passed": False,
            "sealed": False,
            "gate_state_dir": str(gate_dir),
            "status": "HARD_GATE_BLOCKED",
            "failures": failures,
            "warnings": [],
        }

    pass1_data = json.loads(pass1_path.read_text(encoding="utf-8"))
    sealed_at = dt.datetime.now(dt.timezone.utc).isoformat()
    seal_material = f"{current_sha}|{server}|{blind_data['recorded_at']}|{sealed_at}"
    seal_id = hashlib.sha256(seal_material.encode("utf-8")).hexdigest()[:24]

    seal_payload = {
        "status": "SEALED_FOR_SUBMISSION",
        "reverified": True,
        "seal_id": seal_id,
        "target_server": server,
        "manuscript_dir": manifest["manuscript_dir"],
        "manuscript_file": manifest.get("manuscript_file"),
        "manuscript_sha256": current_sha,
        "files": manifest["files"],
        "pass1_audit_sha256": pass1_data.get("manuscript_sha256"),
        "blind_review_sha256": blind_data["manuscript_sha256"],
        "blind_review_recorded_at": blind_data["recorded_at"],
        "sealed_at": sealed_at,
    }
    seal_path.write_text(json.dumps(seal_payload, indent=2) + "\n", encoding="utf-8")

    return {
        "gate": "G6_REVERIFICATION_SEAL",
        "mode": "reverify",
        "passed": True,
        "sealed": True,
        "status": "SEALED_FOR_SUBMISSION",
        "seal_id": seal_id,
        "seal_path": str(seal_path),
        "failures": [],
        "warnings": [],
    }


def run_all_gates(
    manuscript_dir: Path,
    server: str,
    mode: str,
    manuscript_file: Path | None = None,
    state_dir: Path | None = None,
    antigravity_used: bool = True,
    program_member: bool = True,
    brand_approved: bool = False,
    citation_mode: str = "online",
    mock_registry: Path | None = None,
) -> dict:
    if manuscript_dir.is_file() and manuscript_file is None:
        manuscript_file = manuscript_dir
        manuscript_dir = manuscript_file.parent

    manifest = compute_manuscript_manifest(manuscript_dir, manuscript_file=manuscript_file)
    sources = _collect_manuscript_sources(manuscript_dir, manuscript_file=manuscript_file)
    sections = _extract_title_abstract_authors_conclusions(sources)

    g1 = evaluate_g1_ai_attribution(
        sources=sources,
        sections=sections,
        antigravity_used=antigravity_used,
        program_member=program_member,
        brand_approved=brand_approved,
    )
    g2 = evaluate_g2_skill_licenses(
        manuscript_dir=manuscript_dir,
        sources=sources,
        manuscript_file=manuscript_file,
    )
    g3 = evaluate_g3_citations(
        manuscript_dir=manuscript_dir,
        manuscript_file=manuscript_file,
        sources=sources,
        mode=mode,
        citation_mode=citation_mode,
        mock_registry=mock_registry,
    )
    g4 = evaluate_g4_server_screening(server=server, sources=sources, sections=sections)
    g5 = evaluate_g5_claim_grounding(sources=sources, sections=sections)

    substantive_gates = [g1, g2, g3, g4, g5]
    substantive_passed = all(g["passed"] for g in substantive_gates)

    gate_dir = resolve_default_gate_dir(
        manuscript_dir=manuscript_dir,
        manuscript_file=manuscript_file,
        state_dir=state_dir,
    )
    g6 = evaluate_g6_reverification_seal(
        gate_dir=gate_dir,
        manifest=manifest,
        mode=mode,
        server=server,
        prior_gates_passed=substantive_passed,
    )

    all_gates = [g1, g2, g3, g4, g5, g6]
    overall_passed = all(g["passed"] for g in all_gates)

    report = {
        "overall_passed": overall_passed,
        "sealed_for_submission": bool(g6.get("sealed")),
        "mode": mode,
        "target_server": server,
        "manuscript_dir": str(manuscript_dir),
        "manuscript_file": str(manuscript_file.resolve()) if manuscript_file else None,
        "gate_state_dir": str(gate_dir),
        "manuscript_sha256": manifest["manuscript_sha256"],
        "file_count": manifest["file_count"],
        "tracked_files": manifest["files"],
        "evaluated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "gates": {g["gate"]: g for g in all_gates},
    }

    gate_dir.mkdir(parents=True, exist_ok=True)
    if mode == "audit":
        (gate_dir / "audit_pass1.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    else:
        (gate_dir / "reverify_pass2.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Google Antigravity for Science 6-Gate Preprint Compliance & Re-Verification."
    )
    parser.add_argument("--manuscript-dir", type=Path, default=None, help="Manuscript directory.")
    parser.add_argument(
        "--manuscript-file",
        type=Path,
        default=None,
        help="Optional single .tex or .md manuscript file (scopes hashing and .bib checks to that paper).",
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=None,
        help="Optional custom directory for .preprint_gate state files.",
    )
    parser.add_argument(
        "--server",
        required=True,
        choices=SUPPORTED_SERVERS,
        help="Target preprint server screening profile.",
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["audit", "reverify"],
        help="'audit' for Pass 1 discovery; 'reverify' for Pass 2 cryptographic hard gate.",
    )
    parser.add_argument(
        "--antigravity-used",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Require Google Antigravity + Gemini disclosure (default: true).",
    )
    parser.add_argument(
        "--program-member",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Require Google Antigravity/AI for Science program acknowledgment (default: true).",
    )
    parser.add_argument(
        "--brand-approved",
        action="store_true",
        default=False,
        help="Pass only if written Google/DeepMind brand logo authorization was obtained.",
    )
    parser.add_argument(
        "--citation-mode",
        choices=["online", "mock", "syntax-only"],
        default="online",
        help="Citation verification backend (syntax-only is blocked in --mode reverify).",
    )
    parser.add_argument("--mock-registry", type=Path, default=None, help="Mock citation registry JSON path.")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON report output path.")
    args = parser.parse_args()

    if not args.manuscript_dir and not args.manuscript_file:
        parser.error("Provide --manuscript-dir and/or --manuscript-file.")

    mfile = args.manuscript_file.resolve() if args.manuscript_file else None
    mdir = args.manuscript_dir.resolve() if args.manuscript_dir else mfile.parent

    report = run_all_gates(
        manuscript_dir=mdir,
        manuscript_file=mfile,
        state_dir=args.state_dir.resolve() if args.state_dir else None,
        server=args.server,
        mode=args.mode,
        antigravity_used=args.antigravity_used,
        program_member=args.program_member,
        brand_approved=args.brand_approved,
        citation_mode=args.citation_mode,
        mock_registry=args.mock_registry.resolve() if args.mock_registry else None,
    )

    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["overall_passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
