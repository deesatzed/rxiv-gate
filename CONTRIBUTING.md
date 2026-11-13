# Contributing to `rxiv-gate`

Contributions from fellow **Google Antigravity for Science** researchers and open-science developers are welcome!

## Adding Database License Mappings (`G2_SKILL_LICENSES`)

1. Add an entry in `skills/preprint-readiness-gate/references/skill_license_registry.json` specifying `id`, `skills`, `name`, `detect_patterns`, `cite_tokens`, `terms_url`, and `recommended_citation`.
2. Add a unit test case in `tests/test_gates_and_reverification.py` verifying both missing-citation failure and cited pass behavior.

## Adding or Refining Preprint Server Profiles (`G4_SERVER_SCREENING`)

1. Document the server's screening criteria in `skills/preprint-readiness-gate/references/server_screening_matrices.md`.
2. Implement deterministic checks in `evaluate_g4_server_screening` inside `skills/preprint-readiness-gate/scripts/gate_runner.py`.
3. Run the full test suite before opening a Pull Request:
   ```bash
   python3 -m unittest discover -s tests -v
   ```
