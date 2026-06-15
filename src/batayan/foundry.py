"""Foundry mode — Microsoft Foundry Agent Service + Foundry IQ integration.

This is the cloud path. It is **env-gated** and imported lazily so the offline demo
never depends on Azure. The offline engine in :mod:`batayan.reasoner` mirrors the
*same* decompose → retrieve → ground → decide loop and returns the *same*
``ReasoningResult`` schema, so everything the README claims is true in both modes.

What this does, mapped to the hackathon requirements:

* **Microsoft Foundry (track tool)** — creates a reasoning agent on the Foundry
  Agent Service and runs a multi-step thread that decomposes the eligibility
  question into atomic rules and decides per-rule.
* **Foundry IQ (required IQ layer)** — binds a Knowledge Base so retrieval is
  *agentic*, *permission-aware*, and returns *extractive citations* (source +
  section + ``as_of``) that populate each rule's evidence.

References:
  - Foundry IQ: https://learn.microsoft.com/azure/foundry/agents/concepts/foundry-iq-faq
  - Foundry Agent Service / Microsoft Agent Framework (Azure AI Foundry).

Configure via environment (see ``.env.example``):
  AZURE_AI_PROJECT_ENDPOINT   - your Foundry project endpoint
  AZURE_AI_MODEL_DEPLOYMENT   - chat model deployment name (e.g. gpt-4o)
  FOUNDRY_IQ_KNOWLEDGE_BASE   - Foundry IQ knowledge base id (overrides manifest)
"""

from __future__ import annotations

import json
import os
import textwrap

from .knowledge import KnowledgeBase, Program
from .schema import (
    Citation,
    Profile,
    ReasoningResult,
    RuleOutcome,
    RuleVerdict,
    Verdict,
)

AGENT_INSTRUCTIONS = textwrap.dedent(
    """
    You are Batayan, a grounded eligibility-reasoning agent. You decide whether a
    subject is ELIGIBLE, INELIGIBLE, or whether there is INSUFFICIENT_EVIDENCE for
    a program, and you PROVE every claim with a citation retrieved from the bound
    Foundry IQ knowledge base.

    Hard rules:
    1. Decompose the program's eligibility into atomic rules. Evaluate each rule
       independently against the subject's attributes.
    2. For every rule you rely on, you MUST cite the exact source passage returned
       by Foundry IQ (source file, section, and the rule's effective `as_of` date).
       Never assert a requirement you cannot cite.
    3. If a decisive rule cannot be grounded in the knowledge base, OR the subject
       has not provided the attribute needed to evaluate it, mark that rule
       INSUFFICIENT_EVIDENCE and return an overall verdict of INSUFFICIENT_EVIDENCE.
       Abstaining is correct behaviour — do NOT guess.
    4. Return INELIGIBLE only when at least one decisive rule is grounded AND
       evaluated AND fails. List which rule(s) failed and the single fix for each.
    5. Return ELIGIBLE only when every decisive rule is grounded, evaluated, and
       satisfied.

    Respond ONLY with strict JSON matching this schema:
    {
      "verdict": "ELIGIBLE | INELIGIBLE | INSUFFICIENT_EVIDENCE",
      "summary": "one sentence",
      "outcomes": [
        {
          "rule_id": "string",
          "description": "string",
          "decisive": true,
          "verdict": "PASS | FAIL | INSUFFICIENT_EVIDENCE",
          "explanation": "string",
          "remediation": "string or null",
          "citation": {"source": "string", "section": "string",
                       "quote": "string", "as_of": "YYYY-MM-DD"}
        }
      ],
      "missing_evidence": ["string", ...]
    }
    """
).strip()


class FoundryNotConfigured(RuntimeError):
    """Raised when Foundry mode is requested but env/SDK are unavailable."""


def _require_env() -> tuple[str, str]:
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    model = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT")
    if not endpoint or not model:
        raise FoundryNotConfigured(
            "Foundry mode needs AZURE_AI_PROJECT_ENDPOINT and "
            "AZURE_AI_MODEL_DEPLOYMENT (see .env.example). "
            "Use the default offline engine to run without Azure."
        )
    return endpoint, model


def _build_prompt(program: Program, profile: Profile, kb_id: str) -> str:
    return textwrap.dedent(
        f"""
        Program: {program.name}
        Foundry IQ knowledge base: {kb_id}
        Decision subject: {program.decision_subject}

        Subject attributes (JSON):
        {json.dumps({"name": profile.name, **dict(profile.attributes)}, indent=2)}

        Decompose the program's eligibility rules, retrieve each rule's basis from
        the knowledge base, evaluate it against the subject, and return the strict
        JSON verdict described in your instructions.
        """
    ).strip()


