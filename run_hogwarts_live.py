"""
Live Hogwarts variant of Card A — sidecar to the team pipeline.

What this does (in one go):
  1. Ensures `.environment_id` exists (creates one if not)
  2. Creates fresh specialists under the calling API key
     (overwrites `.specialist_ids.json`)
  3. Uploads all 4 skills (3 existing + docx-creation), attaches the 3 domain
     skills to their matching specialists
  4. Creates a Hogwarts-branded coordinator with the docx-creation skill
     attached -- target filename: hogwarts-proposal-v3.docx
     (overwrites `.coordinator_id`)
  5. Streams a deal-desk session against the RFP
  6. Downloads any deliverables produced by the agents to outputs/

This does NOT modify the team's create_*/upload_skills.py scripts.

Usage:
    python run_hogwarts_live.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from anthropic import Anthropic
from anthropic.lib import files_from_dir


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent
RFP_PATH = ROOT / "synthetic-data" / "rfp-acme-corp.md"
SUPPORTING = [
    ROOT / "synthetic-data" / "past-wins.json",
    ROOT / "synthetic-data" / "product-overview.md",
]
OUTPUT_DIR = ROOT / "outputs"
SKILLS_ROOT = ROOT / "skills"

# Specialist roster (same models as create_specialists.py after today's upgrade)
SPECIALISTS = [
    {"key": "pricing",     "name": "Pricing Specialist",        "model": "claude-sonnet-4-6"},
    {"key": "legal",       "name": "Legal Reviewer",            "model": "claude-sonnet-4-6"},
    {"key": "technical",   "name": "Technical Fit Specialist",  "model": "claude-sonnet-4-6"},
    {"key": "competitive", "name": "Competitive Intel Analyst", "model": "claude-sonnet-4-6"},
]

# Domain skills attached to specialists. docx-creation goes on the coordinator.
SKILL_TO_SPECIALIST = {
    "pricing-playbook":  "pricing",
    "legal-checklist":   "legal",
    "competitive-intel": "competitive",
}
COORDINATOR_SKILLS = ["docx-creation"]


# ---------------------------------------------------------------------------
# System prompts (lifted from the team scripts, with Hogwarts overrides)
# ---------------------------------------------------------------------------

PRICING_SYSTEM = (
    "You are the Pricing Specialist on the Hogwarts engagement. You decide commercial "
    "terms for inbound RFPs.\n\n"
    "Inputs you'll receive:\n"
    "- The RFP text\n"
    "- The pricing-playbook skill (your authoritative pricing rules)\n"
    "- past-wins.json (recent comparable deals)\n\n"
    "IMPORTANT — the client's commercial demands you must address explicitly:\n"
    "- 35% discount off list (our max for this deal size is 25% standard / 30% strategic)\n"
    "- Net 90 payment terms (our standard is Net 30; Net 60 is the max acceptable)\n"
    "- 5-year fixed pricing with NO escalators (our playbook requires CPI+2% on 3-year+ terms)\n"
    "- Most Favoured Nation clause (we never accept MFN — see playbook)\n"
    "For each, state whether it is non-starter, negotiable, or acceptable, with exact counter-language.\n\n"
    "Output (~500 words):\n"
    "1. Recommended tier + annual list price for this scope\n"
    "2. Recommended discount band and rationale — cite past-wins.json comparables\n"
    "3. Term and payment structure: what we offer vs. what they asked\n"
    "4. Red lines: which of their demands we will not accept, and exact counter-language\n"
    "5. Concessions we will make to close (ranked by cost to us)\n"
    "6. Margin risk summary\n"
    "7. Deal recommendation: bid aggressively / bid with conditions / consider walking away\n\n"
    "Be specific about numbers. Cite the past-wins data when you use it."
)

LEGAL_SYSTEM = (
    "You are the Legal Reviewer on the Hogwarts engagement. You flag contractual risk and "
    "propose counter-positions.\n\n"
    "Inputs:\n"
    "- The RFP text\n"
    "- The legal-checklist skill (your authoritative position library)\n\n"
    "Work through ALL TEN checklist categories systematically. Flag deviations even when "
    "the RFP is silent — silence often means their standard terms apply.\n\n"
    "Per flag use this exact format:\n"
    "  ITEM [N] — [CATEGORY NAME]\n"
    "  RFP says: [exact or paraphrased RFP requirement]\n"
    "  Severity: BLOCKER / NEGOTIABLE / ACCEPTABLE\n"
    "  Why: [conflict with our standard]\n"
    "  Counter: [exact language we will propose]\n\n"
    "End with the AGGREGATE RISK MATRIX as required by the skill."
)

TECHNICAL_SYSTEM = (
    "You are the Technical Fit Specialist on the Hogwarts engagement. You assess our "
    "product's capability fit against the RFP.\n\n"
    "Inputs:\n"
    "- The RFP text\n"
    "- product-overview.md (the canonical capability map)\n\n"
    "Pay special attention to:\n"
    "- Real-time ingest at 80,000 events/second\n"
    "- Native Power BI integration (explicitly non-negotiable)\n"
    "- Multi-region deployment with EU data residency\n"
    "- 99.99% SLA commitment vs. our standard 99.95%\n"
    "- 2027 Teradata decommission deadline — is our timeline compatible?\n\n"
    "Output (~400 words):\n"
    "1. Requirements we meet fully\n"
    "2. Requirements we meet partially — state exactly what's missing\n"
    "3. Requirements we don't meet\n"
    "4. Overall fit score: HIGH / MEDIUM / LOW with one-sentence rationale\n"
    "5. Implementation timeline (weeks to first prod workload + weeks to full migration)\n"
    "6. The single most important risk for the coordinator to address"
)

COMPETITIVE_SYSTEM = (
    "You are the Competitive Intel Analyst on the Hogwarts engagement.\n\n"
    "Inputs:\n"
    "- The RFP text\n"
    "- The competitive-intel skill (your battlecard library)\n\n"
    "The client has disclosed their shortlist in Section 6: Databricks, Snowflake, "
    "Microsoft Fabric, and an unnamed regional vendor. Analyse these four specifically — "
    "do NOT guess. The client is a Microsoft shop on Azure primary, which makes Fabric "
    "their default-path option.\n\n"
    "Output (~400 words):\n"
    "1. Per competitor: strengths against us on this deal, weaknesses we exploit, one-line counter\n"
    "2. Ranked shortlist with primary target to displace\n"
    "3. Our two best positioning angles\n"
    "4. One trap to avoid\n"
    "5. Win probability: HIGH / MEDIUM / LOW with one-sentence rationale"
)

SPECIALIST_PROMPTS = {
    "pricing":     PRICING_SYSTEM,
    "legal":       LEGAL_SYSTEM,
    "technical":   TECHNICAL_SYSTEM,
    "competitive": COMPETITIVE_SYSTEM,
}

COORDINATOR_SYSTEM = """\
You are the Senior Partner at HARRY POTTER'S CREW running the Deal Desk for the
HOGWARTS engagement. An inbound RFP has arrived. Your job is to orchestrate the
specialists, synthesise their work, and produce a single branded Word document.

