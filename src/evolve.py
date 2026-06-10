"""Evolve workflow: ingest a multi-step case one step at a time.

Each step is a sub-directory under ``raw_sources/<case_id>/``, named
``step_NN_*``. The orchestrator:

1. Wipes any existing wiki state for the case (so the run starts clean).
2. Walks the step directories in lexical order.
3. For each step:
   a. Ingests only that step's files (``ingest_case(subdir=...)``).
   b. Takes a snapshot under ``wiki_snapshots/<case_id>/after_<step>/``.
   c. Runs lint and (if present) the case's eval suite.
   d. Answers a "key question" against the current wiki and captures the
      assessment.
   e. Updates ``hypothesis_history.json`` with the post-step confidence
      of every active hypothesis.
4. Writes ``benchmark_results/<case_id>/evolution_report.md`` summarising
   what happened at every step.

The purpose is pedagogical: read evolution_report.md and watch how the
wiki's assessment shifts as evidence accumulates — especially when an
investigator's "malware confirmed" overclaim is later softened by a clean
AV scan and an inconclusive hash reputation.
"""
from __future__ import annotations

import shutil
from copy import deepcopy
from pathlib import Path

from .eval import load_eval_file, run_eval
from .hypothesis_history import update_history
from .ingest import ingest_case
from .lint import lint_case
from .llm import LLMClient
from .query import answer_question
from .schemas import EvolutionResult, EvolveStep
from .snapshots import snapshots_case_dir, take_snapshot
from .wiki_io import case_dir, load_state, raw_case_dir

KEY_QUESTION_DEFAULT = "Is this confirmed malware?"


def benchmark_root(project_root: Path) -> Path:
    return project_root / "benchmark_results"


def benchmark_case_dir(project_root: Path, case_id: str) -> Path:
    return benchmark_root(project_root) / case_id


def list_step_dirs(project_root: Path, case_id: str) -> list[Path]:
    raw_dir = raw_case_dir(project_root, case_id)
    if not raw_dir.exists():
        return []
    return sorted(
        p for p in raw_dir.iterdir()
        if p.is_dir() and p.name.startswith("step_")
    )


def evolve_case(
    project_root: Path,
    case_id: str,
    *,
    llm: LLMClient | None = None,
    key_question: str = KEY_QUESTION_DEFAULT,
    fresh: bool = True,
) -> EvolutionResult:
    """Walk every step directory in order, ingesting and snapshotting."""
    step_dirs = list_step_dirs(project_root, case_id)
    if not step_dirs:
        raise FileNotFoundError(
            f"No step directories found in raw_sources/{case_id}/. "
            f"Expected step_01_*, step_02_*, ..."
        )

    if fresh:
        _wipe_case(project_root, case_id)

    llm = llm or LLMClient()
    result = EvolutionResult(case_id=case_id, key_question=key_question)
    prior_state = load_state(project_root, case_id)
    prior_hypotheses = {k: deepcopy(h) for k, h in prior_state.hypotheses.items()}
    prior_contradictions = set(prior_state.contradictions)

    for step_path in step_dirs:
        step_name = step_path.name
        subdir = step_name  # relative to raw_sources/<case_id>/

        ingest_report = ingest_case(
            project_root, case_id,
            llm=llm,
            subdir=subdir,
        )
        state = load_state(project_root, case_id)

        snapshot_name = f"after_{step_name}"
        take_snapshot(project_root, case_id, snapshot_name)

        lint_report = lint_case(project_root, case_id)
        lint_summary = lint_report.summary()

        try:
            eval_summary = run_eval(project_root, case_id) if load_eval_file(project_root, case_id) else None
        except FileNotFoundError:
            eval_summary = None

        key_answer = answer_question(project_root, case_id, key_question)
        key_assessment = key_answer.assessment or key_answer.answer

        update_history(
            project_root, case_id, step_name, state,
            assessment_by_title={t.lower(): key_assessment for t in state.hypotheses},
        )

        new_hyps = [
            state.hypotheses[k].title
            for k in state.hypotheses
            if k not in prior_hypotheses
        ]
        confidence_changes = []
        for k in state.hypotheses:
            if k in prior_hypotheses:
                old_c = prior_hypotheses[k].confidence
                new_c = state.hypotheses[k].confidence
                if old_c != new_c:
                    confidence_changes.append({
                        "title": state.hypotheses[k].title,
                        "old": old_c,
                        "new": new_c,
                    })
        new_contras = [
            state.contradictions[k].title
            for k in state.contradictions
            if k not in prior_contradictions
        ]

        result.steps.append(EvolveStep(
            name=step_name,
            subdir=subdir,
            files_added=ingest_report.sources_processed,
            pages_changed=ingest_report.pages_changed,
            new_hypotheses=new_hyps,
            confidence_changes=confidence_changes,
            new_contradictions=new_contras,
            lint_summary=lint_summary,
            eval_summary=eval_summary,
            key_question=key_question,
            key_assessment=key_assessment,
            snapshot_name=snapshot_name,
        ))
        result.snapshots.append(snapshot_name)

        prior_hypotheses = {k: deepcopy(h) for k, h in state.hypotheses.items()}
        prior_contradictions = set(state.contradictions)

    _write_evolution_report(project_root, result)
    return result


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _wipe_case(project_root: Path, case_id: str) -> None:
    cdir = case_dir(project_root, case_id)
    if cdir.exists():
        shutil.rmtree(cdir)
    sdir = snapshots_case_dir(project_root, case_id)
    if sdir.exists():
        shutil.rmtree(sdir)
    bdir = benchmark_case_dir(project_root, case_id)
    if bdir.exists():
        shutil.rmtree(bdir)


