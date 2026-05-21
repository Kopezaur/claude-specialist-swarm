# 2-Minute Demo Narration — Deal Desk Specialist Swarm

## Setup
- **Monitor 1:** terminal, full-screen, ready to run `python run_deal_desk.py`
- **Monitor 2:** `outputs/BTS-Synthetic_Proposal_AcmeCorp.md` (or `.docx` once Stefan wires the docx skill) open in a viewer
- Backup proposal at `outputs/BTS-Synthetic_Proposal_AcmeCorp-baseline-backup.md` in case the live run breaks

## Script

**[0:00 — kick off the run]**
> "This is a Deal Desk. An RFP just landed from Acme Corp — enterprise data platform, multi-million dollar deal. Watch what happens."
>
> *Run `python run_deal_desk.py`.*

**[0:15 — coordinator picks up]**
> "The Senior Partner reads the RFP first — that's the orchestrator. In a real firm, this is the partner who decides who to pull in."

**[0:25 — four threads spawn]**
> "Now watch this. Four threads, spawned in parallel — Pricing, Legal, Technical Fit, Competitive Intel. Each is its own agent, each with its own skill attached. This is the swarm."

**[0:45 — replies coming back]**
> "Replies are coming back asynchronously. Pricing is still computing the commercial terms. Legal is already done — it found four contract dealbreakers. This is exactly how a real services firm runs a deal review, except we just compressed an hour of partner time into 60 seconds."

**[1:10 — critic activates]**
> "Now — and this is the part that lands the architecture pitch — the coordinator doesn't ship the draft. It sends it to a fifth agent: the Critic. The Critic is built to push back. Its only job is to tell the Senior Partner the draft isn't good enough."
>
> *Point at the `VERDICT:` line in the stream.*
>
> "Verdict: REVISE. The Senior Partner just got told to fix things. This is the partner review step, codified into the architecture."

**[1:35 — final synthesis]**
> "Coordinator addresses the critic's issues, re-submits, gets ship-it, and produces the final document."

**[1:50 — show the doc]**
> *Switch to Monitor 2.*
> "Real branded proposal. Pricing, legal positions, technical fit, competitive narrative — all synthesised. Ready to send to procurement."

**[2:00 — punchline]**
> "Coordinator plus specialists plus skills plus a critic. This is the architecture that wins the next $50M transformation deal."

## Things to point out if asked

- **"How parallel is it really?"** → All four specialist threads spawn within ~1 second of each other in the event stream. The fan-out is real.
- **"What's in a skill?"** → A markdown file with domain rules and references. Each specialist has its own (`skills/pricing-playbook/SKILL.md` etc.).
- **"Could you swap a specialist out?"** → Yes — `create_specialists.py` plus an entry in the coordinator's roster. That's the whole change.
- **"What model is the critic?"** → `claude-opus-4-7`. The critic needs to be sharp; specialists run on cheaper models.

## Failure modes (have a recovery line ready)

- **Run hangs / API error:** "We saw this earlier — that's why we have a recorded run. Here it is." → switch to Monitor 2 with the baseline output.
- **Critic returns SHIP IT on first pass:** "Sometimes the partner gets it right first try. The point is the critic *can* push back — and you can see in this earlier run where it did."
- **Markdown not docx:** "Stefan's wiring the docx skill into the coordinator right now — same flow, branded Word doc instead of markdown."
