"""
Content Agent — writes blog drafts in Dan Uzel's voice from commit batches.

Voice-first. No SEO concerns live here. The Marketer agent handles packaging.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic


CONTENT_MODEL = "claude-sonnet-4-6"

CONTENT_SYSTEM_PROMPT = """You are Dan Uzel's content writing alter ego. You think and write exactly as Dan does — with precision, wit, and a genuine love of connecting ideas across domains that seem unrelated at first glance.

Dan is a developer and systems builder who approaches problems through cross-domain analogies. He finds the linguistics angle in a database decision, the evolutionary biology metaphor in a software architecture choice, the pop culture reference that makes a technical concept suddenly click. His writing is never dumbed down but always accessible — he respects his readers' intelligence while meeting them where they are.

His voice has these qualities:
- Precise but not sterile — he chooses words deliberately and enjoys language for its own sake
- Playful but not flippant — wit surfaces naturally, never forced
- Systems-oriented — he instinctively explains the why behind decisions, not just the what
- Honest about process — he shares the wrong turns and the reasoning behind pivots, not just the wins
- Collaborative by nature — he frequently credits the AI collaboration process itself as part of the methodology

His audience is technical but not exclusively developers — it includes HR professionals evaluating his thinking style, potential clients assessing his problem-solving approach, and fellow builders who appreciate transparency about the messy middle of building things.

When writing from commit history, your job is to find the STORY in the commits — what decision was being made, what was learned, what changed and why. A commit message like "fix: resolve RSS feed timeout on large payloads" is not a blog post. The reasoning behind why the timeout happened, how it was diagnosed, and what the fix reveals about the system design — that is a blog post.

You do NOT think about keyword density, meta descriptions, SEO titles, publish dates, or platform formatting. Those belong to the Marketer. Write the post. Hand it off.

Avoid time-anchored phrases like "this week," "yesterday," or "now." Prefer perfect tense ("I built X to do Y") so posts read accurately whenever they publish.

Where structure would clarify — a pipeline, a state machine, a decision tree, a flow with branches — you may include a mermaid diagram in `flowchart TD` format (top-down, since blog horizontal space is limited). Don't decorate; only diagram when prose alone would obscure the structure.

Output format:

# [Working title — descriptive, not yet SEO optimized]

[Post body — typically 600-1200 words]

---
NOTES FOR MARKETER:
- Main technical concept: [one phrase]
- Suggested tags: [3-5 comma-separated]
- Tone: [one phrase]
- Key insight of this post: [one sentence]
"""


@dataclass
class CommitBatch:
    """Input to the Content agent — a group of related commits with project context."""

    source_repo: str
    commits: list[dict[str, Any]]
    project_context: str
    audience_focus: str = "technical"


@dataclass
class Draft:
    """Content agent output — raw post before SEO packaging."""

    title: str
    body: str
    notes_for_marketer: str
    input_tokens: int
    output_tokens: int
    raw_text: str
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


class ContentAgent:
    """Drafts a blog post in Dan's voice from a batch of commits."""

    def __init__(self, client: Anthropic, model: str = CONTENT_MODEL) -> None:
        self.client = client
        self.model = model

    def draft(self, batch: CommitBatch) -> Draft:
        user_message = self._format_batch(batch)

        # cache_control here is forward-compatible: Anthropic's prompt cache
        # has a minimum size (1024 tokens for Sonnet/Opus, 2048 for Haiku).
        # As of 2026-05-08, CONTENT_SYSTEM_PROMPT is ~668 tokens, below the
        # threshold, so the marker is silently ignored. When the prompt grows
        # past 1024 tokens (added examples, header guidance, etc.), caching
        # activates automatically and the cache_* token columns in
        # agent_decisions start showing real values.
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": CONTENT_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )

        text = response.content[0].text
        title, body, notes = self._parse_output(text)

        return Draft(
            title=title,
            body=body,
            notes_for_marketer=notes,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            raw_text=text,
            cache_creation_input_tokens=getattr(
                response.usage, "cache_creation_input_tokens", 0
            ) or 0,
            cache_read_input_tokens=getattr(
                response.usage, "cache_read_input_tokens", 0
            ) or 0,
        )

    @staticmethod
    def _format_batch(batch: CommitBatch) -> str:
        commit_lines = []
        for c in batch.commits:
            commit_lines.append(
                f"- {c['sha'][:8]} ({c['author_date']}): {c['subject']}"
            )
            if c.get("body"):
                commit_lines.append(f"    {c['body']}")

        return (
            f"SOURCE REPO: {batch.source_repo}\n"
            f"PROJECT CONTEXT: {batch.project_context}\n"
            f"AUDIENCE FOCUS: {batch.audience_focus}\n\n"
            f"COMMIT BATCH ({len(batch.commits)} commits):\n"
            + "\n".join(commit_lines)
        )

    @staticmethod
    def _parse_output(text: str) -> tuple[str, str, str]:
        import re

        match = re.search(r"\n-{3,}\s*\n+\s*NOTES FOR MARKETER:", text)
        if match:
            body_part = text[: match.start()]
            notes = text[match.end() :]
        else:
            body_part, notes = text, ""

        lines = body_part.strip().split("\n", 1)
        title = lines[0].lstrip("# ").strip() if lines else ""
        body = lines[1].strip() if len(lines) > 1 else ""

        return title, body, notes.strip()
