#!/usr/bin/env python3
# Copyright 2026 Wayne A. Satz, MD & Contributors
# Licensed under the Apache License, Version 2.0.

"""Verifies BibTeX/.bbl and inline manuscript citations against Crossref, DataCite, OpenAlex, PubMed, and arXiv."""

# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

USER_AGENT = "RxivGate/1.1 (https://github.com/deesatzed/rxiv-gate; mailto:satzwa@temple.edu)"

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "using",
    "via", "under", "over", "between", "study", "analysis", "novel", "new",
    "of", "in", "on", "to", "a", "an", "by", "at", "as", "is", "are",
}

AUTHOR_STOPWORDS = {
    "and", "others", "et", "al", "the", "for", "group", "consortium",
    "investigators", "writing", "committee", "collaboration", "study",
}


def _normalize_tokens(text: str) -> set[str]:
    cleaned = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
    cleaned = re.sub(r"[{}\\\"'`~^$]", "", cleaned.lower())
    words = re.findall(r"[a-z0-9]{3,}", cleaned)
    return {w for w in words if w not in STOPWORDS}


def _normalize_author_tokens(author_str: str) -> set[str]:
    cleaned = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", author_str)
    cleaned = re.sub(r"[{}\\\"'`~^$.]", " ", cleaned.lower())
    words = re.findall(r"[a-z]{3,}", cleaned)
    return {w for w in words if w not in AUTHOR_STOPWORDS}


def title_similarity(title_a: str, title_b: str) -> float:
    """Computes asymmetric containment + Jaccard blend to tolerate subtitle truncation."""
    toks_a = _normalize_tokens(title_a)
    toks_b = _normalize_tokens(title_b)
    if not toks_a or not toks_b:
        return 0.0
    inter = len(toks_a & toks_b)
    union = len(toks_a | toks_b)
    smaller = min(len(toks_a), len(toks_b))
    jaccard = inter / union
    containment = inter / smaller
    return round(0.5 * jaccard + 0.5 * containment, 4)


def authors_overlap(bib_author: str, canonical_authors: list[str]) -> bool:
    """Returns True if at least one surname/token matches or if canonical authors are unavailable."""
    if not canonical_authors:
        return True
    # Consortium / institutional author blocks in .bib
    if re.search(r"\b(consortium|investigators|group|research|synaptics|collaborat)\b", bib_author, re.I):
        return True
    bib_toks = _normalize_author_tokens(bib_author)
    reg_toks = _normalize_author_tokens(" ".join(canonical_authors))
    if not bib_toks or not reg_toks:
        return True
    return len(bib_toks & reg_toks) > 0


def _parse_bibtex_fields(body: str) -> dict[str, str]:
    """Parses BibTeX key=value fields supporting arbitrary nested brace depth."""
    fields: dict[str, str] = {}
    n = len(body)
    i = 0
    while i < n:
        while i < n and body[i] in " \t\r\n,":
            i += 1
        if i >= n:
            break
        m_key = re.match(r"([a-zA-Z0-9_:-]+)\s*=\s*", body[i:])
        if not m_key:
            nxt = body.find(",", i)
            i = (nxt + 1) if nxt != -1 else n
            continue
        fname = m_key.group(1).lower()
        i += m_key.end()
        if i >= n:
            break
        if body[i] == "{":
            depth = 1
            i += 1
            start = i
            while i < n and depth > 0:
                if body[i] == "{":
                    depth += 1
                elif body[i] == "}":
                    depth -= 1
                i += 1
            raw_val = body[start : max(start, i - 1)]
        elif body[i] == '"':
            i += 1
            start = i
            while i < n and not (body[i] == '"' and body[i - 1] != "\\"):
                i += 1
            raw_val = body[start:i]
            i += 1
        else:
            start = i
            while i < n and body[i] not in ",\r\n}":
                i += 1
            raw_val = body[start:i]
        fields[fname] = re.sub(r"\s+", " ", raw_val).strip()
    return fields


