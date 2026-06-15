"""Evaluation harness — turns 'reliability' from a claim into a measurement.

Runs a labelled set of decisions and reports a 3x3 confusion matrix over
{ELIGIBLE, INELIGIBLE, INSUFFICIENT_EVIDENCE}, plus the metric that matters most for
a safety-first agent: **abstention recall** — how often the agent correctly says
"I cannot determine this" instead of guessing.
"""

from __future__ import annotations

import json
from pathlib import Path

from .knowledge import load_all_knowledge_bases
from .reasoner import decide
from .schema import Profile, Verdict

_CLASSES = [Verdict.ELIGIBLE, Verdict.INELIGIBLE, Verdict.INSUFFICIENT_EVIDENCE]
_SHORT = {
    Verdict.ELIGIBLE: "ELIG",
    Verdict.INELIGIBLE: "INELIG",
    Verdict.INSUFFICIENT_EVIDENCE: "ABSTAIN",
}


def default_dataset() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "eval" / "dataset.json"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Bundled eval/dataset.json not found.")


def run(dataset_path: Path) -> dict:
    bases = load_all_knowledge_bases()
    items = json.loads(dataset_path.read_text(encoding="utf-8"))["cases"]

    matrix = {e: {p: 0 for p in _CLASSES} for e in _CLASSES}
    rows = []
    for case in items:
        # locate program across knowledge bases
        program = None
        kb = None
        for base in bases.values():
            program = base.find_program(case["program"])
            if program:
                kb = base
                break
        if not program:
            raise ValueError(f"Program not found for case: {case['program']}")
        profile = Profile.from_dict(case["profile"])
        result = decide(kb, program, profile)
        expected = Verdict(case["expected"])
        predicted = result.verdict
        matrix[expected][predicted] += 1
        rows.append((case.get("name", profile.name), case["program"], expected, predicted))

    total = len(items)
    correct = sum(matrix[c][c] for c in _CLASSES)
    accuracy = correct / total if total else 0.0

    # Per-class precision / recall
    metrics = {}
    for c in _CLASSES:
        tp = matrix[c][c]
        fp = sum(matrix[e][c] for e in _CLASSES if e != c)
        fn = sum(matrix[c][p] for p in _CLASSES if p != c)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        metrics[c] = {"precision": precision, "recall": recall, "support": tp + fn}

    return {
        "total": total,
        "accuracy": accuracy,
        "matrix": matrix,
        "metrics": metrics,
        "rows": rows,
        "abstention_recall": metrics[Verdict.INSUFFICIENT_EVIDENCE]["recall"],
        "denial_precision": metrics[Verdict.INELIGIBLE]["precision"],
    }


def format_report(r: dict) -> str:
    lines = []
    lines.append("BATAYAN — evaluation report")
    lines.append("=" * 52)
    lines.append(f"cases: {r['total']}   accuracy: {r['accuracy']*100:.1f}%")
    lines.append("")
    # confusion matrix
    header = "expected \\ predicted".ljust(22) + "".join(_SHORT[c].ljust(10) for c in _CLASSES)
    lines.append(header)
    for e in _CLASSES:
        row = _SHORT[e].ljust(22) + "".join(str(r["matrix"][e][p]).ljust(10) for p in _CLASSES)
        lines.append(row)
    lines.append("")
    lines.append("per-class:")
    for c in _CLASSES:
        m = r["metrics"][c]
        lines.append(
            f"  {_SHORT[c]:<9} precision={m['precision']*100:5.1f}%  "
            f"recall={m['recall']*100:5.1f}%  support={m['support']}"
        )
    lines.append("")
    lines.append(f"★ abstention recall (correctly refused to guess): {r['abstention_recall']*100:.1f}%")
    lines.append(f"★ denial precision  (no wrongful 'ineligible'):    {r['denial_precision']*100:.1f}%")
    lines.append("")
    # per-case
    lines.append("cases:")
    for name, program, expected, predicted in r["rows"]:
        ok = "ok " if expected == predicted else "XX "
        lines.append(f"  [{ok}] {name:<18} {program:<34} "
                     f"{_SHORT[expected]} -> {_SHORT[predicted]}")
    return "\n".join(lines)


def cmd_eval(args) -> int:
    path = Path(args.dataset) if getattr(args, "dataset", None) else default_dataset()
    report = run(path)
    print(format_report(report))
    # Non-zero exit if any case is wrong — usable as a CI gate.
    return 0 if report["accuracy"] == 1.0 else 1
