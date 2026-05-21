"""
Eval for the Deal Desk specialists.

Each specialist is run as a one-shot Claude API call with its system prompt +
the relevant skill content (pricing-playbook, legal-checklist, competitive-intel)
or product-overview.md for the technical-fit specialist.

Graders:
  response_contains — case-insensitive substring match
  llm_judge        — Claude Haiku PASS/FAIL against a criterion

Outputs:
  evals/results/eval_<timestamp>.json
  evals/results/eval_<timestamp>.html

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
SKILLS_DIR = REPO_ROOT / "skills"

JUDGE_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 2048

client = Anthropic()


def load_inputs() -> dict[str, str]:
    return {
        "rfp": (SYNTHETIC_DIR / "rfp-acme-corp.md").read_text(encoding="utf-8"),
        "product_overview": (SYNTHETIC_DIR / "product-overview.md").read_text(encoding="utf-8"),
        "past_wins": (SYNTHETIC_DIR / "past-wins.json").read_text(encoding="utf-8"),
        "skill_pricing": (SKILLS_DIR / "pricing-playbook" / "SKILL.md").read_text(encoding="utf-8"),
        "skill_legal": (SKILLS_DIR / "legal-checklist" / "SKILL.md").read_text(encoding="utf-8"),
        "skill_competitive": (SKILLS_DIR / "competitive-intel" / "SKILL.md").read_text(encoding="utf-8"),
    }


def build_prompt(specialist_key: str, inputs: dict) -> str:
    rfp = inputs["rfp"]
    if specialist_key == "pricing":
        return (
            "Here is the RFP, our past-wins data, and your pricing-playbook skill. "
            "Produce your pricing recommendation.\n\n"
            f"=== RFP ===\n{rfp}\n\n"
            f"=== past-wins.json ===\n{inputs['past_wins']}\n\n"
            f"=== pricing-playbook skill ===\n{inputs['skill_pricing']}\n"
        )
    if specialist_key == "legal":
        return (
            "Here is the RFP and your legal-checklist skill. "
            "Produce your legal review.\n\n"
            f"=== RFP ===\n{rfp}\n\n"
            f"=== legal-checklist skill ===\n{inputs['skill_legal']}\n"
        )
    if specialist_key == "technical_fit":
        return (
            "Here is the RFP and our product overview. "
            "Produce your technical fit assessment.\n\n"
            f"=== RFP ===\n{rfp}\n\n"
            f"=== product-overview.md ===\n{inputs['product_overview']}\n"
        )
    if specialist_key == "competitive":
        return (
            "Here is the RFP and your competitive-intel skill. "
            "Produce your competitive analysis.\n\n"
            f"=== RFP ===\n{rfp}\n\n"
            f"=== competitive-intel skill ===\n{inputs['skill_competitive']}\n"
        )
    raise ValueError(f"Unknown specialist: {specialist_key}")


def call_specialist(specialist_key: str, inputs: dict) -> dict:
    spec = SPECIALIST_BY_KEY[specialist_key]
    start = time.time()
    response = client.messages.create(
        model=spec["model"],
        system=spec["system"],
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": build_prompt(specialist_key, inputs)}],
    )
    text = "".join(b.text for b in response.content if hasattr(b, "text"))
    return {
        "final_text": text,
        "model": spec["model"],
        "elapsed_s": round(time.time() - start, 2),
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }


# ── Graders ──────────────────────────────────────────────────────────────────

JUDGE_SYS = (
    "You are an eval grader. Judge whether an AI agent's response meets a criterion. "
    "First line must be exactly PASS or FAIL. Second line: one-sentence reason."
)


def grade_contains(result: dict, check: str) -> dict:
    if check.lower() in result["final_text"].lower():
        return {"score": 1.0, "reason": f"Found '{check}'"}
    return {"score": 0.0, "reason": f"'{check}' not found in response"}


def grade_llm_judge(result: dict, check: str, query: str) -> dict:
    prompt = (
        f"Task: {query}\n\n"
        f"Response:\n{result['final_text']}\n\n"
        f"Criterion: {check}"
    )
    try:
        resp = client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=150,
            temperature=0.0,
            system=JUDGE_SYS,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        first = raw.split("\n", 1)[0].upper()
        reason = raw.split("\n", 1)[1].strip() if "\n" in raw else raw
        score = 1.0 if "PASS" in first else 0.0
        return {"score": score, "reason": f"Judge: {reason}"}
    except Exception as exc:
        return {"score": 0.0, "reason": f"Judge error: {exc}"}


# ── Tasks ────────────────────────────────────────────────────────────────────

TASKS = [
    # ── Pricing Specialist ────────────────────────────────────────────────
    {
        "id": "pricing_addresses_acme_demands",
        "specialist": "pricing",
        "description": "Addresses each of Acme's four red-flag demands (35%, Net 90, no escalators, MFN)",
        "graders": [
            {"type": "contains", "checks": ["35%", "Net 90", "MFN", "escalat"]},
            {"type": "llm_judge", "checks": [
                "Response states whether each of Acme's four demands is a non-starter, negotiable, or acceptable and gives a counter-position for each",
            ]},
        ],
    },
    {
        "id": "pricing_uses_playbook_specifics",
        "specialist": "pricing",
        "description": "Uses playbook data: Enterprise tier, discount bands, and playbook counter-language",
        "graders": [
            {"type": "contains", "checks": ["Enterprise", "720", "25%", "30%"]},
            {"type": "llm_judge", "checks": [
                "Response references specific numbers from the pricing playbook (tier names, list prices, or max discount percentages) rather than generic advice",
                "Response cites past-wins comparable deals to justify the recommended discount band",
            ]},
        ],
    },

    # ── Legal Reviewer ────────────────────────────────────────────────────
    {
        "id": "legal_uses_required_format",
        "specialist": "legal",
        "description": "Uses the ITEM/Severity/Why/Counter structure for each flag",
        "graders": [
            {"type": "contains", "checks": ["BLOCKER", "Severity", "Counter:", "Overall contract risk"]},
            {"type": "llm_judge", "checks": [
                "Response follows the exact ITEM N / RFP says / Severity / Why / Counter format for at least two flags",
            ]},
        ],
    },
    {
        "id": "legal_covers_all_categories",
        "specialist": "legal",
        "description": "Works through all 10 checklist categories from the skill",
        "graders": [
            {"type": "contains", "checks": ["Liability", "Intellectual Property", "Audit", "Termination", "Subprocessor"]},
            {"type": "llm_judge", "checks": [
                "Response covers at least 7 of the 10 checklist categories: data residency, liability, IP, audit, termination, breach notification, subprocessors, governing law, service levels, insurance",
            ]},
        ],
    },

    # ── Technical Fit Specialist ──────────────────────────────────────────
    {
        "id": "technical_fit_flags_known_gaps",
        "specialist": "technical_fit",
        "description": "Flags the four key requirements: 80K events/sec, Power BI, 99.99% SLA, 2027 Teradata deadline",
        "graders": [
            {"type": "contains", "checks": ["80,000", "Power BI", "99.99", "2027"]},
            {"type": "llm_judge", "checks": [
                "Response provides an overall fit score (HIGH, MEDIUM, or LOW) with a one-sentence rationale",
            ]},
        ],
    },
    {
        "id": "technical_fit_implementation_timeline",
        "specialist": "technical_fit",
        "description": "Gives a concrete implementation timeline and assesses the 2027 Teradata migration deadline",
        "graders": [
            {"type": "contains", "checks": ["2027", "week", "migrat"]},
            {"type": "llm_judge", "checks": [
                "Response gives a specific estimated timeline in weeks or months to first production workload",
                "Response explicitly states whether the implementation timeline is compatible with Acme's 2027 Teradata decommission deadline",
            ]},
        ],
    },

    # ── Competitive Intel Analyst ─────────────────────────────────────────
    {
        "id": "competitive_analyses_named_shortlist",
        "specialist": "competitive",
        "description": "Covers all four named competitors: Databricks, Snowflake, Microsoft Fabric, regional vendor",
        "graders": [
            {"type": "contains", "checks": ["Databricks", "Snowflake", "Microsoft Fabric", "regional"]},
            {"type": "llm_judge", "checks": [
                "Response identifies which competitor is the single biggest threat to winning this deal and explains why",
            ]},
        ],
    },
    {
        "id": "competitive_uses_threat_ranking",
        "specialist": "competitive",
        "description": "Closes with the required THREAT RANKING block and win probability",
        "graders": [
            {"type": "contains", "checks": ["THREAT RANKING", "Win probability", "primary target"]},
            {"type": "llm_judge", "checks": [
                "Response gives a clear win probability rating (HIGH, MEDIUM, or LOW) with a rationale sentence",
                "Response recommends a single best opening move (specific action, not generic advice)",
            ]},
        ],
    },
]

SPECIALIST_LABELS = {
    "pricing": "Pricing Specialist",
    "legal": "Legal Reviewer",
    "technical_fit": "Technical Fit",
    "competitive": "Competitive Intel",
}


def run_task(task: dict, inputs: dict) -> dict:
    start = time.time()
    try:
        result = call_specialist(task["specialist"], inputs)
    except Exception:
        return {
            **{k: task[k] for k in ("id", "specialist", "description")},
            "passed": False, "grades": [],
            "error": traceback.format_exc(),
            "elapsed_s": round(time.time() - start, 2),
        }

    grades = []
    query = task["description"]
    for grader in task["graders"]:
        for check in grader["checks"]:
            if grader["type"] == "contains":
                g = grade_contains(result, check)
            elif grader["type"] == "llm_judge":
                g = grade_llm_judge(result, check, query)
            else:
                g = {"score": 0.0, "reason": f"Unknown grader: {grader['type']}"}
            grades.append({"type": grader["type"], "check": check, **g})

    passed = bool(grades) and all(g["score"] == 1.0 for g in grades)
    return {
        **{k: task[k] for k in ("id", "specialist", "description")},
        "passed": passed, "grades": grades,
        "final_text": result["final_text"],
        "model": result["model"],
        "elapsed_s": result["elapsed_s"],
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
    }


def run_eval(max_workers: int = 4) -> dict:
    inputs = load_inputs()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(run_task, t, inputs): t for t in TASKS}
        results = [f.result() for f in as_completed(futures)]
    order = {t["id"]: i for i, t in enumerate(TASKS)}
    results.sort(key=lambda r: order[r["id"]])
    n_pass = sum(1 for r in results if r["passed"])
    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "num_tasks": len(results),
        "num_passed": n_pass,
        "results": results,
    }


# ── HTML report ───────────────────────────────────────────────────────────────

CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #f0f2f5;
  color: #111;
  padding: 2rem 1rem;
  font-size: 15px;
}
.page { max-width: 920px; margin: 0 auto; }
h1 {
  font-size: 1.6rem;
  font-weight: 700;
  letter-spacing: -0.5px;
  margin-bottom: 0.25rem;
}
.run-meta { color: #666; font-size: 0.85rem; margin-bottom: 1.75rem; }

/* summary bar */
.summary {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  background: #fff;
  border-radius: 12px;
  padding: 1.1rem 1.4rem;
  margin-bottom: 2rem;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
}
.summary .score {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1;
}
.summary .score .total { color: #888; font-size: 1.2rem; }
.progress-bar {
  flex: 1;
  height: 10px;
  background: #e5e7eb;
  border-radius: 9999px;
  overflow: hidden;
}
.progress-bar .fill {
  height: 100%;
  border-radius: 9999px;
  background: linear-gradient(90deg, #22c55e, #16a34a);
  transition: width .4s;
}
.pct { font-size: 1.1rem; font-weight: 600; color: #16a34a; min-width: 3rem; text-align: right; }
.pct.bad { color: #dc2626; }

/* specialist group */
.group { margin-bottom: 1.75rem; }
.group-header {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .08em;
  color: #6b7280;
  margin-bottom: 0.6rem;
  padding-left: 0.2rem;
}

/* task card */
.card {
  background: #fff;
  border-radius: 10px;
  border-left: 4px solid #e5e7eb;
  margin-bottom: 0.65rem;
  box-shadow: 0 1px 3px rgba(0,0,0,.07);
  overflow: hidden;
}
.card.pass { border-left-color: #22c55e; }
.card.fail { border-left-color: #ef4444; }

.card-head {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.85rem 1rem 0.7rem;
}
.badge {
  font-size: 0.68rem;
  font-weight: 700;
  padding: 0.2em 0.55em;
  border-radius: 4px;
  letter-spacing: .04em;
  flex-shrink: 0;
}
.badge.pass { background: #dcfce7; color: #15803d; }
.badge.fail { background: #fee2e2; color: #b91c1c; }
.task-id { font-weight: 600; font-size: 0.92rem; }
.task-desc { color: #555; font-size: 0.85rem; padding: 0 1rem 0.65rem; }
.metrics-row {
  color: #9ca3af;
  font-size: 0.75rem;
  padding: 0 1rem 0.75rem;
  display: flex;
  gap: 1rem;
}

/* grades */
.grades { padding: 0 1rem 0.5rem; }
.grade {
  display: flex;
  gap: 0.5rem;
  font-size: 0.82rem;
  padding: 0.28rem 0;
  border-top: 1px solid #f3f4f6;
  align-items: flex-start;
}
.grade .icon { flex-shrink: 0; font-weight: 700; }
.grade.gpass .icon { color: #16a34a; }
.grade.gfail .icon { color: #dc2626; }
.grade .gtype {
  flex-shrink: 0;
  background: #f1f5f9;
  color: #64748b;
  font-size: 0.7rem;
  padding: 0.1em 0.4em;
  border-radius: 3px;
}
.grade .greason { color: #374151; }
.grade .gcheck { color: #9ca3af; font-size: 0.78rem; font-style: italic; }

/* error */
.error-box {
  margin: 0 1rem 0.75rem;
  padding: 0.6rem 0.8rem;
  background: #fff1f2;
  border-radius: 6px;
  font-size: 0.78rem;
  color: #b91c1c;
  white-space: pre-wrap;
  word-break: break-all;
}

/* transcript toggle */
details { margin: 0.3rem 1rem 0.8rem; }
details summary {
  cursor: pointer;
  font-size: 0.8rem;
  color: #3b82f6;
  user-select: none;
}
details summary:hover { text-decoration: underline; }
pre {
  margin-top: 0.5rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.8rem;
  font-size: 0.76rem;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 350px;
  overflow-y: auto;
  color: #334155;
}
"""


