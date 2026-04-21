"""
Marketer Agent — SEO packaging and distribution planning for Content-agent drafts.

Never rewrites prose. Adds titles, tags, meta descriptions, slugs, publish dates,
and internal-link selections. Mostly Sonnet; extractive sub-calls go to Haiku.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from anthropic import Anthropic

from agents.content_agent import Draft


MARKETER_MODEL = "claude-sonnet-4-6"
EXTRACTION_MODEL = "claude-haiku-4-5-20251001"

MARKETER_SYSTEM_PROMPT = """You are the distribution and optimization layer for the uzelhub.com content operation. Your job begins where the Content agent's job ends. You never rewrite. You never change the prose. You add the scaffolding that makes good writing findable.

The canonical publishing model is:
1. Ghost (uzelhub.com/blog) — the authoritative source, indexed first
2. Hashnode — developer audience, canonical tag points to Ghost (deferred for v1)
3. Dev.to — broader developer community, canonical tag points to Ghost (deferred for v1)

SEO rules:

TITLES:
- 50-60 characters for search display
- Lead with the problem or insight, not the technology
- Avoid clickbait — the uzelhub audience respects directness
- Include primary keyword naturally

META DESCRIPTIONS:
- 150-160 characters
- Summarize the core insight, not just the topic
- Include a soft call to action or curiosity hook

TAGS:
- 3-5 tags per post
- Mix: 1 broad, 1 specific, 1 conceptual, 1 audience tag if applicable

INTERNAL LINKING:
- Every post includes at least one link back to uzelhub.com when relevant prior posts exist
- Link anchor text is descriptive, not "click here"

You output a structured JSON object. No prose commentary. The post body is passed through unchanged.
"""

EXTRACTION_SYSTEM_PROMPT = """You extract structured data from blog posts. Output JSON only, no commentary.

You produce a descriptor for the post corpus graph:
{
  "topics": [broad subject areas, 2-4 items],
  "concepts": [specific ideas or techniques discussed, 3-6 items],
  "systems_mentioned": [named tools, libraries, services, 0-5 items],
  "decisions_made": [architectural or design choices the post describes, 0-3 items],
  "primary_keyword": [single phrase, the one thing this post is most about]
}

Keep each list item to 1-4 words. No sentences."""


@dataclass
class PostDescriptor:
    """Structured tags used by the corpus graph to rank internal-link candidates."""

    topics: list[str]
    concepts: list[str]
    systems_mentioned: list[str]
    decisions_made: list[str]
    primary_keyword: str


@dataclass
class LinkCandidate:
    """A previously drafted post considered for internal linking from this draft."""

    post_id: int
    slug: str
    title: str
    overlap_score: float


@dataclass
class MarketerOutput:
    """Marketer agent output — draft body plus all SEO packaging."""

    title: str
    slug: str
    tags: list[str]
    meta_description: str
    suggested_publish_date: date
    series: str | None
    internal_links: list[dict[str, str]]
    descriptor: PostDescriptor
    body: str
    input_tokens: int = 0
    output_tokens: int = 0
    extraction_tokens: dict[str, int] = field(default_factory=dict)


class MarketerAgent:
    """Packages a Content-agent draft for publication to Ghost."""

    def __init__(
        self,
        client: Anthropic,
        marketer_model: str = MARKETER_MODEL,
        extraction_model: str = EXTRACTION_MODEL,
    ) -> None:
        self.client = client
        self.marketer_model = marketer_model
        self.extraction_model = extraction_model

    def extract_descriptor(self, draft: Draft) -> tuple[PostDescriptor, dict[str, int]]:
        """Haiku pass — derives the JSON graph descriptor for cohesion queries."""
        import json

        response = self.client.messages.create(
            model=self.extraction_model,
            max_tokens=512,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"# {draft.title}\n\n{draft.body}",
                }
            ],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

        data = json.loads(raw)
        descriptor = PostDescriptor(
            topics=data.get("topics", []),
            concepts=data.get("concepts", []),
            systems_mentioned=data.get("systems_mentioned", []),
            decisions_made=data.get("decisions_made", []),
            primary_keyword=data.get("primary_keyword", ""),
        )
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return descriptor, usage

    def package(
        self,
        draft: Draft,
        descriptor: PostDescriptor,
        link_candidates: list[LinkCandidate],
        queue_depth: int,
    ) -> MarketerOutput:
        """Sonnet pass — produces title, meta, tags, publish date, internal links."""
        import json

        user_message = self._format_packaging_request(
            draft, descriptor, link_candidates, queue_depth
        )

        response = self.client.messages.create(
            model=self.marketer_model,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": MARKETER_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

        data = json.loads(raw)

        return MarketerOutput(
            title=data["title"],
            slug=data["slug"],
            tags=data["tags"],
            meta_description=data["meta_description"],
            suggested_publish_date=date.fromisoformat(data["suggested_publish_date"]),
            series=data.get("series"),
            internal_links=data.get("internal_links", []),
            descriptor=descriptor,
            body=draft.body,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    @staticmethod
    def _format_packaging_request(
        draft: Draft,
        descriptor: PostDescriptor,
        link_candidates: list[LinkCandidate],
        queue_depth: int,
    ) -> str:
        candidates_block = "\n".join(
            f"  - post_id={c.post_id} slug={c.slug} overlap={c.overlap_score:.2f} title={c.title!r}"
            for c in link_candidates
        ) or "  (none — corpus is empty or no overlap)"

        return (
            f"DRAFT TITLE: {draft.title}\n"
            f"DRAFT BODY (do not modify):\n{draft.body}\n\n"
            f"CONTENT AGENT NOTES:\n{draft.notes_for_marketer}\n\n"
            f"GRAPH DESCRIPTOR:\n"
            f"  topics: {descriptor.topics}\n"
            f"  concepts: {descriptor.concepts}\n"
            f"  systems: {descriptor.systems_mentioned}\n"
            f"  primary_keyword: {descriptor.primary_keyword}\n\n"
            f"INTERNAL LINK CANDIDATES (ranked by topic overlap):\n{candidates_block}\n\n"
            f"CURRENT PUBLISH QUEUE DEPTH: {queue_depth}\n\n"
            "Output JSON with keys: title, slug, tags (list), meta_description, "
            "suggested_publish_date (YYYY-MM-DD), series (or null), "
            "internal_links (list of {anchor, slug} — pick 0-2 from the candidates). "
            "No prose."
        )
