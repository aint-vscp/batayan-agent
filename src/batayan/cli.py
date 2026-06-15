"""Command-line interface — renders the reasoning as a legible 'evidence ledger'.

Design goal: a non-technical judge should be able to read the output like a court
transcript — claim, the rule invoked, the citation for each, and the verdict — and
see that the agent *shows its work and refuses to bluff*.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .knowledge import KnowledgeBase, load_all_knowledge_bases
from .reasoner import decide
from .schema import Profile, ReasoningResult, RuleVerdict, Verdict

# --------------------------------------------------------------------------- #
# Minimal, dependency-free styling (honours NO_COLOR and non-TTY pipes)
# --------------------------------------------------------------------------- #
_USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _enable_utf8() -> None:
    """Make Unicode output safe on Windows consoles (cp1252) and piped output."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def _c(text: str, code: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def bold(t: str) -> str: return _c(t, "1")
def dim(t: str) -> str: return _c(t, "2")
def green(t: str) -> str: return _c(t, "32")
def red(t: str) -> str: return _c(t, "31")
def yellow(t: str) -> str: return _c(t, "33")
def cyan(t: str) -> str: return _c(t, "36")


_VERDICT_STYLE = {
    Verdict.ELIGIBLE: (green, "✔"),
    Verdict.INELIGIBLE: (red, "✗"),
    Verdict.INSUFFICIENT_EVIDENCE: (yellow, "?"),
}
_RULE_STYLE = {
    RuleVerdict.PASS: (green, "✔ PASS"),
    RuleVerdict.FAIL: (red, "✗ FAIL"),
    RuleVerdict.INSUFFICIENT_EVIDENCE: (yellow, "? NEEDS EVIDENCE"),
}


def _rule(width: int = 70) -> str:
    return dim("─" * width)


def _banner(width: int = 70) -> str:
    return cyan("═" * width)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render(result: ReasoningResult, show_referrals: list[ReasoningResult] | None = None) -> str:
    lines: list[str] = []
    lines.append(_banner())
    lines.append(bold("  BATAYAN") + dim("  ·  grounded eligibility reasoning  ·  AI that argues with receipts"))
    lines.append(_banner())
    lines.append(f"{bold('Question')}      : {result.question}")
    lines.append(
        f"{bold('Knowledge base')}: {result.knowledge_base}    "
        f"{bold('Engine')}: {result.engine}"
    )
    lines.append("")

    # Plan
    lines.append(cyan("▸ PLAN") + dim(f" — decomposed into {len(result.outcomes)} atomic rule(s)"))
    for i, o in enumerate(result.outcomes, 1):
        tag = dim("(decisive)") if o.decisive else dim("(non-decisive)")
        lines.append(f"  {i}. {bold(o.rule_id):<28} {o.description} {tag}")
    lines.append("")

    # Evidence ledger
    lines.append(cyan("▸ EVIDENCE LEDGER"))
    for i, o in enumerate(result.outcomes, 1):
        style, label = _RULE_STYLE[o.verdict]
        lines.append(f"  [{i}] {bold(o.rule_id):<30} {style(label)}")
        if o.query:
            lines.append(dim(f"      query     : {o.query}"))
        if o.citation:
            cit = o.citation
            badge = green("grounded") if cit.grounded else red("UNGROUNDED")
            lines.append(
                dim("      retrieved : ")
                + f"{cit.source} § {cit.section} "
                + dim(f"(score {cit.retrieval_score})")
            )
            lines.append(
                dim("      evidence  : ")
                + f"{badge} "
                + f"\u201c{cit.quote}\u201d "
                + dim(f"(as of {cit.as_of})")
            )
        lines.append(f"      check     : {o.explanation}")
        if o.remediation and o.verdict is not RuleVerdict.PASS:
            lines.append(yellow(f"      fix       : {o.remediation}"))
    lines.append("")

    # Coverage gate
    decisive = result.decisive_outcomes
    provable = [d for d in decisive if d.verdict is not RuleVerdict.INSUFFICIENT_EVIDENCE]
    pct = int(round(result.coverage * 100))
    cov_line = f"  decisive rules grounded & evaluated: {len(provable)}/{len(decisive)} ({pct}%)"
    lines.append(cyan("▸ COVERAGE GATE"))
    lines.append(cov_line if result.coverage == 1.0 else yellow(cov_line))
    if result.missing_evidence:
        lines.append(yellow("  still needed:"))
        for m in result.missing_evidence:
            lines.append(yellow(f"    • {m}"))
    lines.append("")

    # Verdict
    vstyle, vicon = _VERDICT_STYLE[result.verdict]
    lines.append(_rule())
    lines.append(f"  {bold('VERDICT')}: {vstyle(vicon + ' ' + result.verdict.value)}")
    lines.append(f"  {result.summary}")
    lines.append(_rule())

    # Referrals — turn a 'no' into a path forward
    if show_referrals:
        lines.append("")
        lines.append(cyan("▸ YOU MAY STILL QUALIFY ELSEWHERE"))
        for r in show_referrals:
            lines.append(green(f"  ✔ {r.program}") + dim(f" — {r.summary}"))
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _load_profile(path: str) -> Profile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Profile.from_dict(data)