# Firm and client identity (non-negotiable)

- Our firm name is **Harry Potter's Crew** — use it consistently throughout the doc.
- The client we are responding to is **Hogwarts**.
- The RFP body refers to "Acme Corp" because it is the synthetic source document;
  treat that as the legal entity for the deal but BRAND the deliverable as
  Harry Potter's Crew for Hogwarts (header, footer, cover page).

# Your roster

You can call these specialists:
- Pricing Specialist: commercial terms recommendation
- Legal Reviewer: contract flags and counter-positions
- Technical Fit Specialist: product capability fit
- Competitive Intel Analyst: who else is in the deal and how to position

# How to run the deal

1. Read the RFP yourself. Flag known non-starters (uncapped liability, MFN,
   35% discount, no escalators over 5 years).
2. Delegate to ALL FOUR specialists in parallel. Each gets the full RFP +
   supporting documents and a clear, narrow brief (~500 words back).
3. After all specialists return, reconcile any conflicts explicitly —
   don't smooth them over.
4. Synthesise into a proposal. Cover: exec summary (3 bullets),
   understanding of client need, technical fit, implementation plan tied
   to the 2027 Teradata deadline, commercial proposal with 5-year pricing,
   contract approach (accept / counter / blocker), competitive
   differentiation, customer references, risk register.

# Final deliverable — required

