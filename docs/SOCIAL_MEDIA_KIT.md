# `rxiv-gate` Social Media & Cohort Dissemination Kit

This folder and the [`assets/`](../assets/) directory include visual cards and ready-to-paste copy to share **`rxiv-gate`** across X/Twitter, LinkedIn, Bluesky, and the **10,000-member Google Antigravity for Science** cohort.

---

## 1. Visual Assets Ready to Attach

| File | Resolution / Format | Best Used For |
| :--- | :--- | :--- |
| [`assets/social-preview.png`](../assets/social-preview.png) | `1280 × 640` PNG | **GitHub Repository Social Preview** (`Settings → General → Social preview`), X/Twitter single-image card, LinkedIn link preview |
| [`assets/screenshot-pass1-catch.png`](../assets/screenshot-pass1-catch.png) | `960 × 460` PNG | Showing Pass-1 live Crossref DOI/title mismatch detection (`degrandi2015fungicides`) + `PreToolUse` runtime blocker |
| [`assets/screenshot-pass2-sealed.png`](../assets/screenshot-pass2-sealed.png) | `960 × 440` PNG | Showing Pass-2 isolated blind review binding + cryptographic SHA-256 `SEALED_FOR_SUBMISSION` lock |
| [`assets/hero-banner.svg`](../assets/hero-banner.svg) | Vector SVG | High-DPI README hero banner and web embeds |

### Setting the GitHub Social Preview (Takes 15 Seconds)
1. Open **`https://github.com/deesatzed/rxiv-gate/settings`**
2. Scroll to **Social preview** → Click **Edit** → **Upload an image...**
3. Select `assets/social-preview.png` (`1280 × 640`).
4. Any link shared to `https://github.com/deesatzed/rxiv-gate` on X, LinkedIn, Slack, Discord, or Bluesky will automatically unfurl with the full visual card.

---

## 2. X / Twitter Launch Thread (or Single Long-Form Post)

**Tweet 1 (Attach `assets/social-preview.png`):**
> Built an open-source compliance & cryptographic verification plugin for the 10,000 researchers in the **Google Antigravity for Science** cohort: **`rxiv-gate`** 🛡️📄
>
> Before you submit to arXiv, bioRxiv, medRxiv, or ChemRxiv, it runs 6 deterministic Hard Gates + a 2-pass SHA-256 release seal.
>
> Repo: https://github.com/deesatzed/rxiv-gate

**Tweet 2 (Attach `assets/screenshot-pass1-catch.png`):**
> Why HTTP-200 DOI checks aren't enough for AI-assisted papers:
>
> On our first live test of a 55-reference arXiv manuscript, every DOI returned `200 OK`.
>
> Gate G3 (`CITATION_TITLE_MISMATCH`) caught a `.bib` entry whose DOI (`10.1016/j.jinsphys.2015.06.004`) resolved on Crossref to an unrelated silkworm CRISPR paper (`similarity = 0.00`) instead of the cited honey bee ATP study (`10.1093/jee/tov251`).

**Tweet 3 (Attach `assets/screenshot-pass2-sealed.png`):**
> How the Two-Pass Cryptographic Hard Gate works:
>
> 1️⃣ Pass-1 Audit (`G1`–`G5`): AI/program disclosures, 34 Science Plugin DB licenses (`SKILL_LICENSES.md`), live Crossref/DataCite/PubMed/arXiv title+author match, server & IRB rules, in-silico claim hedging
> 2️⃣ Zero-context `preprint-blind-auditor` subagent review bound to the manuscript's Merkle SHA-256
> 3️⃣ Pass-2 Re-verify + `PreToolUse` hook: blocks `.tar.gz` packaging if even 1 byte drifts after review!

**Tweet 4:**
> Zero third-party Python dependencies (pure Python 3.10+ stdlib). Install into Google Antigravity in 30 seconds:
>
> ```bash
> git clone https://github.com/deesatzed/rxiv-gate.git
> cd rxiv-gate && ./install.sh
> ```
>
> Apache-2.0 open source: https://github.com/deesatzed/rxiv-gate

