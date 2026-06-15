"""Knowledge bases, offline agentic retrieval, and grounding verification.

In **Foundry mode** this responsibility belongs to Foundry IQ: it decomposes the
query, runs permission-aware retrieval over registered knowledge sources, and
returns extractive citations. This module is the **offline** mirror of that same
behaviour so the demo runs without Azure — it chunks the prose rulebooks, scores
chunks against a retrieval query, and *verifies that every cited quote actually
exists in the retrieved source* (the grounding guarantee).
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

_WORD = re.compile(r"[a-z0-9]+")
_HEADER = re.compile(r"^(#{1,6})\s+(.*)$")


def _tokenize(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _normalize(text: str) -> str:
    """Collapse whitespace so quote-matching is robust to wrapping/formatting."""
    return re.sub(r"\s+", " ", text).strip().lower()


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class Chunk:
    source: str
    section: str
    text: str


@dataclass
class Predicate:
    field: str
    op: str
    value: Any = None

    OPS = {
        "eq": lambda a, b: a == b,
        "neq": lambda a, b: a != b,
        "gte": lambda a, b: a >= b,
        "lte": lambda a, b: a <= b,
        "gt": lambda a, b: a > b,
        "lt": lambda a, b: a < b,
        "in": lambda a, b: a in b,
        "not_in": lambda a, b: a not in b,
        "is_true": lambda a, b: bool(a) is True,
        "is_false": lambda a, b: bool(a) is False,
    }

    def evaluate(self, actual: Any) -> bool:
        fn = self.OPS[self.op]
        # Case-insensitive comparison for strings / string membership.
        if isinstance(actual, str) and isinstance(self.value, str):
            return fn(actual.lower(), self.value.lower())
        if self.op in {"in", "not_in"} and isinstance(self.value, list):
            if isinstance(actual, str):
                return fn(actual.lower(), [str(v).lower() for v in self.value])
        return fn(actual, self.value)

    def describe(self, actual: Any) -> str:
        symbols = {
            "eq": "=", "neq": "≠", "gte": "≥", "lte": "≤",
            "gt": ">", "lt": "<", "in": "∈", "not_in": "∉",
            "is_true": "is true", "is_false": "is false",
        }
        sym = symbols.get(self.op, self.op)
        if self.op in {"is_true", "is_false"}:
            return f"{self.field} {sym} (actual: {actual!r})"
        return f"{self.field} {sym} {self.value!r} (actual: {actual!r})"


@dataclass
class CitationSpec:
    source: str
    section: str
    quote: str
    as_of: str


@dataclass
class Rule:
    id: str
    description: str
    predicate: Predicate
    cites: CitationSpec
    decisive: bool = True
    remediation: str | None = None

    @property
    def required_field(self) -> str:
        return self.predicate.field


@dataclass
class Program:
    name: str
    kb: str
    decision_subject: str
    rules: list[Rule] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)

    def matches(self, query: str) -> bool:
        q = query.lower()
        names = [self.name.lower(), *[a.lower() for a in self.aliases]]
        return any(n in q or q in n for n in names) or any(
            tok in q for n in names for tok in _tokenize(n) if len(tok) > 3
        )


@dataclass
class KnowledgeBase:
    """A reusable bundle of cited knowledge sources + the programs they govern."""

    name: str
    description: str
    root: Path
    programs: list[Program] = field(default_factory=list)
    _chunks: list[Chunk] = field(default_factory=list)
    _idf: dict[str, float] = field(default_factory=dict)

    # -- retrieval ---------------------------------------------------------
    def _ensure_index(self) -> None:
        if self._chunks:
            return
        docs: dict[str, list[set[str]]] = {}
        for path in sorted(self.root.glob("*.md")):
            for section, text in _split_sections(path.read_text(encoding="utf-8")):
                self._chunks.append(Chunk(path.name, section, text))
        # Inverse document frequency over chunks → meaningful retrieval scores.
        n = len(self._chunks) or 1
        df: dict[str, int] = {}
        for chunk in self._chunks:
            for tok in set(_tokenize(chunk.text + " " + chunk.section)):
                df[tok] = df.get(tok, 0) + 1
        self._idf = {tok: math.log((n + 1) / (c + 0.5)) for tok, c in df.items()}
        _ = docs  # readability placeholder; index lives in _chunks/_idf

    def retrieve(self, query: str, source: str | None = None, k: int = 1) -> list[tuple[Chunk, float]]:
        """Score chunks against the query (TF·IDF cosine-ish, stdlib only)."""
        self._ensure_index()
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        q_weights = {t: self._idf.get(t, 0.0) for t in set(q_tokens)}
        scored: list[tuple[Chunk, float]] = []
        for chunk in self._chunks:
            if source and chunk.source != source:
                continue
            c_tokens = _tokenize(chunk.text + " " + chunk.section)
            if not c_tokens:
                continue
            tf: dict[str, int] = {}
            for t in c_tokens:
                tf[t] = tf.get(t, 0) + 1
            dot = sum(q_weights.get(t, 0.0) * tf.get(t, 0) * self._idf.get(t, 0.0)
                      for t in q_weights)
            norm = math.sqrt(sum((tf.get(t, 0) * self._idf.get(t, 0.0)) ** 2
                                 for t in set(c_tokens))) or 1.0
            scored.append((chunk, dot / norm))
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:k]
        max_score = top[0][1] if top and top[0][1] else 1.0
        return [(c, round(s / max_score, 3)) for c, s in top]

    def ground(self, cite: CitationSpec, score: float = 0.0):
        """Confirm the cited quote really lives in the cited source.

        Grounding is deliberately stricter and more robust than top-1 retrieval:
        we scan every chunk of the *cited source* for the quote, preferring the
        named section. Retrieval gives us a relevance score to display; grounding
        gives us the safety guarantee that the receipt is real.
        """
        from .schema import Citation

        self._ensure_index()
        norm_q = _normalize(cite.quote)
        candidates = [c for c in self._chunks if c.source == cite.source]
        located: Chunk | None = None
        # Prefer the explicitly cited section.
        for c in candidates:
            if c.section.lower() == cite.section.lower() and norm_q in _normalize(c.text):
                located = c
                break
        # Fall back to anywhere in the same source.
        if located is None:
            for c in candidates:
                if norm_q in _normalize(c.text):
                    located = c
                    break
        return Citation(
            source=cite.source,
            section=located.section if located else cite.section,
            quote=cite.quote,
            as_of=cite.as_of,
            retrieval_score=score,
            grounded=located is not None,
        )

    def has_source(self, source: str) -> bool:
        self._ensure_index()
        return any(c.source == source for c in self._chunks)

    def find_program(self, query: str) -> Program | None:
        for program in self.programs:
            if program.matches(query):
                return program
        return None

    def sources(self) -> list[str]:
        return sorted({p.name for p in self.root.glob("*.md")})


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def _split_sections(markdown: str) -> Iterable[tuple[str, str]]:
    section = "Preamble"
    buffer: list[str] = []
    for line in markdown.splitlines():
        m = _HEADER.match(line)
        if m:
            if buffer:
                yield section, "\n".join(buffer).strip()
                buffer = []
            section = m.group(2).strip()
        else:
            buffer.append(line)
    if buffer:
        yield section, "\n".join(buffer).strip()


def _load_program(path: Path) -> Program:
    data = json.loads(path.read_text(encoding="utf-8"))
    rules = []
    for r in data["rules"]:
        c = r["cites"]
        rules.append(
            Rule(
                id=r["id"],
                description=r["description"],
                predicate=Predicate(**r["predicate"]),
                cites=CitationSpec(
                    source=c["source"], section=c["section"],
                    quote=c["quote"], as_of=c["as_of"],
                ),
                decisive=r.get("decisive", True),
                remediation=r.get("remediation"),
            )
        )
    return Program(
        name=data["program"],
        kb=data["kb"],
        decision_subject=data.get("decision_subject", "eligibility"),
        rules=rules,
        aliases=data.get("aliases", []),
    )


def load_knowledge_base(root: Path) -> KnowledgeBase:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    programs = [_load_program(p) for p in sorted(root.glob("*.rules.json"))]
    return KnowledgeBase(
        name=manifest["name"],
        description=manifest.get("description", ""),
        root=root,
        programs=programs,
    )


def knowledge_root() -> Path:
    """Locate the bundled ``knowledge/`` directory (repo-relative)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "knowledge"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("Could not locate the knowledge/ directory.")


def load_all_knowledge_bases(root: Path | None = None) -> dict[str, KnowledgeBase]:
    root = root or knowledge_root()
    bases: dict[str, KnowledgeBase] = {}
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "manifest.json").exists():
            kb = load_knowledge_base(child)
            bases[kb.name] = kb
    return bases