def _write_evolution_report(project_root: Path, result: EvolutionResult) -> None:
    bcd = benchmark_case_dir(project_root, result.case_id)
    bcd.mkdir(parents=True, exist_ok=True)
    (bcd / "evolution_report.md").write_text(format_evolution_report(result))


def format_evolution_report(result: EvolutionResult) -> str:
    out: list[str] = []
    out.append(f"# Case Evolution Report — `{result.case_id}`\n")
    out.append(
        "This report shows how the wiki's understanding of the case shifted "
        "as evidence arrived in sequence. Each step ingests one drop of "
        f"evidence; the key question tracked across steps is:\n\n"
        f"> {result.key_question}\n"
    )

    out.append("## Snapshots\n")
    for s in result.snapshots:
        out.append(f"- `wiki_snapshots/{result.case_id}/{s}/`")
    out.append("")

    for i, step in enumerate(result.steps, start=1):
        out.append(f"## Step {i}: `{step.name}`\n")
        if step.files_added:
            out.append("**Evidence added:**")
            for f in step.files_added:
                out.append(f"- `{f}`")
            out.append("")

        out.append("**Wiki pages changed:**")
        if step.pages_changed:
            for p in step.pages_changed:
                out.append(f"- `{p}`")
        else:
            out.append("- _(no markdown pages changed)_")
        out.append("")

        out.append("**Hypothesis changes:**")
        if step.new_hypotheses:
            for h in step.new_hypotheses:
                out.append(f"- New: {h}")
        if step.confidence_changes:
            for c in step.confidence_changes:
                out.append(
                    f"- Confidence changed: {c['title']} "
                    f"({c['old']} → {c['new']})"
                )
        if not step.new_hypotheses and not step.confidence_changes:
            out.append("- _(no hypothesis changes)_")
        out.append("")

        out.append("**Contradictions added:**")
        if step.new_contradictions:
            for c in step.new_contradictions:
                out.append(f"- {c}")
        else:
            out.append("- _(none)_")
        out.append("")

        out.append("**Lint findings:**")
        ls = step.lint_summary
        out.append(
            f"- critical={ls.get('critical', 0)} "
            f"high={ls.get('high', 0)} "
            f"medium={ls.get('medium', 0)} "
            f"low={ls.get('low', 0)}"
        )
        out.append("")

        if step.eval_summary is not None:
            es = step.eval_summary
            out.append("**Eval after this step:**")
            out.append(
                f"- {es.passed}/{es.total} passed "
                f"(unsupported-claim failures: {es.unsupported_claim_failures}, "
                f"missing-source failures: {es.missing_source_failures})"
            )
            out.append("")

        out.append("**Assessment after this step:**")
        out.append(f"> {step.key_assessment}")
        out.append("")

    return "\n".join(out)