Produce the final document by invoking the **docx-creation** skill you have
attached. The skill enforces:
  - Gryffindor palette (deep red #7F0909, gold #FFC500, dark red #3C0000,
    cream #FFF8E7)
  - Mandatory header on every page: "Harry Potter's Crew  →  Hogwarts"
  - Mandatory footer on every page: "Harry Potter's Crew · Prepared for
    Hogwarts · Confidential · Page X of Y"
  - Cover page rendering "Harry Potter's Crew / for / Hogwarts"
  - 9-section structure (cover, TOC, exec summary, understanding,
    approach, commercials, timeline, why us, appendix)
  - At least one chart/visualisation (use matplotlib via the skill helpers)
  - Post-save validation: firm + client must appear in the footer

The filename MUST be: **hogwarts-proposal-v3.docx**

The deliverable is the docx itself, not a chat message.

# Tone

Senior partner running a real deal. Confident, terse, decisive.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client() -> Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")
    return Anthropic(
        default_headers={"anthropic-beta": "managed-agents-2026-04-01"}
    )


def ensure_environment(client: Anthropic) -> str:
    path = ROOT / ".environment_id"
    if path.exists():
        existing = path.read_text().strip()
        print(f"[env]    reusing {existing}")
        return existing
    print("[env]    creating new cloud environment...")
    env = client.beta.environments.create(
        name="hogwarts-swarm-env",
        config={"type": "cloud", "networking": {"type": "unrestricted"}},
    )
    path.write_text(env.id)
    print(f"[env]    created {env.id}")
    return env.id


def create_specialists(client: Anthropic) -> dict[str, str]:
    print("[spec]   creating specialists (under your API key)...")
    ids: dict[str, str] = {}
    for spec in SPECIALISTS:
        agent = client.beta.agents.create(
            name=spec["name"],
            model=spec["model"],
            system=SPECIALIST_PROMPTS[spec["key"]],
            tools=[{"type": "agent_toolset_20260401"}],
            metadata={
                "hackathon": "partner-basecamp-2026",
                "track": "specialist-swarm-hogwarts",
                "role": spec["key"],
            },
        )
        ids[spec["key"]] = agent.id
        print(f"[spec]   created {spec['name']:32s} -> {agent.id}")
    (ROOT / ".specialist_ids.json").write_text(json.dumps(ids, indent=2))
    return ids


def upload_all_skills(client: Anthropic, specialist_ids: dict[str, str]) -> dict[str, str]:
    print("[skill]  uploading skills (3 specialist + docx-creation)...")
    existing_by_title: dict[str, str] = {}
    for page in client.beta.skills.list(source="custom"):
        existing_by_title[page.display_title] = page.id

    uploaded: dict[str, str] = {}
    all_skills = list(SKILL_TO_SPECIALIST.keys()) + COORDINATOR_SKILLS
    for skill_name in all_skills:
        skill_dir = SKILLS_ROOT / skill_name
        if not (skill_dir / "SKILL.md").exists():
            print(f"[skill]  skipping {skill_name} — no SKILL.md")
            continue
        display_title = skill_name.replace("-", " ").title()
        if display_title in existing_by_title:
            skill_id = existing_by_title[display_title]
            print(f"[skill]  reusing {skill_name:18s} -> {skill_id}")
        else:
            print(f"[skill]  uploading {skill_name}...")
            skill = client.beta.skills.create(
                display_title=display_title,
                files=files_from_dir(str(skill_dir)),
            )
            skill_id = skill.id
            print(f"[skill]  uploaded {skill_name:18s} -> {skill_id}")
        uploaded[skill_name] = skill_id

    # Attach domain skills to their specialists
    for skill_name, specialist_key in SKILL_TO_SPECIALIST.items():
        if skill_name not in uploaded:
            continue
        specialist_id = specialist_ids[specialist_key]
        current = client.beta.agents.retrieve(specialist_id)
        already = any(
            s.get("skill_id") == uploaded[skill_name] for s in (current.skills or [])
        )
        if already:
            print(f"[skill]  {skill_name} already attached to {specialist_key}")
            continue
        new_skills = list(current.skills or []) + [
            {"type": "custom", "skill_id": uploaded[skill_name], "version": "latest"}
        ]
        client.beta.agents.update(specialist_id, version=current.version, skills=new_skills)
        print(f"[skill]  attached {skill_name} -> {specialist_key}")

    (ROOT / ".skill_ids.json").write_text(json.dumps(uploaded, indent=2))
    return uploaded


def create_coordinator(
    client: Anthropic,
    specialist_ids: dict[str, str],
    skill_ids: dict[str, str],
) -> str:
    print("[coord]  creating Hogwarts-branded coordinator...")
    coord_skills = [
        {"type": "custom", "skill_id": skill_ids[s], "version": "latest"}
        for s in COORDINATOR_SKILLS
        if s in skill_ids
    ]
    coord = client.beta.agents.create(
        name="Harry Potter's Crew — Senior Partner (Hogwarts)",
        model="claude-opus-4-7",
        system=COORDINATOR_SYSTEM,
        tools=[{"type": "agent_toolset_20260401"}],
        skills=coord_skills,
        multiagent={
            "type": "coordinator",
            "agents": [
                {"type": "agent", "id": agent_id}
                for agent_id in specialist_ids.values()
            ],
        },
        metadata={
            "hackathon": "partner-basecamp-2026",
            "track": "specialist-swarm-hogwarts",
            "role": "coordinator",
        },
    )
    (ROOT / ".coordinator_id").write_text(coord.id)
    print(f"[coord]  created {coord.id}")
    print(f"[coord]  skills attached: {[s['skill_id'] for s in coord_skills]}")
    return coord.id


def load_context() -> str:
    blocks = []
    for path in [RFP_PATH, *SUPPORTING]:
        if not path.exists():
            print(f"  WARNING: {path} missing")
            continue
        blocks.append(f"=====  DOCUMENT: {path.name}  =====\n{path.read_text()}")
    return "\n\n".join(blocks)


def run_session(client: Anthropic, coordinator_id: str, environment_id: str) -> None:
    print("[run]    starting session...")
    session = client.beta.sessions.create(
        agent=coordinator_id,
        environment_id=environment_id,
        title="Hogwarts Deal Desk — live run",
    )
    (ROOT / ".last_session_id").write_text(session.id)
    print(f"[run]    session {session.id}")

    user_message = (
        "An RFP has just landed. Please run the standard Deal Desk process:\n"
        "1. Read the RFP yourself.\n"
        "2. Delegate to all four specialists in parallel.\n"
        "3. Synthesise their replies.\n"
        "4. Produce the final proposal response as a branded Word document\n"
        "   using the docx-creation skill. Filename MUST be hogwarts-proposal-v3.docx.\n\n"
        "Move fast — the RFP deadline is real.\n\n"
        f"{load_context()}"
    )

    print("\n=== EVENT STREAM ===\n")
    transcript_parts: list[str] = []
    with client.beta.sessions.events.stream(session.id) as stream:
        client.beta.sessions.events.send(
            session.id,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": user_message}],
                }
            ],
        )
        for event in stream:
            t = event.type
            if t == "session.thread_created":
                print(f"  [thread spawned]   {event.agent_name}", flush=True)
            elif t == "session.thread_status_running":
                name = getattr(event, "agent_name", "?")
                print(f"  [thread running]   {name}", flush=True)
            elif t == "agent.thread_message_received":
                print(f"  [reply <-]         {event.from_agent_name}", flush=True)
            elif t == "agent.thread_message_sent":
                print(f"  [delegate ->]      {event.to_agent_name}", flush=True)
            elif t == "agent.message":
                for block in event.content:
                    if getattr(block, "type", None) == "text":
                        transcript_parts.append(block.text)
                        print(block.text, end="", flush=True)
            elif t == "agent.tool_use":
                print(f"\n  [tool: {getattr(event, 'name', '?')}]", flush=True)
            elif t == "session.status_idle":
                print("\n\n[swarm finished]")
                break

    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "hogwarts-coordinator-transcript.txt").write_text("".join(transcript_parts))
    print(f"\nTranscript saved to {OUTPUT_DIR / 'hogwarts-coordinator-transcript.txt'}")

    # Download deliverables
    print("\n[run]    downloading deliverables...")
    files = client.beta.files.list(
        scope_id=session.id,
        betas=["managed-agents-2026-04-01"],
    )
    count = 0
    for f in files.data:
        out_path = OUTPUT_DIR / f.filename
        print(f"  {f.filename}  ->  {out_path}")
        content = client.beta.files.download(f.id)
        content.write_to_file(str(out_path))
        count += 1
    if count == 0:
        print("  (no files produced)")
    else:
        print(f"\nDownloaded {count} file(s) to {OUTPUT_DIR}/")

    print(f"\nView session at:")
    print(f"  https://platform.claude.com/sessions/{session.id}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    client = _client()
    env_id = ensure_environment(client)
    specialist_ids = create_specialists(client)
    skill_ids = upload_all_skills(client, specialist_ids)
    coord_id = create_coordinator(client, specialist_ids, skill_ids)
    run_session(client, coord_id, env_id)


if __name__ == "__main__":
    main()
