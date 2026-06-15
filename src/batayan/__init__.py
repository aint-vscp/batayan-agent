"""Batayan — a grounded, multi-step eligibility-reasoning agent.

Batayan decides what a person is *entitled* to and proves every verdict with the
exact rule and citation. It is built for the Microsoft Agents League "Reasoning
Agents" track on Microsoft Foundry, with Foundry IQ as the grounded, cited,
permission-aware knowledge-retrieval layer.

The package exposes one reasoning contract (`ReasoningResult`) that is shared by
two interchangeable run modes:

* **offline** — a self-contained agentic-retrieval loop over a local, cited
  corpus, so the demo runs on stage with zero network calls;
* **foundry** — the identical loop wired to Foundry Agent Service + a Foundry IQ
  knowledge base (env-gated).

`batayan` (Filipino): *basis, grounds, foundation.*
"""

from .schema import (
    Citation,
    Profile,
    ReasoningResult,
    RuleOutcome,
    RuleVerdict,
    Verdict,
)

__all__ = [
    "Citation",
    "Profile",
    "ReasoningResult",
    "RuleOutcome",
    "RuleVerdict",
    "Verdict",
    "__version__",
]

__version__ = "0.1.0"
