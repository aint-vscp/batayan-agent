"""The reasoning contract shared by every Batayan run mode.

The whole project hangs off this module. Both the offline engine and the Foundry
Agent Service / Foundry IQ integration must return a `ReasoningResult`, so the CLI,
the evaluation harness, and the README can describe one honest behaviour
regardless of where the retrieval happened.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping


class Verdict(str, Enum):
    """The three — not two — possible outcomes of an eligibility decision.

    The presence of ``INSUFFICIENT_EVIDENCE`` as a first-class, native outcome is
    Batayan's core safety property: the agent abstains instead of guessing when it
    cannot ground a decisive rule.
    """

    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class RuleVerdict(str, Enum):
    """Per-rule outcome inside the larger decision."""

    PASS = "PASS"
    FAIL = "FAIL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class Citation:
    """A receipt. Every claim Batayan makes points at one of these.

    ``as_of`` stamps the *version* of the rule that was used, so a verdict stays
    auditable even after a rulebook changes the following year.
    """

    source: str
    section: str
    quote: str
    as_of: str
    retrieval_score: float = 0.0
    grounded: bool = True

    def short(self) -> str:
        return f"{self.source} § {self.section} (as of {self.as_of})"


@dataclass
class RuleOutcome:
    """The evaluation of a single atomic rule, with its supporting evidence."""

    rule_id: str
    description: str
    decisive: bool
    verdict: RuleVerdict
    # Human-readable explanation of *why* this rule passed/failed/abstained.
    explanation: str
    citation: Citation | None = None
    # The retrieval query the agent issued for this rule (shown in the trace).
    query: str = ""
    # Concrete next step when the rule fails (turns a "no" into an action list).
    remediation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["verdict"] = self.verdict.value
        return data


@dataclass
class ReasoningResult:
    """The full, inspectable record of one decision — the 'evidence ledger'."""

    question: str
    program: str
    verdict: Verdict
    summary: str
    outcomes: list[RuleOutcome] = field(default_factory=list)
    # What is still needed to reach a confident verdict (drives abstention UX).
    missing_evidence: list[str] = field(default_factory=list)
    # Which engine produced this result: "offline" or "foundry".
    engine: str = "offline"
    knowledge_base: str = ""

    # --- derived helpers -------------------------------------------------
    @property
    def decisive_outcomes(self) -> list[RuleOutcome]:
        return [o for o in self.outcomes if o.decisive]

    @property
    def failed(self) -> list[RuleOutcome]:
        return [o for o in self.outcomes if o.verdict is RuleVerdict.FAIL]

    @property
    def unprovable(self) -> list[RuleOutcome]:
        return [
            o
            for o in self.outcomes
            if o.verdict is RuleVerdict.INSUFFICIENT_EVIDENCE
        ]

    @property
    def coverage(self) -> float:
        """Fraction of decisive rules that could be grounded and evaluated."""
        decisive = self.decisive_outcomes
        if not decisive:
            return 0.0
        provable = [
            o for o in decisive if o.verdict is not RuleVerdict.INSUFFICIENT_EVIDENCE
        ]
        return len(provable) / len(decisive)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "program": self.program,
            "verdict": self.verdict.value,
            "summary": self.summary,
            "coverage": round(self.coverage, 3),
            "engine": self.engine,
            "knowledge_base": self.knowledge_base,
            "missing_evidence": self.missing_evidence,
            "outcomes": [o.to_dict() for o in self.outcomes],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


@dataclass
class Profile:
    """The applicant / subject the decision is made about.

    Deliberately a thin wrapper over a mapping: a missing field is the signal that
    drives abstention, so we never silently coerce absence into a default.
    """

    name: str
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def has(self, field_name: str) -> bool:
        return field_name in self.attributes and self.attributes[field_name] is not None

    def get(self, field_name: str) -> Any:
        return self.attributes.get(field_name)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Profile":
        attrs = dict(data)
        name = str(attrs.pop("name", "Applicant"))
        return cls(name=name, attributes=attrs)
