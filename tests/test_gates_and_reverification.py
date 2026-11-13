#!/usr/bin/env python3
# Copyright 2026 Antigravity for Science Community Contributors
# Licensed under the Apache License, Version 2.0.

"""End-to-end unit tests for all 6 hard gates, 1-byte drift detection, and PreToolUse hook."""

from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_SCRIPTS = REPO_ROOT / "skills" / "preprint-readiness-gate" / "scripts"
HOOK_SCRIPTS = REPO_ROOT / "scripts"

sys.path.insert(0, str(SKILL_SCRIPTS))
sys.path.insert(0, str(HOOK_SCRIPTS))

from gate_runner import run_all_gates  # noqa: E402
from package_submission import package_sealed_submission  # noqa: E402
from pre_submission_hook import evaluate_hook  # noqa: E402
from record_blind_review import record_blind_review  # noqa: E402


MOCK_REGISTRY = {
    "dois": {
        "10.1093/nar/gkad1011": {
            "title": "AlphaFold Protein Structure Database in 2024: providing structure coverage for over 214 million protein sequences",
            "authors": ["Varadi Mihaly", "Bertoni Damiano"],
        },
        "10.1038/s41586-023-06045-0": {
            "title": "A genomic mutational constraint map using variation in 76,156 human genomes",
            "authors": ["Chen Siwei", "Francioli Laurent", "Karczewski Konrad"],
        },
        "10.1021/acs.jcim.1c00203": {
            "title": "AutoDock Vina 1.2.0: New Docking Methods, Expanded Force Field, and Python Bindings",
            "authors": ["Eberhardt Jerome", "Santos-Martins Diogo"],
        },
        "10.1000/test.2025.001": {
            "title": "Statistical Methods for High Dimensional Biological Matrices",
            "authors": ["Smith Alice", "Jones Bob"],
        },
    },
    "pmids": {},
    "arxiv": {},
}

COMPLIANT_BIB = """\
@article{varadi2024alphafold,
  title = {AlphaFold Protein Structure Database in 2024: providing structure coverage for over 214 million protein sequences},
  author = {Varadi, Mihaly and Bertoni, Damiano and Magana, Paulyna},
  journal = {Nucleic Acids Research},
  year = {2024},
  doi = {10.1093/nar/gkad1011}
}

@article{chen2024gnomad,
  title = {A genomic mutational constraint map using variation in 76,156 human genomes},
  author = {Chen, Siwei and Francioli, Laurent and Karczewski, Konrad},
  journal = {Nature},
  year = {2024},
  doi = {10.1038/s41586-023-06045-0}
}

@article{eberhardt2021vina,
  title = {AutoDock Vina 1.2.0: New Docking Methods, Expanded Force Field, and Python Bindings},
  author = {Eberhardt, Jerome and Santos-Martins, Diogo},
  journal = {Journal of Chemical Information and Modeling},
  year = {2021},
  doi = {10.1021/acs.jcim.1c00203}
}
"""

COMPLIANT_TEX = r"""\documentclass{article}
\title{Computational Prioritization of Putative Allosteric Pockets Across Constrained Human Kinases}
\author{Ada Lovelace\thanks{Department of Computational Biology, Example University}}
\begin{document}
\maketitle

\begin{abstract}
Missense constraint metrics and predicted protein structures enable scalable in silico hypothesis generation for understudied kinases. Here we present a purely computational pipeline combining population constraint profiles from gnomAD with structural models from the AlphaFold Database and AutoDock Vina pocket scoring across 42 human kinases. Our predictive modeling identifies three putative allosteric cavities as computational candidates warranting downstream biochemical validation.
\end{abstract}

\section{Introduction}
Population constraint from gnomAD \cite{chen2024gnomad} and structural predictions from the AlphaFold Database \cite{varadi2024alphafold} accelerate target triage.

\section{Methods}
Pocket docking simulations were performed with AutoDock Vina \cite{eberhardt2021vina} across public de-identified summary data exempt from IRB review.

\subsection*{AI-Assisted Workflows and Reproducibility}
Literature triage, structural query orchestration, and Python analysis scripts were assisted using Google Antigravity powered by Gemini 4 Argon with the Google DeepMind Science Plugin (v1.4.0). All generated code, database queries, bibliographic citations, and scientific conclusions were independently executed and verified by the human authors.

\section{Conclusions}
These in silico docking predictions nominate candidate pockets that require future wet-lab experimental validation.

\section*{Data and Code Availability}
All scripts, structure manifests, and docking configurations are publicly available at https://github.com/example-lab/kinase-pocket-screen (Zenodo DOI: 10.5281/zenodo.1234567).

\section*{Competing Interests}
The authors declare no competing interests.

\section*{Acknowledgments}
Computational and agentic research platform access was provided through the Google Antigravity for Science program.

\bibliography{references}
\end{document}
"""


class PreprintHardGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.mock_reg_path = self.root / "mock_registry.json"
        self.mock_reg_path.write_text(json.dumps(MOCK_REGISTRY), encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_compliant_manuscript(self, subdir: str = "paper") -> Path:
        mdir = self.root / subdir
        mdir.mkdir(parents=True, exist_ok=True)
        (mdir / "manuscript.tex").write_text(COMPLIANT_TEX, encoding="utf-8")
        (mdir / "references.bib").write_text(COMPLIANT_BIB, encoding="utf-8")
        return mdir

    def test_pass1_catches_all_defects_and_blocks(self) -> None:
        mdir = self.root / "bad_paper"
        mdir.mkdir()
        bad_tex = r"""\documentclass{article}
\title{Definitive Cure Identified via AlphaFold Database and gnomAD}
\author{Jane Doe, Gemini 4 Argon, Google Antigravity}
\begin{document}
\begin{abstract}
Short abstract claiming experimentally confirmed results.
\end{abstract}
\includegraphics{/Users/jane/Desktop/deepmind_logo.png}
\includegraphics{figures/nonexistent_plot.pdf}
\immediate\write18{rm -rf /}
We queried the AlphaFold Database and gnomAD and ran AutoDock Vina \cite{hallucinated2026,wrongtitle2024,wrongauthor2021,dangling2026}.
TODO: finish table XX%.
\section{Conclusions}
Our docking scores are clinically proven and experimentally confirmed.
\end{document}
"""
        bad_bib = """\
@article{hallucinated2026,
  title = {Completely Fabricated Paper},
  author = {Nobody, Fake},
  year = {2026},
  doi = {10.9999/nonexistent.2026.0001}
}

@article{wrongtitle2024,
  title = {Quantum Gravity Loops in Superconducting Qubits},
  author = {Wrong, Author},
  year = {2024},
  doi = {10.1093/nar/gkad1011}
}

@article{wrongauthor2021,
  title = {Statistical Methods for High Dimensional Biological Matrices},
  author = {Fakename, Imaginary and Ghost, Researcher},
  year = {2025},
  doi = {10.1000/test.2025.001}
}

@article{wrongauthor2021,
  title = {Duplicate Entry With Same Key},
  author = {Smith, Alice},
  year = {2025},
  doi = {10.1000/test.2025.001}
}
"""
        (mdir / "manuscript.tex").write_text(bad_tex, encoding="utf-8")
        (mdir / "references.bib").write_text(bad_bib, encoding="utf-8")

        report = run_all_gates(
            manuscript_dir=mdir,
            server="biorxiv",
            mode="audit",
            citation_mode="mock",
            mock_registry=self.mock_reg_path,
        )
        self.assertFalse(report["overall_passed"])
        self.assertFalse(report["sealed_for_submission"])

        g1_codes = {f["code"] for f in report["gates"]["G1_AI_ATTRIBUTION"]["failures"]}
        self.assertIn("AI_LISTED_AS_AUTHOR", g1_codes)
        self.assertIn("INCOMPLETE_AI_WORKFLOW_DISCLOSURE", g1_codes)
        self.assertIn("MISSING_SCIENCE_PROGRAM_ACKNOWLEDGMENT", g1_codes)
        self.assertIn("UNAPPROVED_BRAND_LOGO", g1_codes)

        g2_codes = {f["resource_id"] for f in report["gates"]["G2_SKILL_LICENSES"]["failures"]}
        self.assertIn("alphafold-db", g2_codes)
        self.assertIn("gnomad", g2_codes)
        self.assertIn("autodock-vina", g2_codes)

        g3_codes = {f["code"] for f in report["gates"]["G3_CITATIONS"]["failures"]}
        self.assertIn("UNRESOLVED_CITATION_IDENTIFIER", g3_codes)
        self.assertIn("CITATION_TITLE_MISMATCH", g3_codes)
        self.assertIn("CITATION_AUTHOR_MISMATCH", g3_codes)
        self.assertIn("DUPLICATE_BIB_KEY", g3_codes)
        self.assertIn("MISSING_BIB_ENTRY", g3_codes)
        self.assertIn("UNRESOLVED_PLACEHOLDER", g3_codes)

        g4_codes = {f["code"] for f in report["gates"]["G4_SERVER_SCREENING"]["failures"]}
        self.assertIn("ABSTRACT_TOO_SHORT_OR_MISSING", g4_codes)
        self.assertIn("MISSING_AUTHOR_AFFILIATIONS", g4_codes)
        self.assertIn("MISSING_DATA_CODE_AVAILABILITY", g4_codes)
        self.assertIn("MISSING_COMPETING_INTERESTS", g4_codes)
        self.assertIn("NON_PORTABLE_TEX_PATH", g4_codes)
        self.assertIn("MISSING_REFERENCED_FIGURE", g4_codes)
        self.assertIn("FORBIDDEN_TEX_WRITE18", g4_codes)

        g5_codes = {f["code"] for f in report["gates"]["G5_CLAIM_GROUNDING"]["failures"]}
        self.assertIn("UNHEDGED_COMPUTATIONAL_CLAIM", g5_codes)
        self.assertIn("ABSTRACT_MISSING_IN_SILICO_SCOPE", g5_codes)

    def test_medrxiv_clinical_hard_gates(self) -> None:
        mdir = self._write_compliant_manuscript("medrxiv_bad")
        clinical_tex = COMPLIANT_TEX.replace(
            "public de-identified summary data exempt from IRB review.",
            "a randomized controlled clinical trial of 120 patients at City Clinic. Patients should take 50 mg daily.",
        )
        (mdir / "manuscript.tex").write_text(clinical_tex, encoding="utf-8")

        report = run_all_gates(
            manuscript_dir=mdir,
            server="medrxiv",
            mode="audit",
            citation_mode="mock",
            mock_registry=self.mock_reg_path,
        )
        self.assertFalse(report["overall_passed"])
        g4_codes = {f["code"] for f in report["gates"]["G4_SERVER_SCREENING"]["failures"]}
        self.assertIn("MISSING_ETHICS_IRB_STATEMENT", g4_codes)
        self.assertIn("MEDRXIV_MISSING_TRIAL_REGISTRATION", g4_codes)
        self.assertIn("MEDRXIV_MISSING_CONSENT_OR_DEIDENTIFICATION", g4_codes)
        self.assertIn("MEDRXIV_CLINICAL_TREATMENT_DIRECTIVE", g4_codes)

    def test_reverify_hard_gates_and_1_byte_drift_lock(self) -> None:
        mdir = self._write_compliant_manuscript("strict_flow")

        # 1. Reverify before Pass-1 audit -> HARD FAIL
        early_reverify = run_all_gates(
            manuscript_dir=mdir,
            server="biorxiv",
            mode="reverify",
            citation_mode="mock",
            mock_registry=self.mock_reg_path,
        )
        self.assertFalse(early_reverify["overall_passed"])
        g6_early = {f["code"] for f in early_reverify["gates"]["G6_REVERIFICATION_SEAL"]["failures"]}
        self.assertIn("MISSING_PASS1_AUDIT", g6_early)
        self.assertIn("MISSING_BLIND_REVIEW_ATTESTATION", g6_early)

        # 2. Pass-1 audit passes G1-G5, but does NOT seal for packaging
        pass1 = run_all_gates(
            manuscript_dir=mdir,
            server="biorxiv",
            mode="audit",
            citation_mode="mock",
            mock_registry=self.mock_reg_path,
        )
        self.assertTrue(pass1["overall_passed"])
        self.assertFalse(pass1["sealed_for_submission"])

        with self.assertRaises(PermissionError):
            package_sealed_submission(mdir, self.root / "unsealed.tar.gz", expected_server="biorxiv")

        # Hook must also DENY packaging after Pass-1 alone
        hook_res_unsealed = evaluate_hook(
            {
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": f"tar -czf biorxiv_submission.tar.gz -C {mdir} ."},
                },
                "workspacePaths": [str(mdir)],
            }
        )
        self.assertEqual(hook_res_unsealed["decision"], "deny")

        # 3. Syntax-only citation mode is FORBIDDEN in Pass-2 reverify
        syntax_reverify = run_all_gates(
            manuscript_dir=mdir,
            server="biorxiv",
            mode="reverify",
            citation_mode="syntax-only",
        )
        self.assertFalse(syntax_reverify["overall_passed"])
        self.assertEqual(
            syntax_reverify["gates"]["G3_CITATIONS"]["failures"][0]["code"],
            "SYNTAX_ONLY_FORBIDDEN_IN_REVERIFY",
        )

        # 4. Blind review with non-empty blockers cannot pass even if verdict claims PASS
        bad_blind = record_blind_review(
            mdir,
            {
                "auditor": "preprint-blind-auditor",
                "target_server": "biorxiv",
                "verdict": "PASS",
                "summary": "Has a blocker.",
                "blockers": [{"id": "B1", "detail": "Overstated figure claim"}],
                "warnings": [],
            },
            expected_server="biorxiv",
        )
        self.assertEqual(bad_blind["verdict"], "FAIL")

        # 5. Record clean blind review bound to SHA-256 H1
        clean_blind = record_blind_review(
            mdir,
            {
                "auditor": "preprint-blind-auditor",
                "target_server": "biorxiv",
                "verdict": "PASS",
                "summary": "All computational claims properly qualified and disclosures verified.",
                "blockers": [],
                "warnings": [],
            },
            expected_server="biorxiv",
        )
        self.assertEqual(clean_blind["verdict"], "PASS")

        # 6. Modify 1 byte in manuscript.tex AFTER blind review -> Pass-2 MUST HARD BLOCK!
        orig_tex = (mdir / "manuscript.tex").read_text(encoding="utf-8")
        (mdir / "manuscript.tex").write_text(orig_tex + "\n", encoding="utf-8")

        drifted_reverify = run_all_gates(
            manuscript_dir=mdir,
            server="biorxiv",
            mode="reverify",
            citation_mode="mock",
            mock_registry=self.mock_reg_path,
        )
        self.assertFalse(drifted_reverify["overall_passed"])
        self.assertFalse(drifted_reverify["sealed_for_submission"])
        drift_codes = {f["code"] for f in drifted_reverify["gates"]["G6_REVERIFICATION_SEAL"]["failures"]}
        self.assertIn("STALE_BLIND_REVIEW_HASH_MISMATCH", drift_codes)

        # 7. Re-record blind review on current files & run Pass-2 reverify -> SEALED!
        record_blind_review(
            mdir,
            {
                "auditor": "preprint-blind-auditor",
                "target_server": "biorxiv",
                "verdict": "PASS",
                "summary": "Re-verified exact final manuscript hash.",
                "blockers": [],
                "warnings": [],
            },
            expected_server="biorxiv",
        )
        sealed_pass2 = run_all_gates(
            manuscript_dir=mdir,
            server="biorxiv",
            mode="reverify",
            citation_mode="mock",
            mock_registry=self.mock_reg_path,
        )
        self.assertTrue(sealed_pass2["overall_passed"])
        self.assertTrue(sealed_pass2["sealed_for_submission"])

        # Hook allows sealed packaging
        hook_res_sealed = evaluate_hook(
            {
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": f"tar -czf biorxiv_submission.tar.gz -C {mdir} ."},
                },
                "workspacePaths": [str(mdir)],
            }
        )
        self.assertEqual(hook_res_sealed["decision"], "allow")

        # Package submission succeeds and includes Compliance Certificate
        bundle_path = self.root / "biorxiv_sealed_bundle.tar.gz"
        pkg = package_sealed_submission(mdir, bundle_path, expected_server="biorxiv")
        self.assertTrue(pkg["packaged"])
        with tarfile.open(bundle_path, "r:gz") as tar:
            names = set(tar.getnames())
        self.assertIn("manuscript.tex", names)
        self.assertIn("references.bib", names)
        self.assertIn("SUBMISSION_COMPLIANCE_CERTIFICATE.md", names)

        # 8. Post-seal 1-byte edit to references.bib immediately breaks both Hook and Packager!
        orig_bib = (mdir / "references.bib").read_text(encoding="utf-8")
        (mdir / "references.bib").write_text(orig_bib + "\n", encoding="utf-8")

        hook_post_drift = evaluate_hook(
            {
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": f"python3 package_submission.py --manuscript-dir {mdir}"},
                },
                "workspacePaths": [str(mdir)],
            }
        )
        self.assertEqual(hook_post_drift["decision"], "deny")
        self.assertIn("POST-SEAL DRIFT", hook_post_drift["reason"])

        with self.assertRaises(PermissionError):
            package_sealed_submission(mdir, self.root / "should_fail.tar.gz", expected_server="biorxiv")

    def test_cli_exit_codes_and_stdin_hook_subprocess(self) -> None:
        mdir = self._write_compliant_manuscript("cli_flow")
        gate_cli = SKILL_SCRIPTS / "gate_runner.py"
        blind_cli = SKILL_SCRIPTS / "record_blind_review.py"
        pkg_cli = SKILL_SCRIPTS / "package_submission.py"

        # Pass-2 reverify before Pass-1 must exit 2
        r_fail = subprocess.run(
            [
                sys.executable,
                str(gate_cli),
                "--manuscript-dir",
                str(mdir),
                "--server",
                "arxiv",
                "--mode",
                "reverify",
                "--citation-mode",
                "mock",
                "--mock-registry",
                str(self.mock_reg_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r_fail.returncode, 2)

        # Pass-1 audit exits 0
        r_p1 = subprocess.run(
            [
                sys.executable,
                str(gate_cli),
                "--manuscript-dir",
                str(mdir),
                "--server",
                "arxiv",
                "--mode",
                "audit",
                "--citation-mode",
                "mock",
                "--mock-registry",
                str(self.mock_reg_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r_p1.returncode, 0)

        # Hook subprocess invoked from REPO_ROOT (matching hooks.json CWD) blocks before Pass-2 seal
        hook_stdin = json.dumps(
            {
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": f"tar -czf arxiv_bundle.tar.gz -C {mdir} ."},
                },
                "workspacePaths": [str(mdir)],
            }
        )
        r_hook_deny = subprocess.run(
            [sys.executable, "./scripts/pre_submission_hook.py"],
            cwd=str(REPO_ROOT),
            input=hook_stdin,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r_hook_deny.returncode, 0)
        self.assertEqual(json.loads(r_hook_deny.stdout)["decision"], "deny")

        # Bind blind review via stdin
        blind_payload = json.dumps(
            {
                "auditor": "preprint-blind-auditor",
                "target_server": "arxiv",
                "verdict": "PASS",
                "summary": "Clean arXiv manuscript.",
                "blockers": [],
                "warnings": [],
            }
        )
        r_blind = subprocess.run(
            [sys.executable, str(blind_cli), "--manuscript-dir", str(mdir), "--server", "arxiv"],
            input=blind_payload,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r_blind.returncode, 0)

        # Pass-2 reverify exits 0 and seals
        r_p2 = subprocess.run(
            [
                sys.executable,
                str(gate_cli),
                "--manuscript-dir",
                str(mdir),
                "--server",
                "arxiv",
                "--mode",
                "reverify",
                "--citation-mode",
                "mock",
                "--mock-registry",
                str(self.mock_reg_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r_p2.returncode, 0)

        # Hook subprocess now allows packaging
        r_hook_allow = subprocess.run(
            [sys.executable, "./scripts/pre_submission_hook.py"],
            cwd=str(REPO_ROOT),
            input=hook_stdin,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r_hook_allow.returncode, 0)
        self.assertEqual(json.loads(r_hook_allow.stdout)["decision"], "allow")

        # Package CLI exits 0
        out_tgz = self.root / "arxiv_cli_sealed.tar.gz"
        r_pkg = subprocess.run(
            [
                sys.executable,
                str(pkg_cli),
                "--manuscript-dir",
                str(mdir),
                "--server",
                "arxiv",
                "--output",
                str(out_tgz),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r_pkg.returncode, 0)
        self.assertTrue(out_tgz.exists())


if __name__ == "__main__":
    unittest.main()
