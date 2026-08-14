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
from agents.seo_doctrine import load_doctrine


MARKETER_MODEL = "claude-sonnet-4-6"
EXTRACTION_MODEL = "claude-haiku-4-5-20251001"

DEFAULT_SINK = "blog"

# The ROLE half of the prompt — what this agent is and what it must emit. Stable
# across sinks, so it stays here. The SEO rules themselves are NOT here: they
# load from config/seo/<sink>.md at construction time (see agents/seo_doctrine).
#
# They used to be a literal in this string, and it drifted — the canonical
# paragraph named "uzelhub.com/blog" (the blog is blog.uzelhub.com) and called
# the corpus "indexed first", both wrong and both unnoticed for ~3 months.
# Doctrine lives in a file so it can be reviewed, diffed and drift-tested.
MARKETER_ROLE_PROMPT = """You are the distribution and optimization layer for the uzelhub content operation. Your job begins where the Content agent's job ends. You never rewrite. You never change the prose. You add the scaffolding that makes good writing findable.

You output a structured JSON object. No prose commentary. The post body is passed through unchanged."""


def build_system_prompt(sink: str = DEFAULT_SINK) -> str:
    """Role preamble + the loaded doctrine for one sink."""
    return f"{MARKETER_ROLE_PROMPT}\n\n{load_doctrine(sink)}"

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
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    extraction_tokens: dict[str, int] = field(default_factory=dict)


class MarketerAgent:
    """Packages a Content-agent draft for publication to Ghost."""

    def __init__(
        self,
        client: Anthropic,
        marketer_model: str = MARKETER_MODEL,
        extraction_model: str = EXTRACTION_MODEL,
        sink: str = DEFAULT_SINK,
    ) -> None:
        self.client = client
        self.marketer_model = marketer_model
        self.extraction_model = extraction_model
        self.sink = sink
        # Loaded here, not per-call: a missing doctrine file should fail the run
        # at construction rather than partway through a batch.
        self.system_prompt = build_system_prompt(sink)

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
        data = _parse_json_lenient(raw)
        if data is None:
            import logging
            logging.getLogger("uzelhub_crew").warning(
                "marketer.extract.parse_failed",
                extra={"raw_output": raw[:800]},
            )
            data = {}  # empty descriptor — pipeline continues with no tags

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
            "cache_creation_input_tokens": getattr(
                response.usage, "cache_creation_input_tokens", 0
            ) or 0,
            "cache_read_input_tokens": getattr(
                response.usage, "cache_read_input_tokens", 0
            ) or 0,
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

        # cache_control here is forward-compatible (see content_agent.py for
        # full note). The composed prompt (role + loaded doctrine) sits near the
        # 1024-token Sonnet cache minimum; the marker activates automatically
        # once it crosses. Composed once at construction, so it is byte-stable
        # across a batch and cacheable.
        response = self.client.messages.create(
            model=self.marketer_model,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": self.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()
        data = _parse_json_lenient(raw)
        if data is None:
            import logging
            logging.getLogger("uzelhub_crew").error(
                "marketer.package.parse_failed",
                extra={"raw_output": raw[:800]},
            )
            raise ValueError(
                "marketer.package returned unparseable output; cannot continue this batch"
            )

        return MarketerOutput(
            title=data["title"],
            slug=data["slug"],
            tags=data["tags"],
            meta_description=data["meta_description"],
            suggested_publish_date=_parse_date_lenient(
                data.get("suggested_publish_date")
            ),
            series=data.get("series"),
            internal_links=data.get("internal_links", []),
            descriptor=descriptor,
            body=draft.body,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_creation_input_tokens=getattr(
                response.usage, "cache_creation_input_tokens", 0
            ) or 0,
            cache_read_input_tokens=getattr(
                response.usage, "cache_read_input_tokens", 0
            ) or 0,
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


def _parse_date_lenient(value) -> "date | None":
    """Tolerate model output that omits or malforms suggested_publish_date.

    The publish pipeline orders by `suggested_publish_date NULLS LAST`, so
    None is a clean signal that the marketer didn't suggest a date. Better
    than crashing on a missing/null field, and more honest than fabricating
    today's date as a stand-in."""
    from datetime import date as _date

    if not value or not isinstance(value, str):
        return None
    try:
        return _date.fromisoformat(value.strip())
    except ValueError:
        return None


def _parse_json_lenient(raw: str) -> dict | None:
    """Try several strategies to extract a JSON object from a model response.

    Models occasionally wrap output in markdown fences, prefix with explanatory
    prose, or include a trailing comment. Returns the first parseable dict
    found, or None if no strategy works."""
    import json
    import re

    # Strategy 1: response is just JSON.
    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Strategy 2: wrapped in markdown code fence (```json ... ``` or ``` ... ```).
    if "```" in raw:
        # Take the first fenced block.
        try:
            after_open = raw.split("```", 1)[1]
            # Drop optional language tag on the same line as the opening fence.
            if "\n" in after_open:
                after_open = after_open.split("\n", 1)[1]
            inner = after_open.rsplit("```", 1)[0].strip()
            result = json.loads(inner)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, IndexError):
            pass

    # Strategy 3: find the first {...} block in the text and parse it.
    # Use a non-greedy outer match with DOTALL; bracket-balance heuristic for the close.
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    return None
