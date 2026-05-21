#!/usr/bin/env python3
"""Grade audit outputs against eval_metadata.json assertions.

Walks <iteration_dir>/eval-*/{with_skill,without_skill}/outputs/audit.md,
applies each assertion declared in the sibling eval_metadata.json, writes
grading.json next to outputs/ using the field names the eval-viewer expects
(`text`, `passed`, `evidence`).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def evaluate_assertion(audit_text: str, assertion: dict) -> tuple[bool, str]:
    """Return (passed, evidence) for a single assertion."""
    a_type = assertion.get("type")

    if a_type == "regex":
        pattern = assertion["pattern"]
        min_matches = assertion.get("min_matches", 1)
        matches = re.findall(pattern, audit_text)
        passed = len(matches) >= min_matches
        evidence = f"found {len(matches)} match(es) of /{pattern}/ (need ≥{min_matches}); sample: {matches[:3]}"
        return passed, evidence

    if a_type == "regex_or":
        for pat in assertion["patterns"]:
            m = re.findall(pat, audit_text, flags=re.IGNORECASE)
            if m:
                return True, f"matched /{pat}/ ×{len(m)} (first: {m[0]!r})"
        return False, f"none of {assertion['patterns']} matched"

    if a_type == "contains":
        sub = assertion["substring"]
        passed = sub in audit_text
        evidence = f"substring {sub!r} {'found' if passed else 'NOT found'} in output"
        return passed, evidence

    if a_type == "coverage":
        min_hits = assertion.get("min_hits", 1)
        findings = assertion.get("findings", [])
        hits: list[str] = []
        misses: list[str] = []
        for finding in findings:
            name = finding["name"]
            patterns = finding["patterns"]
            matched = False
            for pat in patterns:
                if re.search(pat, audit_text, flags=re.IGNORECASE):
                    matched = True
                    break
            (hits if matched else misses).append(name)
        passed = len(hits) >= min_hits
        evidence = (
            f"hit {len(hits)}/{len(findings)} (need ≥{min_hits}). "
            f"HIT: {hits}. MISS: {misses}"
        )
        return passed, evidence

    return False, f"unknown assertion type: {a_type}"


def grade_run(run_dir: Path, eval_metadata: dict) -> dict:
    audit_path = run_dir / "outputs" / "audit.md"
    if not audit_path.exists():
        text = ""
        missing = True
    else:
        text = audit_path.read_text(encoding="utf-8", errors="replace")
        missing = False

    expectations = []
    for assertion in eval_metadata.get("assertions", []):
        if missing:
            expectations.append({
                "text": assertion["text"],
                "passed": False,
                "evidence": "audit.md missing — run did not produce output",
            })
            continue
        passed, evidence = evaluate_assertion(text, assertion)
        expectations.append({
            "text": assertion["text"],
            "passed": passed,
            "evidence": evidence,
        })

    n_total = len(expectations)
    n_passed = sum(1 for e in expectations if e["passed"])
    return {
        "eval_id": eval_metadata.get("eval_id"),
        "eval_name": eval_metadata.get("eval_name"),
        "run_path": str(run_dir),
        "expectations": expectations,
        "summary": {
            "passed": n_passed,
            "total": n_total,
            "pass_rate": (n_passed / n_total) if n_total else 0.0,
        },
    }


def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <iteration_dir>", file=sys.stderr)
        sys.exit(2)

    iteration_dir = Path(sys.argv[1]).resolve()
    if not iteration_dir.is_dir():
        print(f"not a directory: {iteration_dir}", file=sys.stderr)
        sys.exit(2)

    eval_dirs = sorted(p for p in iteration_dir.iterdir() if p.is_dir() and p.name.startswith("eval-"))
    if not eval_dirs:
        print(f"no eval-* dirs in {iteration_dir}", file=sys.stderr)
        sys.exit(2)

    summary_rows = []
    for eval_dir in eval_dirs:
        meta_path = eval_dir / "eval_metadata.json"
        if not meta_path.exists():
            print(f"skip {eval_dir.name}: no eval_metadata.json", file=sys.stderr)
            continue
        eval_metadata = json.loads(meta_path.read_text(encoding="utf-8"))

        for config_dir in sorted(p for p in eval_dir.iterdir() if p.is_dir()):
            # Discover run-* subdirs, or fall back to config_dir itself
            run_dirs = sorted(config_dir.glob("run-*")) or [config_dir]
            for run_dir in run_dirs:
                if not (run_dir / "outputs").is_dir() and not (run_dir / "outputs" / "audit.md").exists():
                    continue
                grading = grade_run(run_dir, eval_metadata)
                out_path = run_dir / "grading.json"
                out_path.write_text(json.dumps(grading, indent=2), encoding="utf-8")
                summary_rows.append({
                    "eval": eval_dir.name,
                    "config": config_dir.name,
                    "run": run_dir.name,
                    "passed": grading["summary"]["passed"],
                    "total": grading["summary"]["total"],
                    "pass_rate": grading["summary"]["pass_rate"],
                })
                print(f"{eval_dir.name}/{config_dir.name}/{run_dir.name}: {grading['summary']['passed']}/{grading['summary']['total']}")

    summary_path = iteration_dir / "grading_summary.json"
    summary_path.write_text(json.dumps(summary_rows, indent=2), encoding="utf-8")
    print(f"\nwrote {summary_path}")


if __name__ == "__main__":
    main()