def parse_bibtex_file(bib_path: Path) -> tuple[list[dict], list[dict]]:
    """Parses BibTeX entries and detects duplicate keys."""
    content = bib_path.read_text(encoding="utf-8", errors="replace")
    entries: list[dict] = []
    duplicate_errors: list[dict] = []
    seen_keys: set[str] = set()

    pattern = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.IGNORECASE)
    pos = 0
    while True:
        match = pattern.search(content, pos)
        if not match:
            break
        entry_type = match.group(1).lower()
        if entry_type in ("comment", "preamble", "string"):
            pos = match.end()
            continue
        cite_key = match.group(2).strip()
        if cite_key in seen_keys:
            duplicate_errors.append(
                {
                    "code": "DUPLICATE_BIB_KEY",
                    "key": cite_key,
                    "location": bib_path.name,
                    "detail": f"Duplicate BibTeX key '{cite_key}' in {bib_path.name}.",
                }
            )
        seen_keys.add(cite_key)

        idx = match.end()
        depth = 1
        while idx < len(content) and depth > 0:
            if content[idx] == "{":
                depth += 1
            elif content[idx] == "}":
                depth -= 1
            idx += 1
        body = content[match.end() : max(match.end(), idx - 1)]
        pos = idx

        fields = _parse_bibtex_fields(body)
        doi = fields.get("doi", "").strip()
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
        arxiv_id = fields.get("eprint", "") or fields.get("arxivid", "")
        if not arxiv_id and "arxiv:" in fields.get("journal", "").lower():
            m_arx = re.search(r"arxiv:(\d{4}\.\d{4,5}(?:v\d+)?)", fields.get("journal", ""), re.I)
            if m_arx:
                arxiv_id = m_arx.group(1)
        pmid = fields.get("pmid", "").strip()

        entries.append(
            {
                "source_file": bib_path.name,
                "entry_type": entry_type,
                "key": cite_key,
                "title": fields.get("title", ""),
                "author": fields.get("author", ""),
                "year": fields.get("year", ""),
                "doi": doi,
                "pmid": pmid,
                "arxiv_id": arxiv_id,
            }
        )
    return entries, duplicate_errors


def extract_cited_keys_from_text(manuscript_files: list[Path]) -> tuple[set[str], list[dict]]:
    r"""Extracts cited keys (\cite{...} and [@key]) and empty/broken citation commands."""
    cited_keys: set[str] = set()
    syntax_errors: list[dict] = []

    tex_cite_pat = re.compile(r"\\cite[a-zA-Z*]*\s*(?:\[[^\]]*\]\s*)*\{([^}]*)\}")
    md_cite_pat = re.compile(r"\[((?:@[a-zA-Z0-9_.:-]+(?:\s*;\s*)?)+)\]")

    for fpath in manuscript_files:
        text = fpath.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = re.sub(r"(?<!\\)%.*$", "", line) if fpath.suffix.lower() == ".tex" else line
            for m in tex_cite_pat.finditer(stripped):
                raw = m.group(1).strip()
                if not raw:
                    syntax_errors.append(
                        {
                            "code": "EMPTY_CITE_COMMAND",
                            "location": f"{fpath.name}:L{line_no}",
                            "detail": "Empty \\cite{} command found.",
                        }
                    )
                    continue
                for key in raw.split(","):
                    k = key.strip()
                    if k in ("?", "TODO", "TBD"):
                        syntax_errors.append(
                            {
                                "code": "PLACEHOLDER_CITE_KEY",
                                "location": f"{fpath.name}:L{line_no}",
                                "detail": f"Placeholder citation key '{k}'.",
                            }
                        )
                    elif k:
                        cited_keys.add(k)

            if fpath.suffix.lower() in (".md", ".rmd", ".qmd"):
                for m in md_cite_pat.finditer(stripped):
                    for part in m.group(1).split(";"):
                        k = part.strip().lstrip("@").strip()
                        if k:
                            cited_keys.add(k)

    return cited_keys, syntax_errors


def _http_get_with_retries(url: str, accept: str = "application/json", timeout: float = 10.0, max_retries: int = 3) -> bytes:
    """Executes HTTP GET with exponential backoff on rate limits (429) or transient 5xx errors."""
    delay = 0.4
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2.0
                last_exc = exc
                continue
            raise
        except Exception as exc:  # pylint: disable=broad-except
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2.0
                last_exc = exc
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("Unreachable HTTP retry state")


def _http_get_json(url: str, timeout: float = 10.0) -> dict | None:
    raw = _http_get_with_retries(url, accept="application/json", timeout=timeout)
    return json.loads(raw.decode("utf-8", errors="replace"))


