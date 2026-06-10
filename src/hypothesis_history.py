"""Hypothesis-evolution history.

Persisted at ``wiki/cases/<case_id>/.fw/hypothesis_history.json``. The
``evolve`` command appends one snapshot per hypothesis per step, so we can
see in one place how each hypothesis's confidence and supporting/contradicting
counts shift as evidence arrives.

We deliberately keep this file separate from ``state.json``: state is the
*current* wiki, this file is the *trajectory*.
"""
from __future__ import annotations

from pathlib import Path

from .schemas import (
    HypothesisHistory,
    HypothesisHistoryItem,
    HypothesisSnapshot,
)
from .wiki_io import WikiState, fw_dir, hypothesis_key


def history_path(project_root: Path, case_id: str) -> Path:
    return fw_dir(project_root, case_id) / "hypothesis_history.json"


def load_history(project_root: Path, case_id: str) -> HypothesisHistory:
    p = history_path(project_root, case_id)
    if not p.exists():
        return HypothesisHistory(case_id=case_id)
    return HypothesisHistory.model_validate_json(p.read_text())


def save_history(project_root: Path, history: HypothesisHistory) -> None:
    p = history_path(project_root, history.case_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(history.model_dump_json(indent=2))


def update_history(
    project_root: Path,
    case_id: str,
    step_name: str,
    state: WikiState,
    *,
    assessment_by_title: dict[str, str] | None = None,
) -> HypothesisHistory:
    """Append a snapshot for every current hypothesis under this step."""
    history = load_history(project_root, case_id)
    history.case_id = case_id
    assessment_by_title = assessment_by_title or {}
    by_title = history.by_title()

    for _key, hyp in state.hypotheses.items():
        title_lower = hyp.title.lower()
        snapshot = HypothesisSnapshot(
            step=step_name,
            confidence=hyp.confidence.lower(),
            assessment=assessment_by_title.get(title_lower, ""),
            supporting_count=len(hyp.supporting_evidence),
            contradicting_count=len(hyp.contradicting_evidence),
        )
        item = by_title.get(title_lower)
        if item is None:
            item = HypothesisHistoryItem(
                hypothesis=hyp.title,
                claim_id=state.claim_ids.get(hypothesis_key(hyp), ""),
                history=[],
            )
            history.histories.append(item)
            by_title[title_lower] = item
        else:
            # Refresh the claim_id in case it was assigned after the first record.
            if not item.claim_id:
                item.claim_id = state.claim_ids.get(hypothesis_key(hyp), "")
        # Avoid duplicate same-step entries.
        if not any(s.step == step_name for s in item.history):
            item.history.append(snapshot)

    save_history(project_root, history)
    return history
