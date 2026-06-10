#!/usr/bin/env bash
# Forensic LLM Wiki — full demo flow.
#
# Run from the repo root with the project's Python environment activated:
#   source .venv/bin/activate
#   bash examples/demo_commands.sh
#
# The whole script uses the mock LLM mode (no API key needed).
set -euo pipefail

PY=${PYTHON:-python}

banner() { printf "\n\033[1m==== %s ====\033[0m\n" "$1"; }

banner "1. Show raw evidence for case_001"
ls raw_sources/case_001/

banner "2. Dry-run ingest of case_001 (no files written)"
$PY fw.py ingest raw_sources/case_001 --dry-run | head -25

banner "3. Apply ingest of case_001"
$PY fw.py ingest raw_sources/case_001 --apply

banner "4. Compiled wiki on disk"
ls wiki/cases/case_001/
echo "(.fw/ holds the structured index, manifest, traces — see docs/architecture.md)"

banner "5. Ask the malware question against the compiled wiki"
$PY fw.py query case_001 "Is this confirmed malware?"

banner "6. Compare wiki answer to naive raw-source RAG baseline"
$PY fw.py compare case_001 "Is this confirmed malware?" | tail -40

banner "7. Lint the wiki"
$PY fw.py lint case_001

banner "8. Generate the draft final report"
$PY fw.py report case_001 | head -20

banner "9. Evolve the staged case (six evidence drops, one at a time)"
$PY fw.py evolve case_002_evolving

banner "10. Diff the wiki between step 02 (registry) and step 03 (clean AV scan)"
$PY fw.py diff-snapshots case_002_evolving \
    after_step_02_registry after_step_03_defender | head -40

banner "11. Benchmark: RAG vs LLM Wiki on 16 eval questions"
$PY fw.py benchmark case_002_evolving | head -22

banner "Done."
echo "Browse the final compiled wiki at:        wiki/cases/case_002_evolving/"
echo "Browse the snapshots after each step at:  wiki_snapshots/case_002_evolving/"
echo "Read the benchmark scorecard at:          benchmark_results/case_002_evolving/results.md"
echo "Read the per-step narrative at:           benchmark_results/case_002_evolving/evolution_report.md"