def _lookup_datacite_doi(doi: str) -> dict:
    """Fallback lookup for DataCite DOIs (Zenodo 10.5281, arXiv 10.48550, RCSB PDB 10.2210, Figshare)."""
    encoded = urllib.parse.quote(doi, safe="")
    url = f"https://api.datacite.org/dois/{encoded}"
    try:
        data = _http_get_json(url)
        attrs = ((data or {}).get("data") or {}).get("attributes") or {}
        titles = attrs.get("titles") or []
        canonical_title = (titles[0].get("title") or "") if titles else ""
        creators = attrs.get("creators") or []
        authors = [
            (c.get("name") or f"{c.get('familyName', '')} {c.get('givenName', '')}").strip()
            for c in creators
        ]
        return {
            "resolved": bool(canonical_title),
            "source": "datacite",
            "canonical_title": canonical_title,
            "authors": authors,
        }
    except urllib.error.HTTPError as exc:
        return {"resolved": False, "source": "datacite", "error": f"HTTP {exc.code}"}
    except Exception as exc:  # pylint: disable=broad-except
        return {"resolved": False, "source": "datacite", "error": str(exc)}


def _lookup_doi_online(doi: str) -> dict:
    # Route 10.48550/arXiv.* directly to arXiv API or DataCite
    m_arx_doi = re.match(r"^10\.48550/arxiv\.(.+)$", doi.strip(), re.I)
    if m_arx_doi:
        res = _lookup_arxiv_online(m_arx_doi.group(1))
        if res.get("resolved"):
            return res

    encoded = urllib.parse.quote(doi, safe="")
    url = f"https://api.crossref.org/works/{encoded}"
    try:
        data = _http_get_json(url)
        msg = (data or {}).get("message", {})
        titles = msg.get("title") or []
        canonical_title = titles[0] if titles else ""
        authors = [
            (a.get("name") or f"{a.get('family', '')} {a.get('given', '')}").strip()
            for a in (msg.get("author") or [])
        ]
        if canonical_title:
            return {
                "resolved": True,
                "source": "crossref",
                "canonical_title": canonical_title,
                "authors": authors,
            }
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            # Try DataCite fallback (Zenodo, PDB, Figshare, arXiv DataCite DOIs)
            dc = _lookup_datacite_doi(doi)
            if dc.get("resolved"):
                return dc
        return {"resolved": False, "source": "crossref", "error": f"HTTP {exc.code}"}
    except Exception as exc:  # pylint: disable=broad-except
        return {"resolved": False, "source": "crossref", "error": str(exc)}

    return _lookup_datacite_doi(doi)


def _lookup_pmid_online(pmid: str) -> dict:
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?"
        f"db=pubmed&id={urllib.parse.quote(pmid)}&retmode=json"
    )
    try:
        data = _http_get_json(url)
        rec = ((data or {}).get("result") or {}).get(str(pmid)) or {}
        if "error" in rec or not rec.get("title"):
            return {"resolved": False, "source": "pubmed", "error": rec.get("error", "PMID not found")}
        authors = [a.get("name", "") for a in (rec.get("authors") or [])]
        return {
            "resolved": True,
            "source": "pubmed",
            "canonical_title": rec.get("title", ""),
            "authors": authors,
        }
    except Exception as exc:  # pylint: disable=broad-except
        return {"resolved": False, "source": "pubmed", "error": str(exc)}


def _lookup_arxiv_online(arxiv_id: str) -> dict:
    clean_id = re.sub(r"^arxiv:", "", arxiv_id.strip(), flags=re.I)
    url = f"https://export.arxiv.org/api/query?id_list={urllib.parse.quote(clean_id)}"
    try:
        xml_bytes = _http_get_with_retries(url, accept="application/atom+xml", timeout=10.0)
        root = ET.fromstring(xml_bytes)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.find("atom:entry", ns)
        if entry is None:
            return {"resolved": False, "source": "arxiv", "error": "No arXiv entry returned"}
        title_el = entry.find("atom:title", ns)
        canonical_title = re.sub(r"\s+", " ", (title_el.text or "").strip()) if title_el is not None else ""
        if not canonical_title or canonical_title.lower() == "error":
            return {"resolved": False, "source": "arxiv", "error": "Invalid arXiv ID"}
        authors = [
            (a.findtext("atom:name", default="", namespaces=ns) or "").strip()
            for a in entry.findall("atom:author", ns)
        ]
        return {
            "resolved": True,
            "source": "arxiv",
            "canonical_title": canonical_title,
            "authors": authors,
        }
    except Exception as exc:  # pylint: disable=broad-except
        return {"resolved": False, "source": "arxiv", "error": str(exc)}