def render_html(data: dict) -> str:
    n_pass = data["num_passed"]
    n_total = data["num_tasks"]
    pct = 100 * n_pass / n_total if n_total else 0

    pct_cls = "bad" if pct < 50 else ""

    out = [
        "<!doctype html>",
        '<html lang="en">',
        '<head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        "<title>Deal Desk Eval</title>",
        f"<style>{CSS}</style>",
        "</head><body><div class='page'>",
        "<h1>Deal Desk Specialists — Eval Report</h1>",
        f"<p class='run-meta'>Run: {html.escape(data['timestamp'])}</p>",
        # summary bar
        "<div class='summary'>",
        f"<div class='score'>{n_pass}<span class='total'>/{n_total}</span></div>",
        f"<div class='progress-bar'><div class='fill' style='width:{pct:.0f}%'></div></div>",
        f"<div class='pct {pct_cls}'>{pct:.0f}%</div>",
        "</div>",
    ]

    # group by specialist
    by_specialist: dict[str, list] = {}
    for r in data["results"]:
        by_specialist.setdefault(r["specialist"], []).append(r)

    for specialist_key, tasks in by_specialist.items():
        label = SPECIALIST_LABELS.get(specialist_key, specialist_key)
        sp_pass = sum(1 for t in tasks if t["passed"])
        out += [
            "<div class='group'>",
            f"<div class='group-header'>{html.escape(label)} &nbsp;·&nbsp; {sp_pass}/{len(tasks)} passed</div>",
        ]
        for r in tasks:
            cls = "pass" if r["passed"] else "fail"
            badge = "PASS" if r["passed"] else "FAIL"
            out += [
                f"<div class='card {cls}'>",
                "<div class='card-head'>",
                f"<span class='badge {cls}'>{badge}</span>",
                f"<span class='task-id'>{html.escape(r['id'])}</span>",
                "</div>",
                f"<div class='task-desc'>{html.escape(r['description'])}</div>",
            ]
            if "error" in r:
                out.append(f"<div class='error-box'>{html.escape(r['error'][:600])}</div>")
            else:
                out += [
                    "<div class='metrics-row'>",
                    f"<span>model: {html.escape(r['model'])}</span>",
                    f"<span>⏱ {r['elapsed_s']}s</span>",
                    f"<span>↑ {r['input_tokens']:,} / ↓ {r['output_tokens']:,} tokens</span>",
                    "</div>",
                    "<div class='grades'>",
                ]
                for g in r["grades"]:
                    gcls = "gpass" if g["score"] == 1.0 else "gfail"
                    icon = "✓" if g["score"] == 1.0 else "✗"
                    check_short = g["check"] if len(g["check"]) <= 90 else g["check"][:90] + "…"
                    out += [
                        f"<div class='grade {gcls}'>",
                        f"<span class='icon'>{icon}</span>",
                        f"<span class='gtype'>{html.escape(g['type'])}</span>",
                        f"<span class='greason'>{html.escape(g['reason'])}</span>",
                        f"<span class='gcheck'>— {html.escape(check_short)}</span>",
                        "</div>",
                    ]
                out.append("</div>")
                out += [
                    "<details><summary>Show response</summary>",
                    f"<pre>{html.escape(r['final_text'])}</pre>",
                    "</details>",
                ]
            out.append("</div>")
        out.append("</div>")

    out += ["</div></body></html>"]
    return "\n".join(out)


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Running {len(TASKS)} tasks across {len(SPECIALIST_LABELS)} specialists…")
    data = run_eval()

    ts = time.strftime("%Y%m%d_%H%M%S")
    json_path = RESULTS_DIR / f"eval_{ts}.json"
    html_path = RESULTS_DIR / f"eval_{ts}.html"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    html_path.write_text(render_html(data), encoding="utf-8")

    print(f"\n{data['num_passed']}/{data['num_tasks']} passed ({100*data['num_passed']/data['num_tasks']:.0f}%)")
    for r in data["results"]:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"  [{mark}] {r['id']}")
        for g in r["grades"]:
            tick = "+" if g["score"] == 1.0 else "-"
            print(f"      {tick} [{g['type']}] {g['reason'][:100]}")

    print(f"\nHTML: {html_path}")
    print(f"JSON: {json_path}")


if __name__ == "__main__":
    main()