def _parse_agent_json(raw: str, program: Program, profile: Profile, kb_id: str) -> ReasoningResult:
    # Models occasionally wrap JSON in prose/markdown fences — extract defensively.
    start, end = raw.find("{"), raw.rfind("}")
    payload = json.loads(raw[start : end + 1]) if start != -1 and end != -1 else json.loads(raw)

    outcomes: list[RuleOutcome] = []
    for o in payload.get("outcomes", []):
        cit = o.get("citation")
        citation = (
            Citation(
                source=cit.get("source", ""), section=cit.get("section", ""),
                quote=cit.get("quote", ""), as_of=cit.get("as_of", ""),
                grounded=True,
            )
            if cit
            else None
        )
        outcomes.append(
            RuleOutcome(
                rule_id=o.get("rule_id", ""),
                description=o.get("description", ""),
                decisive=bool(o.get("decisive", True)),
                verdict=RuleVerdict(o.get("verdict", "INSUFFICIENT_EVIDENCE")),
                explanation=o.get("explanation", ""),
                citation=citation,
                remediation=o.get("remediation"),
            )
        )
    return ReasoningResult(
        question=f"Is {profile.name} eligible for {program.name}?",
        program=program.name,
        verdict=Verdict(payload.get("verdict", "INSUFFICIENT_EVIDENCE")),
        summary=payload.get("summary", ""),
        outcomes=outcomes,
        missing_evidence=payload.get("missing_evidence", []),
        engine="foundry",
        knowledge_base=kb_id,
    )


def decide_with_foundry(kb: KnowledgeBase, program: Program, profile: Profile,
                        question: str = "") -> ReasoningResult:
    """Run the decision on Foundry Agent Service, grounded by Foundry IQ.

    Raises :class:`FoundryNotConfigured` with actionable guidance if the Azure SDK
    or environment is missing — callers can fall back to the offline engine.
    """
    endpoint, model = _require_env()
    kb_id = os.environ.get("FOUNDRY_IQ_KNOWLEDGE_BASE") or _kb_id_from_manifest(kb)

    try:
        from azure.ai.projects import AIProjectClient  # type: ignore
        from azure.identity import DefaultAzureCredential  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only in Foundry mode
        raise FoundryNotConfigured(
            "Azure SDK not installed. Run `pip install batayan-agent[foundry]` "
            "(azure-ai-projects, azure-identity) to enable Foundry mode."
        ) from exc

    client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())

    # The Foundry IQ knowledge base is attached as the agent's grounded retrieval
    # tool. Tool wiring follows the Foundry Agent Service knowledge-tool pattern;
    # the knowledge base id resolves to a registered Foundry IQ knowledge source.
    agent = client.agents.create_agent(
        model=model,
        name="batayan-reasoner",
        instructions=AGENT_INSTRUCTIONS,
        tools=[{"type": "foundry_iq", "knowledge_base": kb_id}],
    )
    try:
        thread = client.agents.threads.create()
        client.agents.messages.create(
            thread_id=thread.id, role="user",
            content=_build_prompt(program, profile, kb_id),
        )
        run = client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
        if getattr(run, "status", "") == "failed":
            raise FoundryNotConfigured(f"Foundry run failed: {getattr(run, 'last_error', '')}")
        messages = client.agents.messages.list(thread_id=thread.id)
        raw = _last_assistant_text(messages)
        return _parse_agent_json(raw, program, profile, kb_id)
    finally:
        try:
            client.agents.delete_agent(agent.id)
        except Exception:  # pragma: no cover - best-effort cleanup
            pass


def _kb_id_from_manifest(kb: KnowledgeBase) -> str:
    import json as _json

    manifest = kb.root / "manifest.json"
    if manifest.exists():
        data = _json.loads(manifest.read_text(encoding="utf-8"))
        return data.get("foundry_iq_knowledge_base", kb.name)
    return kb.name


def _last_assistant_text(messages) -> str:  # pragma: no cover - SDK shape varies
    """Extract the latest assistant text across plausible SDK message shapes."""
    items = list(getattr(messages, "data", messages))
    for msg in reversed(items):
        if getattr(msg, "role", "") != "assistant":
            continue
        content = getattr(msg, "content", msg)
        if isinstance(content, str):
            return content
        for part in content:
            text = getattr(getattr(part, "text", None), "value", None)
            if text:
                return text
            if isinstance(part, dict):
                t = part.get("text", {})
                if isinstance(t, dict) and t.get("value"):
                    return t["value"]
    raise FoundryNotConfigured("No assistant response returned by the Foundry agent.")
