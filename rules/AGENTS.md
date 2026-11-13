# Preprint Readiness Hard-Gate Rules

Whenever preparing, reviewing, packaging, or certifying a scientific preprint or manuscript in an active workspace:

1. **Mandatory Two-Pass Hard Gate (`preprint-readiness-gate`)**:
   - **Never** declare a preprint "ready for submission", package a submission archive (`.tar.gz` / `.zip`), or generate a compliance certificate until **Pass 1 (`audit`) -> Remediation -> Independent Blind Review (`preprint-blind-auditor`) -> Pass 2 (`reverify`)** have all completed with exit code `0` and produced a hash-matched `.preprint_gate/release_seal.json`.
2. **Zero Post-Seal Drift**:
   - Any edit to any manuscript file (`.tex`, `.md`, `.bib`, figures, or supplementary files) invalidates the cryptographic `manuscript_sha256` seal. If a single byte changes after Pass 2, you **MUST** re-run blind review and `gate_runner.py --mode reverify` before packaging.
3. **Non-Waivable Hard Gates**:
   - **AI Authorship Prohibition**: Never list Google Antigravity, Gemini, or any AI tool/model as a manuscript author.
   - **Program & Workflow Disclosure**: Ensure explicit human-verified AI workflow disclosure in *Methods* and *Google Antigravity for Science* program support in *Acknowledgments* (when applicable), plus required citations for every third-party database/tool used via Science skills.
   - **Zero Hallucinated Citations**: Every DOI, PMID, PMCID, arXiv ID, and `.bib` entry must resolve and match title/author metadata before sealing.