---

## 3. LinkedIn Announcement Post (Attach `assets/social-preview.png`)

> Excited to open-source **`rxiv-gate`** (`v1.1.0`)—a two-pass scientific preprint readiness, live citation verification, and SHA-256 cryptographic hard-gate plugin built for researchers in the **Google Antigravity for Science** program (and the broader scientific community) submitting to **arXiv, bioRxiv, medRxiv, and ChemRxiv**.
>
> Agentic research workflows dramatically accelerate mathematical derivations, simulations, and literature synthesis—but they also introduce failure modes that standard LaTeX linters and HTTP-200 link checkers miss:
>
> • **Real-DOI / Wrong-Paper Conflations:** During our first live audit of a 55-reference arXiv manuscript, `rxiv-gate` caught a valid, live Elsevier DOI (`HTTP 200`) that actually resolved on Crossref to an unrelated silkworm *Bombyx Wnt1* CRISPR article (`title similarity = 0.00`) rather than the cited honey bee bioenergetics paper.
> • **Third-Party Scientific Database Attribution:** Automatically scans prose and code against 34 scientific databases and tools in the Google DeepMind Science Plugin (`SKILL_LICENSES.md`—AlphaFold DB, AlphaGenome, gnomAD, ChEMBL, PubChem, UniProt, Reactome, OpenMM, AutoDock Vina, etc.) to ensure every queried resource is formally cited.
> • **ICMJE/COPE AI Governance & Program Attribution:** Enforces zero AI co-authorship, explicit *Methods* disclosure of Google Antigravity + Gemini model version + human verification, and *Google Antigravity for Science* program acknowledgment.
> • **Two-Pass Merkle SHA-256 Seal & Runtime Hook:** Combines a stateless `preprint-blind-auditor` subagent with a cryptographic `release_seal.json` and a `PreToolUse` hook that blocks submission archiving if any gate fails or if even **1 byte** changes after re-verification.
>
> Pure Python 3.10+ standard library (zero external dependencies), Apache-2.0 licensed, and ready to install in 30 seconds:
> 🔗 https://github.com/deesatzed/rxiv-gate

---

## 4. Google Antigravity for Science Cohort Message (Slack / Discord / Forum)

> Hey everyone 👋 — we built an open-source Antigravity plugin called **`rxiv-gate`** (`https://github.com/deesatzed/rxiv-gate`) to help everyone in the **Google Antigravity for Science** cohort screen, verify, and cryptographically seal preprints before uploading to **arXiv, bioRxiv, medRxiv, or ChemRxiv**.
>
> **What it checks automatically:**
> - **G1 (AI & Program Attribution):** Verifies human-only authorship, *Methods* AI workflow disclosure (`Google Antigravity` + `Gemini` model + human verification attestation), and *Google Antigravity for Science* acknowledgment.
> - **G2 (Science Plugin `SKILL_LICENSES.md`):** Detects usage of 34 Science Plugin databases/tools in your text or code and verifies each one is cited in your `.bib`.
> - **G3 (Live Crossref / DataCite / PubMed / arXiv Verification):** Verifies not just that DOIs/PMIDs resolve, but that canonical **titles** (`>= 0.45` similarity) and **author surnames** match (already caught a real-DOI/wrong-paper bug in our own 55-ref arXiv paper!).
> - **G4 & G5 (Server & Claim Grounding):** Checks arXiv's 1,920-char abstract limit & `..` path portability, medRxiv IRB/NCT trial IDs, and ensures purely computational studies hedge *in silico* predictions.
> - **G6 (Two-Pass SHA-256 Hard Gate):** Runs an isolated `preprint-blind-auditor` subagent and locks a SHA-256 `release_seal.json` with a `PreToolUse` hook so unsealed or post-review-drifted manuscripts cannot be packaged.
>
>Feedback and PRs from the cohort are super welcome!
