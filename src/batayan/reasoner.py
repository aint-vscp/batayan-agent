"""The multi-step reasoning loop: decompose → retrieve → ground → decide.

This is the offline engine. It mirrors what Foundry Agent Service orchestrates and
Foundry IQ grounds in the cloud, but runs locally and deterministically so the
demo can be trusted on stage. The control flow is intentionally legible: a judge
should be able to read the resulting `ReasoningResult` like a court transcript.
"""

from __future__ import annotations

from .knowledge import KnowledgeBase, Program, Rule
from .schema import (
    Profile,
    ReasoningResult,
    RuleOutcome,
    RuleVerdict,
    Verdict,
)


class Reasoner:
    """Adjudicates an eligibility predicate over grounded evidence."""

    def __init__(self, kb: KnowledgeBase, engine: str = "offline") -> None:
        self.kb = kb
        self.engine = engine

    # -- public API --------------------------------------------------------
    def decide(self, program: Program, profile: Profile, question: str = "") -> ReasoningResult:
        question = question or f"Is {profile.name} eligible for {program.name}?"
        outcomes = [self._evaluate_rule(rule, profile) for rule in program.rules]
        result = ReasoningResult(
            question=question,
            program=program.name,
            verdict=Verdict.INSUFFICIENT_EVIDENCE,  # provisional until aggregated
            summary="",
            outcomes=outcomes,
            engine=self.engine,
            knowledge_base=self.kb.name,
        )
        self._aggregate(result, program, profile)
        return result

    # -- per-rule step -----------------------------------------------------
    def _evaluate_rule(self, rule: Rule, profile: Profile) -> RuleOutcome:
        # 1. Plan a retrieval query for this atomic rule.
        query = f"{rule.description} {rule.cites.section}".strip()

        # 2. Retrieve the most relevant chunk from the cited source (for the trace
        #    + a relevance score). Foundry IQ performs this step in cloud mode.
        if not self.kb.has_source(rule.cites.source):
            return RuleOutcome(
                rule_id=rule.id, description=rule.description, decisive=rule.decisive,
                verdict=RuleVerdict.INSUFFICIENT_EVIDENCE, query=query,
                explanation=f"No source '{rule.cites.source}' found in knowledge base.",
            )
        hits = self.kb.retrieve(query, source=rule.cites.source, k=1)
        score = hits[0][1] if hits else 0.0

        # 3. Ground the claim: the cited quote MUST exist in the cited source.
        citation = self.kb.ground(rule.cites, score=score)
        if not citation.grounded:
            return RuleOutcome(
                rule_id=rule.id, description=rule.description, decisive=rule.decisive,
                verdict=RuleVerdict.INSUFFICIENT_EVIDENCE, query=query, citation=citation,
                explanation=(
                    "Cited text could not be verified in the source — refusing to "
                    "rely on ungrounded evidence."
                ),
            )

        # 4. Abstain if the applicant has not provided the field this rule needs.
        if not profile.has(rule.required_field):
            return RuleOutcome(
                rule_id=rule.id, description=rule.description, decisive=rule.decisive,
                verdict=RuleVerdict.INSUFFICIENT_EVIDENCE, query=query, citation=citation,
                explanation=(
                    f"Cannot evaluate: applicant did not provide "
                    f"'{rule.required_field}'."
                ),
                remediation=f"Provide '{rule.required_field}' to complete this check.",
            )

        # 5. Evaluate the predicate against grounded evidence.
        actual = profile.get(rule.required_field)
        passed = rule.predicate.evaluate(actual)
        return RuleOutcome(
            rule_id=rule.id, description=rule.description, decisive=rule.decisive,
            verdict=RuleVerdict.PASS if passed else RuleVerdict.FAIL,
            query=query, citation=citation,
            explanation=("Satisfied: " if passed else "Not satisfied: ")
            + rule.predicate.describe(actual),
            remediation=None if passed else (rule.remediation or "Does not meet this requirement."),
        )

    # -- aggregation with coverage gating ---------------------------------
    def _aggregate(self, result: ReasoningResult, program: Program, profile: Profile) -> None:
        decisive = result.decisive_outcomes
        unprovable = [o for o in decisive if o.verdict is RuleVerdict.INSUFFICIENT_EVIDENCE]
        failed = [o for o in decisive if o.verdict is RuleVerdict.FAIL]
        passed = [o for o in decisive if o.verdict is RuleVerdict.PASS]

        # Gate: a confident verdict requires every decisive rule to be grounded
        # and evaluable. Otherwise Batayan abstains rather than guess.
        if unprovable:
            result.verdict = Verdict.INSUFFICIENT_EVIDENCE
            result.missing_evidence = [
                (o.remediation or o.explanation) for o in unprovable
            ]
            result.summary = (
                f"Cannot decide {program.decision_subject} for {profile.name}: "
                f"{len(unprovable)} of {len(decisive)} decisive rule(s) could not be "
                f"grounded or evaluated. Abstaining instead of guessing."
            )
            return

        if failed:
            result.verdict = Verdict.INELIGIBLE
            reasons = "; ".join(f"{o.rule_id}" for o in failed)
            result.summary = (
                f"{profile.name} is INELIGIBLE for {program.name}. "
                f"Fails {len(failed)} rule(s): {reasons}. "
                f"All {len(decisive)} decisive rules were grounded and checked."
            )
            return

        result.verdict = Verdict.ELIGIBLE
        result.summary = (
            f"{profile.name} is ELIGIBLE for {program.name}. "
            f"All {len(passed)} decisive rules are satisfied and individually cited."
        )


def decide(kb: KnowledgeBase, program: Program, profile: Profile,
           question: str = "", engine: str = "offline") -> ReasoningResult:
    """Convenience wrapper used by the CLI and the evaluation harness."""
    return Reasoner(kb, engine=engine).decide(program, profile, question)
