"""
Simple eval for the Deal Desk specialists.

Each specialist's system prompt is taken from create_specialists.py. We run each
one as a one-shot Claude API call against the synthetic RFP and grade the
response. No coordinator, no multi-agent — this isolates each specialist's
behaviour.

Graders:
  - response_contains: substring match (case-insensitive)
  - llm_judge: Claude Haiku judges PASS/FAIL against a criterion

Outputs:
  - evals/results/eval_<timestamp>.json   (full structured results)
  - evals/results/eval_<timestamp>.html   (human-readable report)

Usage:
  export ANTHROPIC_API_KEY="sk-ant-..."
  python evals/eval_specialists.py
"""

from __future__ import annotations

import html
import json
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from anthropic import Anthropic

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from create_specialists import SPECIALISTS  # noqa: E402

SPECIALIST_BY_KEY = {s["key"]: s for s in SPECIALISTS}

RESULTS_DIR = Path(__file__).resolve().parent / "results"
SYNTHETIC_DIR = REPO_ROOT / "synthetic-data"

JUDGE_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 2048

client = Anthropic()


def load_synthetic_inputs() -> dict[str, str]:
    return {
        "rfp": (SYNTHETIC_DIR / "rfp-acme-corp.md").read_text(encoding="utf-8"),
        "product_overview": (SYNTHETIC_DIR / "product-overview.md").read_text(encoding="utf-8"),
        "past_wins": (SYNTHETIC_DIR / "past-wins.json").read_text(encoding="utf-8"),
    }


def build_user_prompt(specialist_key: str, inputs: dict[str, str]) -> str:
    rfp = inputs["rfp"]
    if specialist_key == "pricing":
        return (
            "Here is the RFP and our past-wins data. Produce your pricing recommendation.\n\n"
            f"=== RFP ===\n{rfp}\n\n"
            f"=== past-wins.json ===\n{inputs['past_wins']}\n"
        )
    if specialist_key == "legal":
        return f"Here is the RFP. Produce your legal review.\n\n=== RFP ===\n{rfp}\n"
    if specialist_key == "technical_fit":
        return (
            "Here is the RFP and our product overview. Produce your technical fit assessment.\n\n"
            f"=== RFP ===\n{rfp}\n\n"
            f"=== product-overview.md ===\n{inputs['product_overview']}\n"
        )
    if specialist_key == "competitive":
        return f"Here is the RFP. Produce your competitive analysis.\n\n=== RFP ===\n{rfp}\n"
    raise ValueError(f"Unknown specialist key: {specialist_key}")


def run_specialist(specialist_key: str, inputs: dict[str, str]) -> dict:
    spec = SPECIALIST_BY_KEY[specialist_key]
    user_prompt = build_user_prompt(specialist_key, inputs)
    start = time.time()
    response = client.messages.create(
        model=spec["model"],
        system=spec["system"],
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": user_prompt}],
    )
    elapsed = time.time() - start
    text = "".join(block.text for block in response.content if hasattr(block, "text"))
    return {
        "final_text": text,
        "model": spec["model"],
        "elapsed_s": round(elapsed, 2),
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }


# ── Graders ──────────────────────────────────────────────────────────────────

JUDGE_SYSTEM = (
    "You are an eval grader. Judge whether an agent's response meets a criterion. "
    "Respond with PASS or FAIL on the first line, then a one-sentence reason on the next."
)


def grade_contains(result: dict, check: str) -> dict:
    text = result["final_text"].lower()
    if check.lower() in text:
        return {"score": 1.0, "reason": f"Found '{check}'"}
    return {"score": 0.0, "reason": f"'{check}' not found"}


def grade_llm_judge(result: dict, check: str, query: str) -> dict:
    judge_prompt = (
        f"Original task: {query}\n\n"
        f"Agent's response:\n{result['final_text']}\n\n"
        f"Criterion: {check}"
    )
    try:
        resp = client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=150,
            temperature=0.0,
            system=JUDGE_SYSTEM,
            messages=[{"role": "user", "content": judge_prompt}],
        )
        text = resp.content[0].text.strip()
        first = text.split("\n", 1)[0].upper()
        reason = text.split("\n", 1)[1].strip() if "\n" in text else text
        if "PASS" in first:
            return {"score": 1.0, "reason": f"Judge: {reason}"}
        if "FAIL" in first:
            return {"score": 0.0, "reason": f"Judge: {reason}"}
        return {"score": 0.0, "reason": f"Unparseable: {text[:120]}"}
    except Exception as exc:
        return {"score": 0.0, "reason": f"Judge error: {exc}"}


# ── Tasks ────────────────────────────────────────────────────────────────────

