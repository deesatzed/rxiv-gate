# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

static HTML/CSS/JS (`docs/index.html` for GitHub Pages)

## Users

Computational biologists, physicists, chemists, machine learning researchers, and principal investigators in the 10,000-member Google Antigravity for Science cohort (and broader open-science community) preparing LaTeX (`.tex`/`.bib`) or Markdown (`.md`) preprints for submission to arXiv, bioRxiv, medRxiv, or ChemRxiv.

## Product Purpose

`rxiv-gate` prevents AI-era preprint screening rejections, citation hallucinations, unattributed database usage, and post-review edit drift before submission. It enforces 6 deterministic hard gates, an isolated zero-context blind auditor subagent (`preprint-blind-auditor`), a two-pass Merkle SHA-256 release seal (`release_seal.json`), and an Antigravity `PreToolUse` runtime hook that blocks `.tar.gz`/`.zip` submission archiving if any gate fails or if even 1 byte changes after re-verification.

## Positioning

Unlike LaTeX syntax linters or HTTP-200 link checkers, `rxiv-gate` performs live Crossref, DataCite, PubMed E-utilities, and arXiv API resolution with canonical title similarity (`>= 0.45`) and author surname overlap verification, checks 34 third-party scientific databases from the Google DeepMind Science Plugin (`SKILL_LICENSES.md`), and cryptographically binds a two-pass audit + isolated blind review to the exact composite SHA-256 digest of every manuscript file.

## Operating Context

Used inside Google Antigravity IDE and CLI workflows (`gate_runner.py`, `record_blind_review.py`, `package_submission.py`, and `pre_submission_hook.py`) immediately prior to uploading a manuscript archive to arXiv, bioRxiv, medRxiv, or ChemRxiv.

## Capabilities and Constraints

- Zero third-party Python dependencies (pure Python 3.10+ standard library).
- Supports both single-file (`--manuscript-file`) and whole-directory (`--manuscript-dir`) scoping.
- Enforces 6 hard gates: `G1_AI_ATTRIBUTION`, `G2_SKILL_LICENSES`, `G3_CITATIONS`, `G4_SERVER_SCREENING`, `G5_CLAIM_GROUNDING`, and `G6_REVERIFICATION_SEAL`.
- Licensed under Apache-2.0 (`https://github.com/deesatzed/rxiv-gate`).

## Brand Commitments

- Name: `rxiv-gate` (`v1.1.0`)
- Voice: Rigorous, empirical, transparent, peer-scientist to peer-scientist.
- Disclaimer: Independent open-source community plugin built for Google Antigravity users; not affiliated with or endorsed by Google LLC, Cornell University (arXiv), or Cold Spring Harbor Laboratory (bioRxiv/medRxiv).

## Evidence on Hand

- Live evaluation catch on a 55-reference arXiv manuscript (`paper1_core_control_and_coral_npu.tex`): caught `degrandi2015fungicides` (`DOI: 10.1016/j.jinsphys.2015.06.004`), which returned `HTTP 200` on Elsevier/Crossref but resolved to an unrelated silkworm *Bombyx Wnt1* CRISPR study (`similarity = 0.00`) instead of the authentic *Journal of Economic Entomology* honey bee ATP study (`10.1093/jee/tov251`).
- 34 mapped scientific database license entries across all 41 Google DeepMind Science Plugin skills (`skills/preprint-readiness-gate/references/skill_license_registry.json`).
- End-to-end automated unit and CLI/hook test suite (`tests/test_gates_and_reverification.py`).

## Product Principles

1. **Cryptographic Determinism Over Advisory Checklists:** A gate that does not block unsealed packaging or detect 1-byte post-review drift is merely advice.
2. **Semantic Verification Over HTTP Status Codes:** A resolving DOI is only valid if its canonical title and author surnames match the manuscript's bibliography entry.
3. **Zero-Friction Reproducibility:** Pure Python 3.10+ standard library with zero external dependencies so any researcher can run it in 30 seconds.
