# Safety & reliability model

Batayan is designed around one principle: **never assert a verdict you cannot
cite, and abstain rather than guess.** This document records the specific failure
modes it defends against and how each defense is verified.

## Threats and defenses

### 1. Hallucinated verdicts
A language model will happily invent an eligibility rule. Batayan structurally
prevents this: a decisive rule contributes to a confident verdict **only if its
cited quote is verified to exist in the source**. Ungrounded evidence collapses the
verdict to `INSUFFICIENT_EVIDENCE`.
*Verified by:* `tests/test_reasoning.py::test_grounding_rejects_tampered_quote`.

### 2. Confidently wrong denials
Telling someone "you don't qualify" when they do is a real harm. Every `INELIGIBLE`
verdict names the exact failing rule and attaches its citation and a remediation.
We measure **denial precision** on the eval set (currently 100%).
*Verified by:* `batayan eval` (denial precision metric).

### 3. Guessing on missing data
If the applicant hasn't supplied a fact a rule needs, Batayan does **not** assume a
default — it abstains for that rule, and the coverage gate turns the overall verdict
into `INSUFFICIENT_EVIDENCE` with an explicit "still needed" list.
*Verified by:* `test_abstains_when_evidence_missing` and the eval **abstention
recall** metric (currently 100%).

### 4. Stale rules
Eligibility rules change yearly. Every citation carries an **`as_of`** date, so a
verdict can be audited against the exact rule version that produced it.

### 5. Over-permissioned retrieval
In Foundry mode, retrieval is delegated to **Foundry IQ**, which enforces
permission-aware access (Microsoft Purview sensitivity labels) so the agent only
grounds on content the end user is authorized to see.

### 6. Opaque reasoning
A verdict you can't inspect can't be trusted. The CLI renders the full **evidence
ledger** — plan, per-rule query, retrieved source, grounded quote, predicate check,
coverage gate, verdict — so a human can audit every step.

## What Batayan is *not*

- It is **not** a source of truth. The bundled rulebooks are simplified and
  illustrative for the demo. In production, the knowledge base would point at the
  authoritative rulebooks via Foundry IQ.
- It is **not** a final decision-maker for high-stakes outcomes. It is a
  *grounded reasoning and triage* layer: it proves what the rules say and where a
  case stands, and it abstains when it cannot. Human review remains in the loop for
  contested or high-impact decisions.

## Evaluation as a gate

`batayan eval` runs the labelled set and exits non-zero on any error, so reliability
is enforced in CI (`.github/workflows/ci.yml`) — not just asserted in prose.
