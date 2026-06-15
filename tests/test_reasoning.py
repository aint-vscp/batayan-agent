"""Behavioural tests for the Batayan offline reasoning engine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from batayan.evaluate import default_dataset, run
from batayan.knowledge import load_all_knowledge_bases, knowledge_root
from batayan.reasoner import decide
from batayan.schema import Profile, RuleVerdict, Verdict

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def bases():
    return load_all_knowledge_bases()


def _profile(name: str) -> Profile:
    data = json.loads((REPO / "examples" / name).read_text(encoding="utf-8"))
    return Profile.from_dict(data)


def _resolve(bases, query):
    for kb in bases.values():
        p = kb.find_program(query)
        if p:
            return kb, p
    raise AssertionError(f"program not found: {query}")


def test_eligible_with_full_citations(bases):
    kb, program = _resolve(bases, "DOST-SEI")
    result = decide(kb, program, _profile("liza.json"))
    assert result.verdict is Verdict.ELIGIBLE
    # Every decisive rule must carry a grounded citation with an as_of stamp.
    for o in result.decisive_outcomes:
        assert o.verdict is RuleVerdict.PASS
        assert o.citation is not None and o.citation.grounded
        assert o.citation.as_of
    assert result.coverage == 1.0


def test_ineligible_isolates_the_failing_rule(bases):
    kb, program = _resolve(bases, "DOST-SEI")
    result = decide(kb, program, _profile("mateo.json"))
    assert result.verdict is Verdict.INELIGIBLE
    failed = result.failed
    assert [o.rule_id for o in failed] == ["financial_need"]
    # Failure must come with a concrete fix and a citation (a denial with a receipt).
    assert failed[0].remediation
    assert failed[0].citation and failed[0].citation.grounded


def test_abstains_when_evidence_missing(bases):
    kb, program = _resolve(bases, "DOST-SEI")
    result = decide(kb, program, _profile("aisha.json"))
    assert result.verdict is Verdict.INSUFFICIENT_EVIDENCE
    assert result.missing_evidence
    assert result.coverage < 1.0


def test_same_engine_different_knowledge_base(bases):
    kb, program = _resolve(bases, "parental leave")
    result = decide(kb, program, _profile("employee-ramon.json"))
    assert result.verdict is Verdict.ELIGIBLE
    assert result.knowledge_base == "hr-leave"


def test_grounding_rejects_tampered_quote(bases):
    """If a cited quote is not actually in the source, it must not be trusted."""
    kb, program = _resolve(bases, "DOST-SEI")
    rule = program.rules[0]
    object.__setattr__(rule.cites, "quote", "this sentence does not exist in the source")
    result = decide(kb, program, _profile("liza.json"))
    # An ungrounded decisive rule collapses the verdict to abstention, never a guess.
    assert result.verdict is Verdict.INSUFFICIENT_EVIDENCE


def test_eval_set_is_fully_correct():
    report = run(default_dataset())
    assert report["accuracy"] == 1.0, report["rows"]
    assert report["abstention_recall"] == 1.0
    assert report["denial_precision"] == 1.0


def test_knowledge_root_exists():
    assert (knowledge_root() / "scholarships" / "manifest.json").exists()
