<div align="center">

<img src="assets/hero-banner.svg" alt="rxiv-gate — Cryptographic Two-Pass Preprint Readiness & Citation Gate for Google Antigravity" width="100%" />

<br />

[![Version](https://img.shields.io/badge/version-1.1.0-10B981?style=flat-square)](https://github.com/deesatzed/rxiv-gate)
[![Python](https://img.shields.io/badge/python-3.10%2B%20(zero%20deps)-38BDF8?style=flat-square)](https://github.com/deesatzed/rxiv-gate)
[![Servers](https://img.shields.io/badge/servers-arXiv%20%7C%20bioRxiv%20%7C%20medRxiv%20%7C%20ChemRxiv-A78BFA?style=flat-square)](https://github.com/deesatzed/rxiv-gate)
[![License](https://img.shields.io/badge/license-Apache--2.0-F59E0B?style=flat-square)](LICENSE)

**Two-pass scientific preprint compliance, live citation verification, and SHA-256 cryptographic hard gates for [Google Antigravity](https://antigravity.google).**

[Why `rxiv-gate`](#why-rxiv-gate-exists) · [Live Screenshots](#see-rxiv-gate-in-action) · [The 6 Hard Gates](#the-6-hard-gates) · [30-Second Install](#installation) · [CLI Usage](#cli-usage-single-file-or-directory-mode) · [Social Media Kit](docs/SOCIAL_MEDIA_KIT.md)

</div>

---

## Why `rxiv-gate` Exists

Built for researchers in the **10,000-member Google Antigravity for Science** cohort and the broader scientific community, `rxiv-gate` prevents the subtle failure modes that standard TeX linters and HTTP-200 link checkers miss before submitting to **arXiv**, **bioRxiv**, **medRxiv**, or **ChemRxiv**:

1. **Real-DOI / Wrong-Paper Citation Conflations**: A `.bib` entry whose DOI resolves (`HTTP 200`) to a completely unrelated article—or a "chimeric" reference combining a real title and DOI with mismatched authors.
2. **Unattributed Science Plugin Databases**: Missing bibliography citations required by third-party databases queried through the Google DeepMind Science Plugin (`SKILL_LICENSES.md`).
3. **Undisclosed AI Workflows or Prohibited AI Authorship**: Missing *Methods* disclosures, missing human-verification attestations, or accidental AI co-authorship (prohibited by ICMJE, COPE, arXiv, bioRxiv, and medRxiv).
4. **Overstated *In Silico* Claims & Clinical Screening Blockers**: Purely computational predictions phrased as wet-lab/clinical validation, or missing IRB / `NCT` clinical trial IDs on `medRxiv`.
5. **Post-Review Edit Drift**: Last-minute `.tex` or `.bib` edits made *after* an audit or review has already passed.

`rxiv-gate` enforces **6 deterministic Hard Gates**, an isolated fresh-context **Blind Auditor Subagent** (`preprint-blind-auditor`), a **Two-Pass Merkle SHA-256 Release Seal**, and an Antigravity **`PreToolUse` Runtime Hook** that physically blocks submission packaging if any gate fails or if even **1 byte** changes after re-verification.

---

## See `rxiv-gate` in Action

### Pass 1 (`--mode audit`): Catching a Real-World Crossref DOI Conflation & Blocking Unsealed Packaging

During our first live evaluation of a 55-reference arXiv manuscript, standard DOI link checkers reported `HTTP 200 OK` on every reference—but `rxiv-gate`'s **Gate G3 (`CITATION_TITLE_MISMATCH`)** caught that `degrandi2015fungicides` (`DOI: 10.1016/j.jinsphys.2015.06.004`) actually resolved on Crossref to an unrelated silkworm *Bombyx Wnt1* CRISPR study (`token similarity = 0.00`), allowing immediate replacement with the authentic *Journal of Economic Entomology* DOI (`10.1093/jee/tov251`):

<p align="center">
  <img src="assets/screenshot-pass1-catch.svg" alt="Pass 1 Audit catching a live Crossref title mismatch and blocking unsealed tar packaging" width="100%" />
</p>

### Pass 2 (`--mode reverify`): Isolated Blind Review Binding & Cryptographic SHA-256 Release Seal

After remediation, the zero-context `preprint-blind-auditor` subagent inspects the manuscript and binds its verdict to the live composite Merkle `manuscript_sha256` digest. Only when Pass-2 re-verification confirms `0` blockers and `0` bytes of post-review drift does `rxiv-gate` issue `.preprint_gate/<stem>/release_seal.json` and unlock `package_submission.py`:

<p align="center">
  <img src="assets/screenshot-pass2-sealed.svg" alt="Pass 2 Re-verification issuing SHA-256 release seal and compliance certificate" width="100%" />
</p>

---

## The 6 Hard Gates

| Gate ID | What It Enforces | Failure Action |
| :--- | :--- | :--- |
| **`G1_AI_ATTRIBUTION`** | Blocks AI models/agents in the Author list (ICMJE/COPE); verifies *Methods* AI disclosure (`Google Antigravity` + `Gemini` model + explicit human verification/responsibility attestation); verifies *Google Antigravity for Science* program acknowledgment; blocks unauthorized Google/DeepMind logos. | **HARD BLOCK** (`exit 2`) |
| **`G2_SKILL_LICENSES`** | Scans manuscript prose, code scripts, and `.licenses/` against 34 scientific databases/tools across all 41 Google DeepMind Science Plugin skills (AlphaFold DB, AlphaGenome, Boltz, ChEMBL, PubChem, gnomAD, GTEx, UniProt, Reactome, RCSB PDB, RDKit, OpenMM, AutoDock Vina, etc.) and ensures each detected source is formally cited. | **HARD BLOCK** (`exit 2`) |
| **`G3_CITATIONS`** | Parses `.bib` (arbitrary nested brace depth), `\cite{}`, and Markdown `[@key]` citations; queries **Crossref**, **DataCite**, **PubMed E-utilities**, and **arXiv** APIs with exponential backoff; enforces canonical **Title Similarity (`>= 0.45`)** + **Author Surname Overlap** + **Duplicate BibTeX Key Detection**; blocks `TODO`/`TBD`/`[?]` placeholders. | **HARD BLOCK** (`exit 2`) |
| **`G4_SERVER_SCREENING`** | Enforces server-specific rules for `arxiv` (`1,920`-char Step-3 abstract limit, no `\cite`/`\ref` in abstract, `..` path checks), `biorxiv`, `medrxiv`, and `chemrxiv`: abstract bounds, affiliations, concrete Code/Data Reproducibility links, missing figure file checks, `\write18` shell-escape bans, Competing Interests, IRB/ethics statements, and `medRxiv` clinical trial IDs (`NCT...`) + clinical directive safety checks. | **HARD BLOCK** (`exit 2`) |
| **`G5_CLAIM_GROUNDING`** | Detects purely computational / host-emulated studies and blocks unhedged wet-lab or clinical efficacy claims in Title, Abstract, and Conclusions. | **HARD BLOCK** (`exit 2`) |
| **`G6_REVERIFICATION_SEAL`** | Enforces **Pass-1 Audit $\rightarrow$ Remediation $\rightarrow$ Stateless `preprint-blind-auditor` Review $\rightarrow$ Pass-2 Re-Verification** locked to an exact Merkle **SHA-256** manifest digest (`.preprint_gate/.../release_seal.json`). | **HARD BLOCK** (`exit 2` + `PreToolUse` `"deny"`) |

---

## Two-Pass Hard-Gate Workflow

```mermaid
flowchart LR
    A["Pass 1: gate_runner.py --mode audit"] --> B{"Gates G1-G5 Clean?"}
    B -- "No" --> C["Remediate Manuscript & .bib"]
    C --> A
    B -- "Yes" --> D["Isolated Subagent: preprint-blind-auditor"]
    D --> E["record_blind_review.py (Binds SHA-256)"]
    E --> F["Pass 2: gate_runner.py --mode reverify"]
    F --> G{"All Gates Clean & SHA-256 Unchanged?"}
    G -- "No (1-Byte Drift or Blocker)" --> C
    G -- "Yes" --> H["release_seal.json"]
    H --> I["package_submission.py + PreToolUse Hook Allow"]
```

---

## Installation

```bash
git clone https://github.com/deesatzed/rxiv-gate.git
cd rxiv-gate
./install.sh
```

*(For local plugin development, run `./install.sh --link` to symlink into `~/.gemini/config/plugins/rxiv-gate`.)*

Restart **Google Antigravity** once after installing to activate the `rxiv-gate` plugin, `preprint-readiness-gate` skill, `preprint-blind-auditor` subagent, `rules/AGENTS.md`, and `hooks.json` runtime hard gate.

---

## CLI Usage (Single-File or Directory Mode)

`rxiv-gate` supports both **single-file targeting** (`--manuscript-file`, ideal when multiple `.tex` papers share a single `references.bib`) and **whole-directory targeting** (`--manuscript-dir`):

```bash
# 1. Pass-1 Audit (with live Crossref / DataCite / PubMed / arXiv DOI, title & author verification)
python3 skills/preprint-readiness-gate/scripts/gate_runner.py \
  --manuscript-file /path/to/paper1.tex \
  --server arxiv \
  --mode audit \
  --citation-mode online

# 2. Bind Isolated Blind Auditor Report to Live Merkle SHA-256
python3 skills/preprint-readiness-gate/scripts/record_blind_review.py \
  --manuscript-file /path/to/paper1.tex \
  --server arxiv \
  --review-file /tmp/blind_review.json

# 3. Pass-2 Hard-Gate Re-Verification (writes .preprint_gate/<stem>/release_seal.json)
python3 skills/preprint-readiness-gate/scripts/gate_runner.py \
  --manuscript-file /path/to/paper1.tex \
  --server arxiv \
  --mode reverify \
  --citation-mode online

# 4. Package Sealed Submission Archive + Compliance Certificate
python3 skills/preprint-readiness-gate/scripts/package_submission.py \
  --manuscript-file /path/to/paper1.tex \
  --server arxiv \
  --output /path/to/paper1_arxiv_sealed.tar.gz
```

---

## Running the Automated Test Suite

Zero third-party Python packages are required (pure Python 3.10+ standard library):

```bash
python3 -m unittest discover -s tests -v
```

---

## Sharing & Social Media Dissemination

See [`docs/SOCIAL_MEDIA_KIT.md`](docs/SOCIAL_MEDIA_KIT.md) for ready-to-post announcement copy for **X/Twitter**, **LinkedIn**, **Bluesky**, and the **Google Antigravity for Science** cohort channels, along with `1280x640` OpenGraph card instructions (`assets/social-preview.png`).

---

## License & Disclaimer

Licensed under the **Apache License, Version 2.0** (see [LICENSE](LICENSE)).

`rxiv-gate` is an independent open-source community plugin built for Google Antigravity users and is not affiliated with or endorsed by Google LLC, Cornell University (arXiv), or Cold Spring Harbor Laboratory (bioRxiv/medRxiv). Authors remain solely responsible for the accuracy, ethical compliance, and data licensing of their manuscripts.
