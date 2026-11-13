---
name: preprint-readiness-gate
description: >-
  Audits, remediates, re-verifies, and cryptographically seals scientific preprints
  (arXiv, bioRxiv, medRxiv, ChemRxiv) for Google Antigravity for Science researchers.
  Enforces 6 hard gates—including zero AI authorship, AI/program attribution,
  Google DeepMind Science Plugin SKILL_LICENSES database citations, live citation
  title-match verification, clinical/IRB safety checks, in-silico claim framing,
  and a post-remediation SHA-256 blind-review hard gate before submission packaging.
  Activate whenever the user prepares, reviews, validates, checks compliance of,
  or packages a scientific manuscript or preprint.
metadata:
  version: "1.0.0"
---

# Scientific Preprint Readiness & Two-Pass Hard Gate

This skill enforces a **mandatory two-pass verification workflow with cryptographic SHA-256 hard gates** before any preprint can be certified or packaged for submission to `arxiv`, `biorxiv`, `medrxiv`, or `chemrxiv`.

## Hard-Gate Architecture (Why Two Passes?)

Fixes applied after an initial audit frequently introduce secondary regressions (broken `.bib` keys, missing database citations, or drifted claims). Therefore, **Pass-1 (`audit`) can NEVER seal a manuscript**. Sealing requires:

1. **Pass 1 (`--mode audit`)**: Deterministic check of Gates `G1`–`G5` to surface all defects.
2. **Remediation**: Fix all reported defects in `.tex` / `.md` / `.bib` (using templates in [resources/attribution_snippets.md](resources/attribution_snippets.md)).
3. **Fresh-Eyes Blind Review (`preprint-blind-auditor`)**: Spawn the isolated read-only subagent with zero conversation context, then bind its `PASS` JSON output to the exact current `manuscript_sha256` using [scripts/record_blind_review.py](scripts/record_blind_review.py).
4. **Pass 2 (`--mode reverify` — HARD GATE)**: Re-runs Gates `G1`–`G5` from scratch (live citation lookup required; `syntax-only` is blocked) **and** verifies `blind_review.manuscript_sha256 == live_manuscript_sha256`. Any 1-byte edit after blind review triggers `STALE_BLIND_REVIEW_HASH_MISMATCH` (exit code `2`).
5. **Sealed Packaging ([scripts/package_submission.py](scripts/package_submission.py))**: Verifies `.preprint_gate/release_seal.json` + live SHA-256 match before emitting `SUBMISSION_COMPLIANCE_CERTIFICATE.md` and `.tar.gz`.

---

## Step-by-Step Execution Protocol

### Step 1: Run Pass-1 Audit (`--mode audit`)

Identify the manuscript directory (`<MANUSCRIPT_DIR>`) and target server (`arxiv`, `biorxiv`, `medrxiv`, or `chemrxiv`). Run:

```bash
# Directory mode (single-paper folder) OR --manuscript-file for a specific .tex/.md in a multi-paper folder:
python3 skills/preprint-readiness-gate/scripts/gate_runner.py \
  --manuscript-file "<PATH_TO_MANUSCRIPT.tex>" \
  --server arxiv \
  --mode audit \
  --output /tmp/preprint_pass1.json
```

> **Sandbox Note**: Live citation checks (`--citation-mode online`, the default) query Crossref, PubMed E-utilities, and arXiv over HTTPS. Attempt sandboxed first; if network access is blocked in the sandbox, re-run with `BypassSandbox: true` so live DOI/PMID/arXiv resolution succeeds.

### Step 2: Remediate All `G1`–`G5` Failures

Consult the reference guides only as needed:
- **AI & Science Program Attribution (`G1` / `G2`)**: [references/google_science_attribution.md](references/google_science_attribution.md) and [resources/attribution_snippets.md](resources/attribution_snippets.md)
- **Database Citation Registry (`G2`)**: [references/skill_license_registry.json](references/skill_license_registry.json)
- **Server Screening & Clinical Rules (`G4` / `G5`)**: [references/server_screening_matrices.md](references/server_screening_matrices.md)

Re-run `--mode audit` after edits until `G1`–`G5` report zero `failures`. **Stop editing manuscript files once Pass-1 is clean**—any subsequent byte modification will invalidate the blind review hash!

### Step 3: Isolated Blind Subagent Audit & Hash Binding

1. Invoke the `preprint-blind-auditor` subagent via `invoke_subagent` (`TypeName: "preprint-blind-auditor"`, `Role: "Blind Preprint Screening Auditor"`), passing `<MANUSCRIPT_DIR>` and `--server <SERVER>`.
2. Save its fenced JSON response to `/tmp/blind_review_output.json` and bind it to the live manuscript SHA-256:

```bash
python3 skills/preprint-readiness-gate/scripts/record_blind_review.py \
  --manuscript-dir "<MANUSCRIPT_DIR>" \
  --server biorxiv \
  --review-file /tmp/blind_review_output.json
```

If `record_blind_review.py` exits `2` (`verdict == "FAIL"` or non-empty `blockers`), fix the blockers, re-run Step 1 (`--mode audit`), and repeat Step 3 with a fresh blind audit.

### Step 4: Run Pass-2 Re-Verification Hard Gate (`--mode reverify`)

```bash
python3 skills/preprint-readiness-gate/scripts/gate_runner.py \
  --manuscript-dir "<MANUSCRIPT_DIR>" \
  --server biorxiv \
  --mode reverify \
  --output /tmp/preprint_pass2_seal.json
```

- **Exit code `0`**: `.preprint_gate/release_seal.json` is written with `status: "SEALED_FOR_SUBMISSION"`.
- **Exit code `2`**: **HARD GATE BLOCKED**. Do NOT claim readiness or package files; inspect `gates.G6_REVERIFICATION_SEAL.failures` (e.g., `STALE_BLIND_REVIEW_HASH_MISMATCH`) and repeat from the required step.

### Step 5: Package Sealed Submission Bundle (Optional)

Only after Step 4 exits `0`:

```bash
python3 skills/preprint-readiness-gate/scripts/package_submission.py \
  --manuscript-dir "<MANUSCRIPT_DIR>" \
  --server biorxiv \
  --output "<MANUSCRIPT_DIR>_biorxiv_sealed.tar.gz"
```

This generates `SUBMISSION_COMPLIANCE_CERTIFICATE.md` and a clean portable `.tar.gz` submission archive.
