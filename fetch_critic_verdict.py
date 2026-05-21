"""Pull the Critic's verbatim verdicts out of the last session via events."""

from pathlib import Path

from anthropic import Anthropic

session_id = Path(".last_session_id").read_text().strip()
client = Anthropic(default_headers={"anthropic-beta": "managed-agents-2026-04-01"})

# Find the critic's thread id
threads = client.beta.sessions.threads.list(session_id)
critic_thread = next(
    (t for t in threads.data if "Critic" in (t.agent.name or "")), None
)
if not critic_thread:
    raise SystemExit("No critic thread found.")
print(f"Critic thread: {critic_thread.id}\n")

# List events for that thread
events = client.beta.sessions.threads.events.list(
    thread_id=critic_thread.id, session_id=session_id
)
verdict_n = 0
for ev in events.data:
    if ev.type == "agent.message":
        verdict_n += 1
        print(f"=== Critic verdict #{verdict_n} ===")
        for block in ev.content:
            text = getattr(block, "text", None)
            if text:
                print(text)
        print()
