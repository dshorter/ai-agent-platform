"""Markdown → Telegram HTML, conservatively.

Agents write ordinary markdown. Telegram renders none of it unless the send
sets a parse_mode, and until 2026-08-17 neither sender did — so every `**bold**`
and ``` fence arrived as literal punctuation.

WHY HTML AND NOT MARKDOWN. Telegram's MarkdownV2 requires escaping
`_ * [ ] ( ) ~ \\` > # + - = | { } . !` — every one of which appears constantly
in our content: file paths (dots, hyphens, slashes), diffs (+, -, @@), ordinary
prose (full stops). A single missed escape returns HTTP 400 and the message is
NOT DELIVERED. Legacy `Markdown` is barely better and does not understand the
double-asterisk bold our agents actually write. HTML needs only `& < >` escaped,
which is three characters we control completely.

WHAT IS DELIBERATELY NOT CONVERTED. Underscore emphasis. Our identifiers are
snake_case — `_pass_summary`, `email_recipient_filter` — and treating those
underscores as italics would mangle the names into unreadable fragments. The
loss is real and small; the alternative is corrupting the thing being reported.

Delivery still must not depend on this. Callers send with parse_mode=HTML and
fall back to plain text on rejection: a formatted pager message is nice, a
delivered pager message is the requirement.
"""
from __future__ import annotations

import html
import re

_FENCE = re.compile(r"```[a-zA-Z0-9_+-]*\n(.*?)```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", re.MULTILINE)
_BULLET = re.compile(r"^\s{0,3}[-*]\s+", re.MULTILINE)


def to_telegram_html(text: str) -> str:
    """Convert a markdown-ish agent message to Telegram-flavoured HTML."""
    # Fenced blocks come out first and ride as placeholders, so their contents
    # are never touched by the inline rules below — a diff is full of asterisks
    # and hashes that are punctuation, not formatting.
    blocks: list[str] = []

    def _stash(m: re.Match) -> str:
        blocks.append(m.group(1))
        return f"\x00BLOCK{len(blocks) - 1}\x00"

    out = _FENCE.sub(_stash, text)

    # Escape once, after stashing and before adding any tags of our own.
    out = html.escape(out, quote=False)

    out = _HEADING.sub(lambda m: f"<b>{m.group(1)}</b>", out)
    out = _BOLD.sub(lambda m: f"<b>{m.group(1)}</b>", out)
    out = _INLINE_CODE.sub(lambda m: f"<code>{m.group(1)}</code>", out)
    out = _BULLET.sub("• ", out)

    for i, block in enumerate(blocks):
        out = out.replace(f"\x00BLOCK{i}\x00",
                          f"<pre>{html.escape(block, quote=False)}</pre>")
    return out.strip()
