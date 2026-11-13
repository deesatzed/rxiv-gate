# Design System — `rxiv-gate`

## Visual Direction

**Cryptographic Ledger & Scientific Monograph** — built for computational researchers auditing and sealing preprints before uploading to arXiv, bioRxiv, medRxiv, and ChemRxiv.

## Palette Tokens

- **Grounds & Surfaces**:
  - `--bg-vellum`: `#090E1A` (Primary page ground)
  - `--bg-paper`: `#111A2E` (Elevated dossier & ledger table container)
  - `--bg-ledger`: `#0D1526` (Terminal and cryptographic inspector surface)
  - `--bg-ledger-elevated`: `#17233B` (Table headers and simulator toolbar)
- **Foreground & Ink**:
  - `--ink-primary`: `#F1F5F9` (Primary headings & prose, >14:1 contrast)
  - `--ink-secondary`: `#CBD5E1` (Cool-slate body copy, >10:1 contrast)
  - `--ink-muted`: `#94A3B8` (Secondary metadata & captions, >5.5:1 contrast)
- **Semantic Verification Accents**:
  - `--seal-emerald`: `#34D399` on `#042F24` / `#064E3B` (Cryptographic seal & primary actions, >8.5:1 contrast)
  - `--reject-vermilion`: `#FCA5A5` on `#450A0A` (Hard-gate blocker & drift diagnostic badges)
  - `--rule-hairline`: `#1E2D47` / `--rule-ledger`: `#283A5A` (1px structural hairlines)

## Typography

- **Display & Section Headings (`--font-display`)**: `STIX Two Text` (STI Pub scientific & mathematical journal serif), weights `600`–`700`, `text-wrap: balance`.
- **Body & Specification Tables (`--font-sans`)**: `Source Sans 3`, `1.0625rem` (`17px`), line-height `1.65`, `font-variant-numeric: tabular-nums`, `64–70ch` measure.
- **Code, SHA-256 Hashes & CLI Commands (`--font-mono`)**: `Fira Code`, used strictly for CLI commands, SHA-256 digests, and diagnostic codes.

## Interactive Components

1. **Interactive Merkle SHA-256 Drift Simulator (`#drift-btn`)**: Toggles a simulated 1-byte post-review edit in `paper1.tex`, demonstrating how `G6_REVERIFICATION_SEAL` and the `PreToolUse` hook transition immediately from `SEALED_FOR_SUBMISSION (ALLOW)` to `STALE_BLIND_REVIEW_HASH_MISMATCH (DENY)`.
2. **Server Screening Profile Matrix (`.server-tabs`)**: Accessible ARIA tablist switching between `arxiv`, `biorxiv`, `medrxiv`, and `chemrxiv` screening rules and CLI invocations.
3. **One-Click Dissemination Copy Controls (`[data-copy-target]`)**: Copies install snippets and ready-to-share X/Twitter, LinkedIn, and Cohort announcements to the clipboard.
