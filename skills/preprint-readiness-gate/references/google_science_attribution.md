# Google Antigravity for Science — Attribution & Disclosure Standard

Researchers participating in the **Google Antigravity for Science** program (or using Google Antigravity and the Google DeepMind Science Plugin) must comply with publisher AI transparency rules (ICMJE, COPE, arXiv, bioRxiv, medRxiv, ChemRxiv) and third-party database licensing terms.

## 1. Non-Negotiable Attribution Rules

1. **No AI Authorship (`G1_NO_AI_AUTHOR`)**:
   - AI agents, platforms, and foundation models (`Google Antigravity`, `Gemini`, `AlphaFold`, etc.) do not satisfy ICMJE authorship accountability criteria and **must never** appear in the author list or `\author{}` block.
2. **Methods / AI Workflow Disclosure (`G1_METHODS_AI_DISCLOSURE`)**:
   - Disclose in **Methods** (or a dedicated *AI-Assisted Workflows* / *Computational Reproducibility* subsection):
     - Platform: **Google Antigravity**
     - Frontier Model(s): e.g., **Gemini 4 Argon** or **Gemini 4 Carbon**
     - Plugin & Version: **Google DeepMind Science Plugin** (e.g., `v1.4.0`) and specific skills invoked
     - Specific task scope (e.g., literature search, analysis script generation, variant prioritization, structural visualization)
     - Explicit **human verification attestation** confirming that authors independently verified all code, citations, data outputs, and scientific interpretations.
3. **Program Support Acknowledgment (`G1_PROGRAM_ACKNOWLEDGMENT`)**:
   - Credit computational/platform access in **Acknowledgments**:
     > *"Computational and agentic research access was provided through the Google Antigravity for Science program."*
   - If your cohort welcome letter includes a specific award or cohort identifier, append it here.
4. **No Unapproved Logos or Endorsement Claims (`G1_NO_UNAPPROVED_LOGOS`)**:
   - Do not embed official Google or Google DeepMind logos/badges on preprint title pages or claim Google endorsement of scientific conclusions without written brand authorization.
5. **Third-Party Database & Tool Licenses (`G2_SKILL_LICENSES`)**:
   - Per the Science Plugin `SKILL_LICENSES.md`, Apache 2.0 covers only the plugin wrapper scripts—not external databases queried at runtime. Every queried resource (AlphaFold DB, AlphaGenome, gnomAD, GTEx, ChEMBL, PubChem, UniProt, Reactome, RCSB PDB, etc.) must be formally cited in your bibliography.
