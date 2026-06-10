# Demo flow (one-page)

A single-page index of the 60-second demo, the 3-minute demo, and the
5-minute live walkthrough. Pick the one that matches your audience.

## 60-second demo — `examples/demo_commands.sh`

The script in the repo. Runs end-to-end without API keys.

1. List raw evidence (`ls raw_sources/case_001/`).
2. Dry-run ingest, then apply.
3. Ask the malware question against the compiled wiki.
4. Run `compare` to print the RAG baseline next to the wiki — RAG
   confidently asserts what the wiki refuses.
5. Lint + final report.
6. `evolve` over the staged case — eval climbs 2 → 16 across six steps.
7. `diff-snapshots` between two consecutive steps.
8. `benchmark` — Wiki 16 / 16, RAG 4 / 16, refusal accuracy 1.00 vs 0.33.

Expected output examples live in
`examples/demo_expected_output.md`.

## 3-minute demo — `docs/demo_video_script.md`

The recordable version, scene by scene with voiceover. Adds:

- Opening README hook.
- Obsidian export + graph view.
- The four-way `compare-all` and `benchmark-methods` scorecards.
- The adversarial overclaim case (Phase 7).
- The review-queue catching a risky update.

## 5-minute live walkthrough — `docs/demo_script.md`

The talking script for in-person walkthroughs. Each step is a single
command and a one-sentence explanation.

## Reading order if you have 30 minutes

1. `README.md` — hook, thesis, method-comparison table.
2. `assets/method_comparison_table.md` — same table standalone.
3. `assets/architecture.mmd` — one Mermaid diagram.
4. `benchmark_results/case_002_evolving/results.md` — the two-way
   scorecard with real numbers.
5. `benchmark_results/case_002_evolving/method_comparison.md` — the
   four-way scorecard.
6. `CASE_STUDY.md` — full narrative.
7. `docs/threats_to_validity.md` — honest limits.

## Reading order if you have 5 minutes

1. README first screen.
2. `assets/method_comparison_table.md` numbers.
3. `PROJECT_SUMMARY.md` resume bullet.

That's the whole pitch.
