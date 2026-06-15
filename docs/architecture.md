# Architecture

Batayan is a **grounded, multi-step eligibility-reasoning agent**. This document
explains the reasoning loop, the data model, and how the offline engine maps onto
Microsoft Foundry Agent Service + Foundry IQ.

## The one contract: `ReasoningResult`

Everything in Batayan exists to produce one inspectable object (`src/batayan/schema.py`):

- `verdict ∈ {ELIGIBLE, INELIGIBLE, INSUFFICIENT_EVIDENCE}` — three classes, not two.
- `outcomes: list[RuleOutcome]` — one per atomic rule, each with:
  - a `RuleVerdict ∈ {PASS, FAIL, INSUFFICIENT_EVIDENCE}`,
  - a `Citation` (source, section, quote, **`as_of`**, retrieval score, `grounded` flag),
  - a plain-language `explanation` and, on failure, a concrete `remediation`.
- `missing_evidence` — what is still needed to reach a confident verdict.
- `coverage` — fraction of decisive rules that could be grounded and evaluated.

Both run modes return this same object, so the CLI, the eval harness, and the
README describe one honest behaviour regardless of where retrieval happened.

## The reasoning loop

```
decompose → retrieve → ground → evaluate → aggregate(coverage gate)
```

1. **Decompose** (`reasoner.py`). The program's eligibility is expressed as a set
   of *atomic rules*, each a predicate over one applicant field
   (`gwa ≥ 90`, `household_income_annual ≤ 400000`, `course ∈ {...}` …). Decomposing
   a compound "Am I eligible?" into independently-checkable rules is the reasoning
   step a plain RAG pipeline skips.

2. **Retrieve** (`knowledge.py`). For each rule, the agent issues a retrieval query
   and scores chunks of the cited source with a TF·IDF-style ranker (stdlib only,
   so it is deterministic and dependency-free). In Foundry mode this step is
   performed by **Foundry IQ**.

3. **Ground**. The cited quote must actually exist in the cited source (preferring
   the named section). If it cannot be verified, the rule is marked
   `INSUFFICIENT_EVIDENCE` — Batayan refuses to rely on ungrounded evidence. Each
   citation is stamped with the rule's `as_of` date for auditability.

4. **Evaluate**. The predicate is checked against the applicant's fact. If the
   applicant did not supply that fact, the rule abstains (`INSUFFICIENT_EVIDENCE`)
   rather than assuming a default.

5. **Aggregate with a coverage gate**:
   - any decisive rule unprovable → **`INSUFFICIENT_EVIDENCE`** (abstain; report what's missing);
   - else any decisive rule fails → **`INELIGIBLE`** (name the failing rule(s) + fix);
   - else → **`ELIGIBLE`** (every decisive rule satisfied and individually cited).

A confident verdict therefore *requires* 100% coverage of decisive rules. This is
the mechanism that makes "I don't know" the default when evidence is thin.

## Knowledge bases

A knowledge base is a directory under `knowledge/` containing:

- `manifest.json` — name, description, sources, and the `foundry_iq_knowledge_base`
  id used in Foundry mode.
- one or more prose rulebooks (`*.md`) — the **cited sources**, split into sections.
- one `*.rules.json` per program — the **atomic rules**, each linking a predicate to
  a `cites` block (source + section + exact `quote` + `as_of`).

Separating prose (what Foundry IQ retrieves and cites) from the structured
predicate (what the agent evaluates) keeps citations real: the quote in
`*.rules.json` must be present verbatim in the `*.md`, or grounding fails loudly.

## Mapping to Microsoft Foundry + Foundry IQ

| Batayan concept | Offline implementation | Foundry / Foundry IQ |
|---|---|---|
| Reasoning orchestration | `Reasoner` loop | **Foundry Agent Service** thread/run |
| Retrieval + citations | TF·IDF over local chunks + quote verification | **Foundry IQ** agentic, permission-aware retrieval with extractive citations |
| Knowledge base | `knowledge/<kb>/` directory | Foundry IQ **Knowledge Base** (id in `manifest.json`) |
| Permission scoping | n/a (local) | Foundry IQ honours Microsoft Purview sensitivity labels |
| Output | `ReasoningResult` | Agent returns strict JSON → parsed into the same `ReasoningResult` |

The Foundry integration lives in `src/batayan/foundry.py`, is imported lazily, and
is fully env-gated (`AZURE_AI_PROJECT_ENDPOINT`, `AZURE_AI_MODEL_DEPLOYMENT`,
`FOUNDRY_IQ_KNOWLEDGE_BASE`). The offline engine is the default so the demo never
depends on cloud connectivity.

### References
- Foundry IQ FAQ — https://learn.microsoft.com/azure/foundry/agents/concepts/foundry-iq-faq
- Microsoft Foundry Agent Service / Microsoft Agent Framework (Azure AI Foundry).
