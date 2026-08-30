"""Redaction detector — the backstop on the absolute gate.

NEWSROOM's redaction rule is absolute: nothing derived from a session log
publishes without a hard secret/PII scrub AND the Editor's approval. Until now
that gate was a doctrine, a hardcoded `redaction: required` label on every lead,
and a pill on the review page. Nothing detected anything and nothing enforced
anything — a draft could cross into uzelhub-web's notes.json, whose working tree
is the LIVE apex docroot, and be world-readable on the next generate.

This is a DETECTOR, deliberately not a scrubber. A scrubber that silently
rewrites text buys false confidence: it will miss something and be trusted
anyway. This finds candidates, hands them to a human, and refuses to let an
unresolved one through — the same "refuse loudly" contract as lead_mark and
promote_draft.

Two design rules, both learned from what makes gates get ignored:

  * HIGH PRECISION over recall. A detector that cries wolf gets clicked past,
    and then it is worse than nothing because it manufactures the habit of
    dismissing it. Every pattern here is one whose match is almost never
    innocent, and the known-innocent values are allowlisted by name.
  * NEVER auto-apply. Each finding needs an explicit verdict — redact it, or
    call it a false positive. Unresolved findings block the promote.

Why no bare 40-hex pattern: a git SHA is 40 hex characters, and commit SHAs are
*receipts* — the notes cite them deliberately and often. Flagging them would
fire on the site's most characteristic content. High-entropy strings are caught
by their assignment context instead (key=, token=, password=), which is where a
real leak actually looks like a leak.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Values that look sensitive and are deliberately public. Matching one is not a
# finding — the site publishes these on purpose.
ALLOW = {
    "contact@uzelhub.com",      # the published contact address
    "127.0.0.1", "0.0.0.0",     # loopback / bind-all, in every config
    "255.255.255.255",
}

# Hosts whose addresses are public knowledge anyway.
ALLOW_SUFFIX = ("uzelhub.com",)


@dataclass(frozen=True)
class Finding:
    kind: str          # short label, shown to the reviewer
    text: str          # the exact matched substring
    start: int         # offset into the scanned string
    end: int
    why: str           # one line: why this pattern is almost never innocent

    @property
    def key(self) -> str:
        """Stable handle for a verdict, so a decision survives a rebuild."""
        return f"{self.kind}:{self.text}"


# (kind, regex, why). Ordered most-severe first; overlapping matches resolve to
# the earlier entry.
PATTERNS: list[tuple[str, str, str]] = [
    ("anthropic key", r"sk-ant-[A-Za-z0-9_\-]{16,}",
     "An Anthropic API key prefix. There is no innocent reason for one in prose."),
    ("private key", r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----",
     "A private key header. Never publishable, in any context."),
    ("aws key id", r"\bAKIA[0-9A-Z]{16}\b",
     "An AWS access key id."),
    ("db credentials", r"\b(?:postgres(?:ql)?|mysql|mongodb|redis)://[^\s:/@]+:[^\s@]+@\S+",
     "A connection string carrying a password inline."),
    ("assigned secret",
     r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|bearer)\b"
     r"\s*[:=]\s*[\"']?([A-Za-z0-9_\-./+=]{8,})[\"']?",
     "A secret-shaped name assigned a value. The assignment is what makes it a leak."),
    ("capability url", r"\bdesk-[0-9a-f]{24,}\b",
     "An unlisted capability token — the URL IS the access control."),
    ("home path", r"/(?:home|root|Users)/[A-Za-z0-9._-]+",
     "An absolute home path leaks an account name and the machine's shape."),
    # The trailing boundary is (?![\w-]), not \b, so a match cannot stop
    # mid-token. `\b` sits happily between a letter and a hyphen, so a calendar
    # UID like some-event@director.ai-agent-platform reported as just the part
    # through the `.ai` -- a PREFIX of the token, and a false positive on every
    # ops-calendar UID appearing in prose or code. A gate that cries wolf gets
    # clicked past; see the config README's own argument for precision over
    # recall. Same idiom the gate's term_pattern already uses. The only shape
    # no longer flagged is an address written flush against a trailing hyphen,
    # which is not a shape a real address appears in.
    ("email", r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}(?![\w-])",
     "An address that is not the published contact one."),
    ("public ip", r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
     "A routable address. Loopback and private ranges are allowed."),
]

_COMPILED = [(kind, re.compile(rx), why) for kind, rx, why in PATTERNS]

_PRIVATE_IP = re.compile(
    r"^(?:10\.|127\.|0\.|169\.254\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.|22[4-9]\.|23\d\.)"
)
# A systemd template unit (notify-telegram@thing.service) is not an email.
_UNIT_LIKE = re.compile(r"@[A-Za-z0-9._-]+\.(?:service|timer|socket|target|mount|path)$")


def _allowed(kind: str, text: str) -> bool:
    if text in ALLOW:
        return True
    if kind == "email":
        if _UNIT_LIKE.search(text):
            return True                       # systemd unit, not an address
        if text.endswith(ALLOW_SUFFIX):
            return True
    if kind == "public ip" and _PRIVATE_IP.match(text):
        return True                           # loopback / private / multicast
    return False


def scan(text: str) -> list[Finding]:
    """Findings in one string, ordered by position, non-overlapping.

    Earlier PATTERNS entries win an overlap, so `db credentials` beats the
    `email`-shaped user:pass@host fragment inside it.
    """
    found: list[Finding] = []
    taken: list[tuple[int, int]] = []
    for kind, rx, why in _COMPILED:
        for m in rx.finditer(text):
            # For patterns with a capture group, the secret is the group.
            span = m.span(1) if m.groups() else m.span(0)
            body = text[span[0]:span[1]]
            if _allowed(kind, body):
                continue
            if any(span[0] < e and s < span[1] for s, e in taken):
                continue                      # already claimed by a stronger pattern
            taken.append(span)
            found.append(Finding(kind, body, span[0], span[1], why))
    return sorted(found, key=lambda f: f.start)


# Fields of a note payload that become published prose. Structural fields
# (slug, dates, the copyDraft provenance stamp) are excluded: the stamp is
# generated, not authored, and deliberately cites session ids.
PROSE_FIELDS = ("title", "tagline", "metaDescription")


def _strings(note: dict):
    """(path, string) for every publishable string in a note payload."""
    for f in PROSE_FIELDS:
        if isinstance(note.get(f), str):
            yield f, note[f]
    for i, b in enumerate(note.get("bullets") or []):
        if isinstance(b, str):
            yield f"bullets[{i}]", b
    for si, s in enumerate(note.get("sections") or []):
        if isinstance(s.get("h"), str):
            yield f"sections[{si}].h", s["h"]
        for bi, item in enumerate(s.get("body") or []):
            if isinstance(item, str):
                yield f"sections[{si}].body[{bi}]", item
            elif isinstance(item, dict):
                for lk in ("list", "numbered"):
                    for li, x in enumerate(item.get(lk) or []):
                        yield f"sections[{si}].body[{bi}].{lk}[{li}]", str(x)


def scan_note(note: dict) -> list[tuple[str, Finding]]:
    """Every finding across a note's publishable prose, as (field path, finding)."""
    out = []
    for path, s in _strings(note):
        out.extend((path, f) for f in scan(s))
    return out


REDACTED = "[redacted]"


def apply_redactions(text: str, findings: list[Finding]) -> str:
    """Replace each finding with a visible marker, right to left so offsets hold.

    A VISIBLE marker, not a blackout and not a silent deletion. On a site whose
    posture is "here are the receipts", saying plainly where something was
    withheld reads as honest; a seamless removal would quietly misrepresent the
    sentence, and a black block just imports the censor's aesthetic.
    """
    out = text
    for f in sorted(findings, key=lambda f: f.start, reverse=True):
        out = out[:f.start] + REDACTED + out[f.end:]
    return out