def _resolve(bases: dict[str, KnowledgeBase], program_query: str, kb_name: str | None):
    """Find the (knowledge base, program) for a query across all bases."""
    candidates = [bases[kb_name]] if kb_name and kb_name in bases else list(bases.values())
    for kb in candidates:
        program = kb.find_program(program_query)
        if program:
            return kb, program
    return None, None


def _referrals(bases: dict[str, KnowledgeBase], kb: KnowledgeBase, profile: Profile,
               exclude: str) -> list[ReasoningResult]:
    out: list[ReasoningResult] = []
    for program in kb.programs:
        if program.name == exclude:
            continue
        r = decide(kb, program, profile)
        if r.verdict is Verdict.ELIGIBLE:
            out.append(r)
    return out


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_ask(args: argparse.Namespace) -> int:
    bases = load_all_knowledge_bases()
    program_query = args.program or args.question or ""
    if not program_query:
        print(red("Specify a program with --program or in the question."), file=sys.stderr)
        return 2
    kb, program = _resolve(bases, program_query, args.kb)
    if not program:
        print(red(f"No program matched '{program_query}'. Try `batayan programs`."), file=sys.stderr)
        return 2

    profile = _load_profile(args.applicant)

    if args.engine == "foundry":
        from .foundry import decide_with_foundry  # lazy import (optional deps)
        result = decide_with_foundry(kb, program, profile, question=args.question or "")
    else:
        result = decide(kb, program, profile, question=args.question or "", engine="offline")

    if args.json:
        print(result.to_json())
        return 0

    referrals = None
    if args.refer and result.verdict is not Verdict.ELIGIBLE:
        referrals = _referrals(bases, kb, profile, exclude=program.name)
    print(render(result, show_referrals=referrals))
    return 0


def cmd_programs(args: argparse.Namespace) -> int:
    bases = load_all_knowledge_bases()
    for kb in bases.values():
        print(bold(f"\n{kb.name}") + dim(f" — {kb.description}"))
        for p in kb.programs:
            print(f"  • {p.name}  " + dim(f"({len(p.rules)} rules)"))
            if p.aliases:
                print(dim(f"      aliases: {', '.join(p.aliases)}"))
    return 0


def cmd_kb(args: argparse.Namespace) -> int:
    bases = load_all_knowledge_bases()
    for kb in bases.values():
        print(bold(f"\n{kb.name}") + dim(f" — {kb.description}"))
        for s in kb.sources():
            print(f"  - {s}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    """Run the three canonical reasoning beats + the reuse beat."""
    here = Path(__file__).resolve().parents[2]
    ex = here / "examples"
    script = [
        ("DOST-SEI", ex / "liza.json", "Yes — with receipts"),
        ("DOST-SEI", ex / "mateo.json", "No — because of exactly one rule (+ referral)"),
        ("DOST-SEI", ex / "aisha.json", "Abstain — refuses to guess"),
        ("parental leave", ex / "employee-ramon.json", "Same engine, different rulebook"),
    ]
    bases = load_all_knowledge_bases()
    for program_query, profile_path, caption in script:
        print("\n" + yellow(f"### BEAT: {caption}"))
        kb, program = _resolve(bases, program_query, None)
        profile = Profile.from_dict(json.loads(Path(profile_path).read_text(encoding="utf-8")))
        result = decide(kb, program, profile)
        referrals = (_referrals(bases, kb, profile, program.name)
                     if result.verdict is not Verdict.ELIGIBLE else None)
        print(render(result, show_referrals=referrals))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="batayan",
        description="Batayan — a grounded, multi-step eligibility-reasoning agent "
                    "(Microsoft Foundry + Foundry IQ).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask", help="Adjudicate one eligibility decision with cited reasoning.")
    ask.add_argument("question", nargs="?", default="", help="Natural-language question (optional).")
    ask.add_argument("--program", help="Program/policy to evaluate (name or alias).")
    ask.add_argument("--applicant", required=True, help="Path to applicant/subject JSON profile.")
    ask.add_argument("--kb", help="Restrict to a knowledge base by name.")
    ask.add_argument("--engine", choices=["offline", "foundry"], default="offline",
                     help="offline (local, default) or foundry (Foundry Agent Service + Foundry IQ).")
    ask.add_argument("--json", action="store_true", help="Emit the ReasoningResult as JSON.")
    ask.add_argument("--no-refer", dest="refer", action="store_false",
                     help="Disable auto-referral to other programs the applicant qualifies for.")
    ask.set_defaults(func=cmd_ask, refer=True)

    sub.add_parser("programs", help="List all programs across knowledge bases.").set_defaults(func=cmd_programs)
    sub.add_parser("kb", help="List knowledge bases and their sources.").set_defaults(func=cmd_kb)
    sub.add_parser("demo", help="Run the 3 canonical reasoning beats + reuse beat.").set_defaults(func=cmd_demo)

    ev = sub.add_parser("eval", help="Run the labelled eval set and print a confusion matrix.")
    ev.add_argument("--dataset", help="Path to eval dataset JSON (defaults to bundled eval/dataset.json).")
    from .evaluate import cmd_eval  # local import to avoid cycle
    ev.set_defaults(func=cmd_eval)

    return p


def main(argv: list[str] | None = None) -> int:
    _enable_utf8()
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as e:
        print(red(f"File not found: {e}"), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
