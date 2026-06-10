"""Human review queue for risky wiki changes.

When ingest/report runs with ``--review``, anything that would write
a "confirmed malware", "exfiltration occurred", or similarly heavy
phrase to a wiki page is held back and dropped into the review queue
instead. A human runs ``fw.py review approve|reject`` to either commit
the proposed content or discard it.

Storage:

  - ``wiki/cases/<case_id>/.fw/review_queue/review_NNNN.json``
    One file per pending or decided review item.
  - ``wiki/cases/<case_id>/.fw/review_history.jsonl``
    Append-only audit log of every create / approve / reject.

This module is intentionally simple. There is no auth model and no
multi-reviewer workflow. The audit log exists so any decision is
recoverable from disk.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from .schemas import ReviewHistoryEntry, ReviewItem
from .wiki_io import case_dir, fw_dir

# --------------------------------------------------------------------------- #
# Risky-phrase detection
# --------------------------------------------------------------------------- #


RISKY_PHRASES: tuple[str, ...] = (
    "confirmed malware",
    "malware confirmed",
    "confirmed exfiltration",
    "exfiltration occurred",
    "exfiltration confirmed",
    "data was stolen",
    "confirmed compromise",
    "definitely malicious",
    "definite malware",
)

# Lines that *quote* the phrase rather than assert it are not risky.
_ATTRIBUTION_MARKERS = (
    "investigator", "analyst", "asserts", "alleges", "claims",
    "describes", "describe", "diagnosis", "note:", "notes:",
    "according to", "claim a:", "claim b:",
)


def scan_for_risky_phrases(content: str) -> list[str]:
    """Return every risky phrase that appears unattributed in the content.

    Attributed lines (investigator notes, claim_a / claim_b lines, etc.)
    are not flagged — the wiki is allowed to *quote* someone else's
    overclaim.
    """
    found: list[str] = []
    for line in content.splitlines():
        lower = line.lower()
        if any(m in lower for m in _ATTRIBUTION_MARKERS):
            continue
        for phrase in RISKY_PHRASES:
            if phrase in lower and phrase not in found:
                found.append(phrase)
    return found


# --------------------------------------------------------------------------- #
# Filesystem layout
# --------------------------------------------------------------------------- #


def review_queue_dir(project_root: Path, case_id: str) -> Path:
    return fw_dir(project_root, case_id) / "review_queue"


def review_history_path(project_root: Path, case_id: str) -> Path:
    return fw_dir(project_root, case_id) / "review_history.jsonl"


def review_path(project_root: Path, case_id: str, review_id: str) -> Path:
    return review_queue_dir(project_root, case_id) / f"{review_id}.json"


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #


def next_review_id(project_root: Path, case_id: str) -> str:
    qd = review_queue_dir(project_root, case_id)
    qd.mkdir(parents=True, exist_ok=True)
    existing = [p.stem for p in qd.glob("review_*.json")]
    n = 1
    while f"review_{n:04d}" in existing:
        n += 1
    return f"review_{n:04d}"


def create_review(
    project_root: Path,
    case_id: str,
    *,
    change_type: str,
    target_page: str,
    proposed_content: str,
    prior_content: str = "",
    reason: str = "",
    risky_phrases: list[str] | None = None,
) -> ReviewItem:
    rid = next_review_id(project_root, case_id)
    item = ReviewItem(
        review_id=rid,
        case_id=case_id,
        change_type=change_type,  # type: ignore[arg-type]
        target_page=target_page,
        reason=reason,
        proposed_content=proposed_content,
        prior_content=prior_content,
        risky_phrases=risky_phrases or scan_for_risky_phrases(proposed_content),
    )
    save_review(project_root, item)
    append_history(project_root, ReviewHistoryEntry(
        review_id=item.review_id,
        case_id=case_id,
        target_page=target_page,
        action="created",
        reason=reason,
    ))
    return item


def save_review(project_root: Path, item: ReviewItem) -> None:
    p = review_path(project_root, item.case_id, item.review_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(item.model_dump_json(indent=2))


def load_review(project_root: Path, case_id: str, review_id: str) -> ReviewItem:
    p = review_path(project_root, case_id, review_id)
    if not p.exists():
        raise FileNotFoundError(f"Review item not found: {p}")
    return ReviewItem.model_validate_json(p.read_text())


def list_reviews(
    project_root: Path,
    case_id: str,
    *,
    status: str | None = None,
) -> list[ReviewItem]:
    qd = review_queue_dir(project_root, case_id)
    if not qd.exists():
        return []
    items = [ReviewItem.model_validate_json(p.read_text())
             for p in sorted(qd.glob("review_*.json"))]
    if status is not None:
        items = [i for i in items if i.status == status]
    return items


def approve_review(
    project_root: Path,
    case_id: str,
    review_id: str,
    *,
    reason: str = "",
) -> ReviewItem:
    item = load_review(project_root, case_id, review_id)
    if item.status != "pending":
        raise RuntimeError(
            f"Review {review_id} is already {item.status}; cannot approve."
        )
    # Apply the proposed content to the target wiki page.
    target = case_dir(project_root, case_id) / item.target_page
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(item.proposed_content)
    item.status = "approved"
    item.decided_at = _now()
    item.decided_reason = reason
    save_review(project_root, item)
    append_history(project_root, ReviewHistoryEntry(
        review_id=item.review_id,
        case_id=case_id,
        target_page=item.target_page,
        action="approved",
        reason=reason,
    ))
    return item


def reject_review(
    project_root: Path,
    case_id: str,
    review_id: str,
    *,
    reason: str = "",
) -> ReviewItem:
    item = load_review(project_root, case_id, review_id)
    if item.status != "pending":
        raise RuntimeError(
            f"Review {review_id} is already {item.status}; cannot reject."
        )
    item.status = "rejected"
    item.decided_at = _now()
    item.decided_reason = reason
    save_review(project_root, item)
    append_history(project_root, ReviewHistoryEntry(
        review_id=item.review_id,
        case_id=case_id,
        target_page=item.target_page,
        action="rejected",
        reason=reason,
    ))
    return item


# --------------------------------------------------------------------------- #
# History
# --------------------------------------------------------------------------- #


def append_history(project_root: Path, entry: ReviewHistoryEntry) -> None:
    p = review_history_path(project_root, entry.case_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(entry.model_dump_json() + "\n")


def read_history(project_root: Path, case_id: str) -> list[ReviewHistoryEntry]:
    p = review_history_path(project_root, case_id)
    if not p.exists():
        return []
    out: list[ReviewHistoryEntry] = []
    for line in p.read_text().splitlines():
        if line.strip():
            out.append(ReviewHistoryEntry.model_validate(json.loads(line)))
    return out


# --------------------------------------------------------------------------- #
# Formatting helpers (CLI)
# --------------------------------------------------------------------------- #


def format_list(items: list[ReviewItem]) -> str:
    if not items:
        return "No review items recorded for this case."
    lines: list[str] = [f"{'ID':<14} {'STATUS':<10} {'PAGE':<24} REASON / RISKY"]
    lines.append("-" * 78)
    for it in items:
        risky = ", ".join(it.risky_phrases) or "—"
        reason = it.reason or risky
        lines.append(
            f"{it.review_id:<14} {it.status:<10} {it.target_page:<24} {reason[:30]}"
        )
    return "\n".join(lines)


def format_show(item: ReviewItem) -> str:
    return (
        f"Review {item.review_id} ({item.status})\n"
        f"Case:         {item.case_id}\n"
        f"Target page:  {item.target_page}\n"
        f"Change type:  {item.change_type}\n"
        f"Created at:   {item.created_at}\n"
        f"Risky phrases:{(' ' + ', '.join(item.risky_phrases)) if item.risky_phrases else ' (none detected)'}\n"
        f"Reason:       {item.reason or '(none)'}\n"
        + (f"Decided at:   {item.decided_at}\nDecided reason: {item.decided_reason or '(none)'}\n"
           if item.decided_at else "")
        + "\n--- proposed content ---\n"
        + item.proposed_content
    )


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


# --------------------------------------------------------------------------- #
# Used by ingest/report --review
# --------------------------------------------------------------------------- #


_PAGE_NAME_RE = re.compile(r"^[a-zA-Z0-9_./-]+$")


def is_safe_target_page(target_page: str) -> bool:
    """Cheap guard against absurd target_page values from agents/MCP."""
    if not target_page or ".." in target_page or target_page.startswith("/"):
        return False
    return bool(_PAGE_NAME_RE.match(target_page))