TASKS = [
    {
        "id": "pricing_addresses_acme_demands",
        "specialist": "pricing",
        "description": "Pricing specialist addresses each of Acme's four red-flag demands",
        "graders": [
            {"type": "contains", "checks": ["35%", "Net 90", "MFN", "escalator"]},
            {"type": "llm_judge", "checks": [
                "Response states whether each of Acme's demands (35% discount, Net 90, no escalators, MFN) is a non-starter, negotiable, or acceptable",
                "Response references comparable past wins data when recommending a discount band",
            ]},
        ],
    },
    {
        "id": "legal_uses_required_format",
        "specialist": "legal",
        "description": "Legal reviewer uses the structured ITEM/Severity format and aggregate risk matrix",
        "graders": [
            {"type": "contains", "checks": ["BLOCKER", "Severity", "Counter", "Overall contract risk"]},
            {"type": "llm_judge", "checks": [
                "Response uses the required ITEM N / RFP says / Severity / Why / Counter structure for each flag",
            ]},
        ],
    },
    {
        "id": "technical_fit_flags_known_gaps",
        "specialist": "technical_fit",
        "description": "Technical fit calls out 80K events/sec, Power BI, 99.99 SLA, and the 2027 Teradata deadline",
        "graders": [
            {"type": "contains", "checks": ["80,000", "Power BI", "99.99", "2027"]},
            {"type": "llm_judge", "checks": [
                "Response provides an overall fit score of HIGH, MEDIUM, or LOW with a rationale",
            ]},
        ],
    },
    {
        "id": "competitive_analyses_named_shortlist",
        "specialist": "competitive",
        "description": "Competitive analyst covers Databricks, Snowflake, Microsoft Fabric, and the regional vendor",
        "graders": [
            {"type": "contains", "checks": ["Databricks", "Snowflake", "Microsoft Fabric"]},
            {"type": "llm_judge", "checks": [
                "Response identifies which competitor is the biggest threat and explains why",
                "Response gives a win-probability rating (HIGH, MEDIUM, or LOW) with rationale",
            ]},
        ],
    },
]


def run_task(task: dict, inputs: dict[str, str]) -> dict:
    start = time.time()
    try:
        result = run_specialist(task["specialist"], inputs)
    except Exception:
        return {
            "task_id": task["id"],
            "specialist": task["specialist"],
            "description": task["description"],
            "passed": False,
            "grades": [],
            "error": traceback.format_exc(),
            "elapsed_s": round(time.time() - start, 2),
        }

    grades = []
    query = f"[{task['specialist']}] {task['description']}"
    for grader in task["graders"]:
        gtype = grader["type"]
        for check in grader["checks"]:
            if gtype == "contains":
                g = grade_contains(result, check)
            elif gtype == "llm_judge":
                g = grade_llm_judge(result, check, query)
            else:
                g = {"score": 0.0, "reason": f"Unknown grader: {gtype}"}
            grades.append({"type": gtype, "check": check, **g})

    passed = bool(grades) and all(g["score"] == 1.0 for g in grades)
    return {
        "task_id": task["id"],
        "specialist": task["specialist"],
        "description": task["description"],
        "passed": passed,
        "grades": grades,
        "final_text": result["final_text"],
        "model": result["model"],
        "elapsed_s": result["elapsed_s"],
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
    }


def run_eval(max_workers: int = 4) -> dict:
    inputs = load_synthetic_inputs()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(run_task, t, inputs): t for t in TASKS}
        results = [f.result() for f in as_completed(futures)]
    order = {t["id"]: i for i, t in enumerate(TASKS)}
    results.sort(key=lambda r: order[r["task_id"]])
    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "num_tasks": len(TASKS),
        "num_passed": sum(1 for r in results if r["passed"]),
        "results": results,
    }


# ── HTML report ──────────────────────────────────────────────────────────────