def verify_manuscript_citations(
    manuscript_dir: Path,
    manuscript_file: Path | None = None,
    mode: str = "online",
    mock_registry_path: Path | None = None,
    min_title_similarity: float = 0.45,
) -> dict:
    """Runs citation integrity verification across .bib and manuscript files."""
    if manuscript_file is not None:
        mfile = manuscript_file.resolve()
        text_files = [mfile]
        bib_files = sorted(mfile.parent.glob("*.bib"))
        only_cited = True
    else:
        bib_files = sorted(manuscript_dir.rglob("*.bib"))
        text_files = sorted(
            p
            for p in manuscript_dir.rglob("*")
            if p.is_file()
            and p.suffix.lower() in (".tex", ".md", ".qmd", ".rmd")
            and ".preprint_gate" not in p.parts
            and p.name not in ("SUBMISSION_COMPLIANCE_CERTIFICATE.md", "README.md")
            and not p.name.startswith("README_")
        )
        only_cited = False

    entries: list[dict] = []
    duplicate_errors: list[dict] = []
    for bf in bib_files:
        parsed_entries, dup_errs = parse_bibtex_file(bf)
        entries.extend(parsed_entries)
        duplicate_errors.extend(dup_errs)

    entries_by_key = {e["key"]: e for e in entries}
    cited_keys, syntax_errors = extract_cited_keys_from_text(text_files)

    failures: list[dict] = list(syntax_errors) + list(duplicate_errors)
    warnings: list[dict] = []
    verified_records: list[dict] = []

    for ck in sorted(cited_keys):
        if ck not in entries_by_key:
            failures.append(
                {
                    "code": "MISSING_BIB_ENTRY",
                    "key": ck,
                    "detail": f"Citation key '{ck}' is cited in manuscript text but missing from all .bib files.",
                }
            )

    target_entries = (
        [entries_by_key[k] for k in sorted(cited_keys) if k in entries_by_key]
        if only_cited
        else entries
    )

    mock_db: dict = {}
    if mode == "mock":
        if not mock_registry_path or not mock_registry_path.exists():
            failures.append(
                {
                    "code": "MOCK_REGISTRY_MISSING",
                    "detail": f"Citation mode 'mock' requires a valid --mock-registry file (got {mock_registry_path}).",
                }
            )
        else:
            mock_db = json.loads(mock_registry_path.read_text(encoding="utf-8"))

    for entry in target_entries:
        key = entry["key"]
        if not entry["title"] or not entry["author"] or not entry["year"]:
            failures.append(
                {
                    "code": "INCOMPLETE_BIB_FIELDS",
                    "key": key,
                    "detail": f"BibTeX entry '{key}' is missing required title, author, or year.",
                }
            )
            continue

        has_identifier = bool(entry["doi"] or entry["pmid"] or entry["arxiv_id"])
        if not has_identifier:
            if entry["entry_type"] == "article":
                failures.append(
                    {
                        "code": "ARTICLE_MISSING_IDENTIFIER",
                        "key": key,
                        "detail": (
                            f"Journal/preprint @article '{key}' ('{entry['title'][:60]}') lacks a verifiable "
                            "DOI, PMID, or arXiv eprint identifier."
                        ),
                    }
                )
            else:
                warnings.append(
                    {
                        "code": "NON_ARTICLE_NO_DOI",
                        "key": key,
                        "detail": f"Entry '{key}' (@{entry['entry_type']}) has no DOI/PMID/arXiv ID; verify URL/report manually.",
                    }
                )
            continue

        if mode == "syntax-only":
            verified_records.append({"key": key, "status": "SYNTAX_OK_UNVERIFIED_ONLINE"})
            continue

        lookup: dict | None = None
        if mode == "mock":
            dois_map = {k.lower(): v for k, v in (mock_db.get("dois") or {}).items()}
            pmids_map = {str(k): v for k, v in (mock_db.get("pmids") or {}).items()}
            arxiv_map = {k.lower(): v for k, v in (mock_db.get("arxiv") or {}).items()}
            if entry["doi"]:
                rec = dois_map.get(entry["doi"].lower())
                lookup = (
                    {"resolved": True, "source": "mock:doi", "canonical_title": rec["title"], "authors": rec.get("authors", [])}
                    if rec
                    else {"resolved": False, "source": "mock:doi", "error": "DOI not found in registry"}
                )
            elif entry["pmid"]:
                rec = pmids_map.get(str(entry["pmid"]))
                lookup = (
                    {"resolved": True, "source": "mock:pmid", "canonical_title": rec["title"], "authors": rec.get("authors", [])}
                    if rec
                    else {"resolved": False, "source": "mock:pmid", "error": "PMID not found in registry"}
                )
            elif entry["arxiv_id"]:
                clean_id = re.sub(r"^arxiv:", "", entry["arxiv_id"], flags=re.I).lower()
                rec = arxiv_map.get(clean_id)
                lookup = (
                    {"resolved": True, "source": "mock:arxiv", "canonical_title": rec["title"], "authors": rec.get("authors", [])}
                    if rec
                    else {"resolved": False, "source": "mock:arxiv", "error": "arXiv ID not found in registry"}
                )
        elif mode == "online":
            if entry["doi"]:
                lookup = _lookup_doi_online(entry["doi"])
                time.sleep(0.12)
            elif entry["pmid"]:
                lookup = _lookup_pmid_online(entry["pmid"])
                time.sleep(0.34)
            elif entry["arxiv_id"]:
                lookup = _lookup_arxiv_online(entry["arxiv_id"])
                time.sleep(0.5)

        if not lookup or not lookup.get("resolved"):
            err = (lookup or {}).get("error", "Unresolved identifier")
            failures.append(
                {
                    "code": "UNRESOLVED_CITATION_IDENTIFIER",
                    "key": key,
                    "identifier": entry["doi"] or entry["pmid"] or entry["arxiv_id"],
                    "detail": f"Entry '{key}' failed live identifier resolution ({err}). Possible hallucinated or mistyped ID.",
                }
            )
            continue

        sim = title_similarity(entry["title"], lookup["canonical_title"])
        if sim < min_title_similarity:
            failures.append(
                {
                    "code": "CITATION_TITLE_MISMATCH",
                    "key": key,
                    "identifier": entry["doi"] or entry["pmid"] or entry["arxiv_id"],
                    "similarity": sim,
                    "manuscript_title": entry["title"],
                    "canonical_title": lookup["canonical_title"],
                    "detail": (
                        f"Entry '{key}' resolved via {lookup['source']}, but title similarity ({sim}) is below "
                        f"hard threshold ({min_title_similarity}). Manuscript has '{entry['title']}' vs "
                        f"canonical '{lookup['canonical_title']}'."
                    ),
                }
            )
            continue

        if not authors_overlap(entry["author"], lookup.get("authors") or []):
            failures.append(
                {
                    "code": "CITATION_AUTHOR_MISMATCH",
                    "key": key,
                    "identifier": entry["doi"] or entry["pmid"] or entry["arxiv_id"],
                    "manuscript_author": entry["author"],
                    "canonical_authors": (lookup.get("authors") or [])[:5],
                    "detail": (
                        f"Entry '{key}' title matched via {lookup['source']}, but zero author surnames overlap "
                        f"between manuscript ('{entry['author']}') and registry ({(lookup.get('authors') or [])[:3]})."
                    ),
                }
            )
            continue

        verified_records.append(
            {
                "key": key,
                "source": lookup["source"],
                "similarity": sim,
                "canonical_title": lookup["canonical_title"],
            }
        )

    return {
        "passed": len(failures) == 0,
        "mode": mode,
        "scoped_to_file": str(manuscript_file) if manuscript_file else None,
        "bib_entry_count": len(target_entries),
        "total_bib_pool_count": len(entries),
        "cited_key_count": len(cited_keys),
        "verified_count": len(verified_records),
        "failures": failures,
        "warnings": warnings,
        "verified_records": verified_records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify manuscript citations against authoritative registries.")
    parser.add_argument("--manuscript-dir", type=Path, default=None, help="Path to manuscript folder.")
    parser.add_argument("--manuscript-file", type=Path, default=None, help="Path to single .tex/.md manuscript file.")
    parser.add_argument(
        "--mode",
        choices=["online", "mock", "syntax-only"],
        default="online",
        help="Verification mode (default: online; Note: Pass-2 reverify forbids syntax-only).",
    )
    parser.add_argument("--mock-registry", type=Path, default=None, help="Mock JSON registry for offline testing.")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path.")
    args = parser.parse_args()

    if not args.manuscript_dir and not args.manuscript_file:
        parser.error("Provide either --manuscript-dir or --manuscript-file.")

    mfile = args.manuscript_file.resolve() if args.manuscript_file else None
    mdir = args.manuscript_dir.resolve() if args.manuscript_dir else mfile.parent

    result = verify_manuscript_citations(
        manuscript_dir=mdir,
        manuscript_file=mfile,
        mode=args.mode,
        mock_registry_path=args.mock_registry.resolve() if args.mock_registry else None,
    )
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
