"""Pydantic models for everything the LLM proposes and everything the wiki stores.

The LLM never writes files directly. It returns instances of these models,
which are validated and then committed to markdown by `wiki_io.py`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Confidence = Literal["Low", "Medium", "High", "Confirmed"]
Severity = Literal["Critical", "High", "Medium", "Low"]
Classification = Literal["fact", "inference", "hypothesis"]
ClaimType = Literal["hypothesis", "ioc", "fact", "observation"]
EntityType = Literal[
    "process", "file", "user", "host", "ip", "domain",
    "registry_key", "command", "hash", "url", "other",
]


class Citation(BaseModel):
    """A pointer back to a raw source file or another wiki page."""

    kind: Literal["source", "evidence"]
    target: str  # e.g. "raw_sources/case_001/powershell_history.txt" or "[[timeline]]"
    note: str | None = None

    def render(self) -> str:
        if self.kind == "source":
            return f"Source: {self.target}"
        suffix = f" → {self.note}" if self.note else ""
        return f"Evidence: {self.target}{suffix}"


class Entity(BaseModel):
    """A process, file, user, IP, hash, etc. observed in evidence."""

    type: EntityType
    value: str
    appears_in: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)

    @property
    def key(self) -> str:
        """Canonical identifier used for dedup."""
        return f"{self.type}:{self.value.lower()}"

    @property
    def heading(self) -> str:
        return f"{self.type}: {self.value}"


class Event(BaseModel):
    """A single timeline entry."""

    timestamp: str | None = None  # ISO 8601 or "unknown"
    description: str
    citation: Citation

    @field_validator("timestamp")
    @classmethod
    def _normalise_timestamp(cls, v: str | None) -> str | None:
        if v is None or v == "" or v.lower() == "unknown":
            return "unknown"
        return v


class IOC(BaseModel):
    """An indicator of compromise or suspicious artifact."""

    artifact: str
    type: EntityType
    first_seen: str = "unknown"
    source: str
    confidence: Confidence = "Low"
    reason: str
    related: list[str] = Field(default_factory=list)


class Hypothesis(BaseModel):
    """An investigation hypothesis with facts and inferences kept separate."""

    title: str
    confidence: Confidence
    facts: list[str] = Field(default_factory=list)
    inference: str = ""
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class Contradiction(BaseModel):
    """Two pieces of evidence that disagree."""

    title: str
    claim_a: str
    claim_b: str
    status: str = "Unresolved"


class ExtractedFacts(BaseModel):
    """Everything pulled from a single raw source file."""

    source_path: str
    entities: list[Entity] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    iocs: list[IOC] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class WikiUpdate(BaseModel):
    """The merged set of changes applied to a case wiki during one ingest."""

    case_id: str
    extracted: list[ExtractedFacts] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")

    @property
    def all_entities(self) -> list[Entity]:
        return [e for batch in self.extracted for e in batch.entities]

    @property
    def all_events(self) -> list[Event]:
        return [e for batch in self.extracted for e in batch.events]

    @property
    def all_iocs(self) -> list[IOC]:
        return [i for batch in self.extracted for i in batch.iocs]

    @property
    def all_hypotheses(self) -> list[Hypothesis]:
        return [h for batch in self.extracted for h in batch.hypotheses]

    @property
    def all_contradictions(self) -> list[Contradiction]:
        return [c for batch in self.extracted for c in batch.contradictions]

    @property
    def all_open_questions(self) -> list[str]:
        return [q for batch in self.extracted for q in batch.open_questions]


class QueryAnswer(BaseModel):
    """A structured answer produced by the query operation."""

    question: str
    answer: str
    classification: Classification
    confidence: Confidence
    assessment: str = ""
    supporting_pages: list[str] = Field(default_factory=list)
    supporting_sources: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    evidence_items: list[str] = Field(default_factory=list)  # e.g. "claim_0001: ..."
    insufficient: bool = False
    fell_back_to_raw_sources: bool = False


class LintFinding(BaseModel):
    """A single lint observation."""

    rule: str  # e.g. "H1"
    severity: Severity
    page: str
    message: str


class LintReport(BaseModel):
    findings: list[LintFinding] = Field(default_factory=list)
    case_id: str = ""
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")

    def by_severity(self, sev: Severity) -> list[LintFinding]:
        return [f for f in self.findings if f.severity == sev]

    def is_clean(self) -> bool:
        return not self.findings

    def summary(self) -> dict[str, int]:
        return {
            "critical": len(self.by_severity("Critical")),
            "high": len(self.by_severity("High")),
            "medium": len(self.by_severity("Medium")),
            "low": len(self.by_severity("Low")),
        }


# --------------------------------------------------------------------------- #
# Phase 2: Source manifest
# --------------------------------------------------------------------------- #


class ManifestEntry(BaseModel):
    source_path: str
    sha256: str
    last_ingested_at: str
    status: Literal["processed", "skipped", "error", "pending"] = "processed"
    pages_touched: list[str] = Field(default_factory=list)


class Manifest(BaseModel):
    case_id: str
    schema_version: str = "v1"
    sources: list[ManifestEntry] = Field(default_factory=list)
    last_full_lint_at: str | None = None
    last_ingest_at: str | None = None

    def by_path(self) -> dict[str, ManifestEntry]:
        return {e.source_path: e for e in self.sources}

    def upsert(self, entry: ManifestEntry) -> None:
        for i, existing in enumerate(self.sources):
            if existing.source_path == entry.source_path:
                self.sources[i] = entry
                return
        self.sources.append(entry)


# --------------------------------------------------------------------------- #
# Phase 2: Structured indexes (events.json / entities.json / claims.json)
# --------------------------------------------------------------------------- #


class IndexedEvent(BaseModel):
    event_id: str  # e.g. "evt_0001"
    timestamp: str = "unknown"
    event_type: str
    description: str
    source_path: str
    evidence_text: str = ""
    confidence: Confidence = "Medium"


class IndexedEntity(BaseModel):
    entity_id: str  # e.g. "ent_0001"
    entity_type: EntityType
    value: str
    source_paths: list[str] = Field(default_factory=list)
    related_pages: list[str] = Field(default_factory=list)


class IndexedClaimEvidence(BaseModel):
    source_path: str
    evidence_text: str


class IndexedClaim(BaseModel):
    claim_id: str  # e.g. "claim_0001"
    claim_type: ClaimType
    claim_text: str
    confidence: Confidence = "Medium"
    supporting_evidence: list[IndexedClaimEvidence] = Field(default_factory=list)
    contradicting_evidence: list[IndexedClaimEvidence] = Field(default_factory=list)
    linked_pages: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Phase 2: Trace logging
# --------------------------------------------------------------------------- #


class TraceStep(BaseModel):
    step: str
    status: Literal["ok", "error", "skipped"] = "ok"
    duration_ms: int = 0
    detail: str | None = None


class TraceRecord(BaseModel):
    trace_id: str
    operation: str
    case_id: str
    source_path: str | None = None
    steps: list[TraceStep] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")


class IngestionLogEntry(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")
    case_id: str
    sources_processed: list[str] = Field(default_factory=list)
    sources_skipped: list[str] = Field(default_factory=list)
    pages_written: list[str] = Field(default_factory=list)
    mode: str = "mock"
    dry_run: bool = False


# --------------------------------------------------------------------------- #
# Phase 2: Eval suite
# --------------------------------------------------------------------------- #


class EvalCase(BaseModel):
    id: str
    question: str
    expected_behavior: str = ""
    must_include: list[str] = Field(default_factory=list)
    must_not_include: list[str] = Field(default_factory=list)
    required_sources: list[str] = Field(default_factory=list)
    expect_refusal: bool = False
    expect_separation: bool = False  # answer must separate facts from hypotheses
    category: str = "general"  # Phase 3: bucket for benchmark grouping
    expected_best_method: str = ""  # Phase 5: raw_rag | graph_rag_lite | llm_wiki | hybrid


class EvalCheck(BaseModel):
    name: str
    passed: bool
    detail: str = ""


class EvalCaseResult(BaseModel):
    id: str
    question: str
    passed: bool
    checks: list[EvalCheck] = Field(default_factory=list)
    answer_text: str = ""


class EvalSummary(BaseModel):
    total: int
    passed: int
    failed: int
    unsupported_claim_failures: int = 0
    missing_source_failures: int = 0
    results: list[EvalCaseResult] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Phase 3: Hypothesis history, evolution, benchmark
# --------------------------------------------------------------------------- #


class HypothesisSnapshot(BaseModel):
    step: str
    confidence: str  # lower-cased confidence string for output parity with spec
    assessment: str = ""
    supporting_count: int = 0
    contradicting_count: int = 0


class HypothesisHistoryItem(BaseModel):
    hypothesis: str
    claim_id: str = ""
    history: list[HypothesisSnapshot] = Field(default_factory=list)


class HypothesisHistory(BaseModel):
    case_id: str
    histories: list[HypothesisHistoryItem] = Field(default_factory=list)

    def by_title(self) -> dict[str, HypothesisHistoryItem]:
        return {h.hypothesis.lower(): h for h in self.histories}


class EvolveStep(BaseModel):
    name: str
    subdir: str
    files_added: list[str] = Field(default_factory=list)
    pages_changed: list[str] = Field(default_factory=list)
    new_hypotheses: list[str] = Field(default_factory=list)
    confidence_changes: list[dict] = Field(default_factory=list)  # {title, old, new}
    new_contradictions: list[str] = Field(default_factory=list)
    lint_summary: dict = Field(default_factory=dict)
    eval_summary: EvalSummary | None = None
    key_question: str = ""
    key_assessment: str = ""
    snapshot_name: str = ""


class EvolutionResult(BaseModel):
    case_id: str
    key_question: str
    steps: list[EvolveStep] = Field(default_factory=list)
    snapshots: list[str] = Field(default_factory=list)


class BenchmarkRow(BaseModel):
    question_id: str
    question: str
    category: str = ""
    wiki_passed: bool
    rag_passed: bool
    wiki_checks: list[EvalCheck] = Field(default_factory=list)
    rag_checks: list[EvalCheck] = Field(default_factory=list)
    wiki_answer: str = ""
    rag_answer: str = ""
    wiki_unsupported_failures: int = 0
    rag_unsupported_failures: int = 0
    wiki_missing_source_failures: int = 0
    rag_missing_source_failures: int = 0


class BenchmarkSummary(BaseModel):
    case_id: str
    total: int
    wiki_passed: int
    wiki_failed: int
    rag_passed: int
    rag_failed: int
    wiki_unsupported_failures: int = 0
    rag_unsupported_failures: int = 0
    wiki_missing_source_failures: int = 0
    rag_missing_source_failures: int = 0
    wiki_contradiction_misses: int = 0
    rag_contradiction_misses: int = 0
    wiki_refusal_accuracy: float = 0.0  # 0..1
    rag_refusal_accuracy: float = 0.0  # 0..1
    rows: list[BenchmarkRow] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Phase 5: GraphRAG-lite + four-way method comparison
# --------------------------------------------------------------------------- #


GraphNodeType = Literal[
    "process", "file", "registry_key", "ip_address", "domain", "user",
    "command", "source", "claim", "hypothesis", "other",
]


EdgeType = Literal[
    "appears_in", "spawned", "references", "connected_to",
    "supports", "contradicts", "mentioned_in", "related_to",
]


class GraphNode(BaseModel):
    id: str
    type: GraphNodeType
    label: str


class GraphEdge(BaseModel):
    source: str  # node id
    target: str  # node id
    type: EdgeType
    evidence: str | None = None  # raw_sources/... path if available


class Graph(BaseModel):
    case_id: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)

    def neighbors(self, node_id: str) -> list[tuple[GraphEdge, GraphNode]]:
        by_id = {n.id: n for n in self.nodes}
        out: list[tuple[GraphEdge, GraphNode]] = []
        for e in self.edges:
            if e.source == node_id and e.target in by_id:
                out.append((e, by_id[e.target]))
            elif e.target == node_id and e.source in by_id:
                # Treat as the inverse direction.
                out.append((e, by_id[e.source]))
        return out


Method = Literal["raw_rag", "vector_rag", "graph_rag_lite", "llm_wiki", "hybrid"]


class MethodRowCheck(BaseModel):
    method: Method
    passed: bool
    checks: list[EvalCheck] = Field(default_factory=list)
    unsupported_failures: int = 0
    missing_source_failures: int = 0
    answer: str = ""


class MethodBenchmarkRow(BaseModel):
    question_id: str
    question: str
    category: str = "general"
    expected_best_method: str = ""
    results: dict[str, MethodRowCheck] = Field(default_factory=dict)


class MethodBenchmarkSummary(BaseModel):
    case_id: str
    total: int
    per_method: dict[str, dict] = Field(default_factory=dict)
    # per_method[method] -> {
    #   passed, failed, unsupported_failures, missing_source_failures,
    #   refusal_accuracy, contradiction_misses, relationship_coverage,
    #   narrative_state_quality, expected_best_wins
    # }
    rows: list[MethodBenchmarkRow] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Phase 6: Human review queue
# --------------------------------------------------------------------------- #


ReviewStatus = Literal["pending", "approved", "rejected"]
ChangeType = Literal["wiki_update", "report_update", "other"]


class ReviewItem(BaseModel):
    review_id: str
    case_id: str
    change_type: ChangeType
    target_page: str
    reason: str = ""
    proposed_content: str
    prior_content: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z"
    )
    status: ReviewStatus = "pending"
    risky_phrases: list[str] = Field(default_factory=list)
    decided_at: str | None = None
    decided_reason: str = ""


class ReviewHistoryEntry(BaseModel):
    review_id: str
    case_id: str
    target_page: str
    action: Literal["created", "approved", "rejected"]
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z"
    )
    reason: str = ""