HTML_STYLES = """
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       max-width: 1000px; margin: 2em auto; padding: 0 1em; color: #1d1d1f; }
h1 { margin-bottom: 0.2em; }
.meta { color: #6e6e73; font-size: 0.9em; margin-bottom: 2em; }
.summary { padding: 1em 1.25em; border-radius: 8px; background: #f5f5f7;
           font-size: 1.1em; margin-bottom: 1.5em; }
.summary strong { font-size: 1.3em; }
.task { border: 1px solid #e1e1e6; border-radius: 8px; margin-bottom: 1em;
        padding: 1em 1.25em; }
.task.pass { border-left: 4px solid #34c759; }
.task.fail { border-left: 4px solid #ff3b30; }
.task h2 { font-size: 1.05em; margin: 0 0 0.3em 0; }
.badge { display: inline-block; font-size: 0.75em; padding: 0.15em 0.55em;
         border-radius: 4px; margin-left: 0.5em; vertical-align: middle;
         font-weight: 600; }
.badge.pass { background: #34c759; color: white; }
.badge.fail { background: #ff3b30; color: white; }
.specialist { color: #6e6e73; font-size: 0.85em; font-weight: normal; }
.metrics { color: #6e6e73; font-size: 0.8em; margin: 0.4em 0 0.8em 0; }
.grade { font-size: 0.88em; margin: 0.2em 0; padding-left: 1.4em;
         text-indent: -1.4em; }
.grade .icon { font-weight: bold; margin-right: 0.4em; }
.grade.pass .icon { color: #34c759; }
.grade.fail .icon { color: #ff3b30; }
.grade .check { color: #6e6e73; }
details { margin-top: 0.6em; }
details summary { cursor: pointer; color: #0071e3; font-size: 0.85em; }
pre { background: #f5f5f7; padding: 0.8em; border-radius: 6px;
      white-space: pre-wrap; word-wrap: break-word; font-size: 0.8em;
      max-height: 400px; overflow-y: auto; }
.error { color: #ff3b30; font-size: 0.85em; }
"""


def render_html(eval_result: dict) -> str:
    passed = eval_result["num_passed"]
    total = eval_result["num_tasks"]
    pct = 100 * passed / total if total else 0

    parts = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        "<title>Deal Desk Specialists — Eval Results</title>",
        f"<style>{HTML_STYLES}</style></head><body>",
        "<h1>Deal Desk Specialists — Eval Results</h1>",
        f'<div class="meta">Run: {html.escape(eval_result["timestamp"])}</div>',
        f'<div class="summary"><strong>{passed}/{total}</strong> tasks passed '
        f"({pct:.0f}%)</div>",
    ]

    for r in eval_result["results"]:
        cls = "pass" if r["passed"] else "fail"
        badge_label = "PASS" if r["passed"] else "FAIL"
        parts.append(f'<div class="task {cls}">')
        parts.append(
            f'<h2>{html.escape(r["task_id"])}'
            f'<span class="badge {cls}">{badge_label}</span>'
            f'<span class="specialist"> — {html.escape(r["specialist"])}</span></h2>'
        )
        parts.append(f'<div>{html.escape(r["description"])}</div>')
        if "error" in r:
            parts.append(f'<div class="error">Error: {html.escape(r["error"][:500])}</div>')
        else:
            parts.append(
                f'<div class="metrics">'
                f'model: {html.escape(r["model"])} · '
                f'{r["elapsed_s"]}s · '
                f'{r["input_tokens"]:,} in / {r["output_tokens"]:,} out tokens</div>'
            )
            for g in r["grades"]:
                gcls = "pass" if g["score"] == 1.0 else "fail"
                icon = "✓" if g["score"] == 1.0 else "✗"
                check_label = (
                    g["check"][:120] + "…" if len(g["check"]) > 120 else g["check"]
                )
                parts.append(
                    f'<div class="grade {gcls}">'
                    f'<span class="icon">{icon}</span>'
                    f'<span class="check">[{html.escape(g["type"])}] '
                    f'{html.escape(check_label)}</span> — '
                    f'{html.escape(g["reason"])}</div>'
                )
            parts.append(
                "<details><summary>Show specialist response</summary>"
                f'<pre>{html.escape(r["final_text"])}</pre></details>'
            )
        parts.append("</div>")

    parts.append("</body></html>")
    return "\n".join(parts)


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Running {len(TASKS)} specialist eval task(s)...")
    eval_result = run_eval()

    ts = time.strftime("%Y%m%d_%H%M%S")
    json_path = RESULTS_DIR / f"eval_{ts}.json"
    html_path = RESULTS_DIR / f"eval_{ts}.html"
    json_path.write_text(json.dumps(eval_result, indent=2), encoding="utf-8")
    html_path.write_text(render_html(eval_result), encoding="utf-8")

    print(
        f"\n{eval_result['num_passed']}/{eval_result['num_tasks']} passed"
        f"  ({100 * eval_result['num_passed'] / eval_result['num_tasks']:.0f}%)"
    )
    for r in eval_result["results"]:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"  [{mark}] {r['task_id']}")
        for g in r["grades"]:
            tick = "+" if g["score"] == 1.0 else "-"
            print(f"      {tick} [{g['type']}] {g['reason'][:100]}")

    print(f"\nJSON:  {json_path}")
    print(f"HTML:  {html_path}")


if __name__ == "__main__":
    main()
