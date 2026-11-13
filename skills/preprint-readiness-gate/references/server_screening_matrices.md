# Preprint Server Screening Matrices (`G4_SERVER_SCREENING`)

Each preprint server enforces distinct pre-posting screening gates. `gate_runner.py` validates manuscripts against the selected `--server` profile (`arxiv`, `biorxiv`, `medrxiv`, or `chemrxiv`).

| Gate Requirement | `arxiv` | `biorxiv` | `medrxiv` | `chemrxiv` |
| :--- | :---: | :---: | :---: | :---: |
| Non-empty Title & Abstract (30–500 words) | HARD | HARD | HARD | HARD |
| Author Affiliations Present | HARD | HARD | HARD | HARD |
| AI / Agentic Workflow Disclosure (when AI used) | HARD | HARD | HARD | HARD |
| Data & Code Availability Statement | WARN/HARD* | HARD | HARD | HARD |
| Competing Interests / COI Declaration | WARN | HARD | HARD | HARD |
| No Unresolved Placeholders (`TODO`, `TBD`, `[?]`) | HARD | HARD | HARD | HARD |
| TeX Portability (no `/Users/...` or `/home/...` paths) | HARD | HARD (if TeX) | HARD (if TeX) | HARD (if TeX) |
| Human/Animal Ethics / IRB Approval or Exemption | Conditional | HARD (if bio/human/animal) | **HARD (Always)** | Conditional |
| Clinical Trial Registration ID (`NCT...` / ICTRP) | N/A | N/A | **HARD (if clinical trial)** | N/A |
| Patient De-Identification & Consent Attestation | N/A | Conditional | **HARD (if human/clinical)** | N/A |
| No Direct Clinical Treatment Recommendations | N/A | WARN | **HARD** | N/A |

*\*Data & Code Availability is enforced as a Hard Gate across all Google Antigravity for Science computational manuscripts to ensure reproducibility.*

## Common Screening Rejection Triggers in AI-Assisted Manuscripts

1. **Hallucinated or Mismatched Citations (`G3_CITATIONS`)**: Valid-looking DOIs that 404 or point to an unrelated paper, or fabricated author/year combinations.
2. **Overstated *In Silico* Claims (`G5_CLAIM_GROUNDING`)**: Describing predicted binding affinities, docking poses, variant pathogenicity scores, or co-folded complexes as "experimentally validated", "clinically proven", or "therapeutic cures" without wet-lab or clinical assay sections.
3. **medRxiv Clinical Safety Blocks**: Missing IRB/ethics committee names, missing prospective trial registration numbers (`NCT...`, `ISRCTN...`, `EudraCT`), or identifiable patient details (exact dates of hospital admission, initials, medical record numbers).
