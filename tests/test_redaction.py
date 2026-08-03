"""Tests for the redaction detector — the backstop on an absolute gate.

Half of these test that it FIRES. The other half, which matter more, test that
it stays QUIET: a detector that cries wolf gets clicked past, and then it is
worse than useless because it trains the habit of dismissing it. Every quiet
case below is a real string from this box's own material.

    .venv/bin/python -m pytest tests/test_redaction.py -q
"""
from __future__ import annotations

import pytest

from pipelines.writer.redaction import (
    ALLOW, PATTERNS, REDACTED, apply_redactions, scan, scan_note,
)

# ── it fires ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind,text", [
    ("anthropic key",  "leaked sk-ant-api03-AbCdEf1234567890xyzQ here"),
    ("private key",    "-----BEGIN OPENSSH PRIVATE KEY-----"),
    ("private key",    "-----BEGIN PRIVATE KEY-----"),
    ("aws key id",     "id AKIAIOSFODNN7EXAMPLE in the config"),
    ("db credentials", "postgresql://ask_writer:hunter2@db.internal:5432/app"),
    ("assigned secret", "API_KEY=4f9ab21ce77d0e5510bb"),
    ("assigned secret", 'password: "correct-horse-battery"'),
    ("assigned secret", "Authorization bearer = abcdef1234567890"),
    ("capability url", "/desk-758f0999c11a2b2e44b808df947db8c7/notes/"),
    ("home path",      "staged under /root/staging/codex-logs"),
    ("home path",      "/home/claude/.claude/projects"),
    ("email",          "write to dan.shorter@example.org"),
    ("public ip",      "the box answers on 203.0.113.44"),
])
def test_fires(kind, text):
    kinds = [f.kind for f in scan(text)]
    assert kind in kinds, f"expected {kind}, got {kinds}"


def test_finding_carries_exact_span():
    text = "before sk-ant-api03-ZZZZ1111YYYY2222 after"
    f, = [x for x in scan(text) if x.kind == "anthropic key"]
    assert text[f.start:f.end] == f.text
    assert f.text.startswith("sk-ant-")
    assert f.why  # every finding explains itself to the reviewer


# ── it stays quiet ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    # THE important one: commit SHAs are receipts. The notes cite them
    # constantly and deliberately. A bare 40-hex rule would fire on the site's
    # most characteristic content, so there deliberately isn't one.
    "commits a67f4b6 and 9cd8168ff2a0b1c3d4e5f60718293a4b5c6d7e8f closed it",
    "sha256:9caece13f10a matched the zip",
    # A systemd template unit is not an email address.
    "notify-telegram@sysadmin-daily.service fired",
    "notify-telegram@agent-platform-health.service.service",
    # The published contact address is published on purpose.
    "reach me at contact@uzelhub.com",
    # Loopback, bind-all, and private ranges are in every config on the box.
    "binds 127.0.0.1:3001 behind 0.0.0.0",
    "the container sits on 172.17.0.2 and the LAN on 192.168.1.10",
    "10.0.0.5 and 169.254.1.1 are not routable",
    # /opt paths are the entire repo's vocabulary.
    "/opt/uzelhub-web/marketing/data/notes.json",
    "/var/lib/sysadmin-agent/proposals/2026-07-28-daily.md",
    # Ordinary prose that happens to contain the trigger words.
    "the retention policy kept seven days and deleted nothing",
    "a secret handshake between two agents",   # `secret` with no assignment
    "the password was never the problem",      # `password` with no assignment
])
def test_stays_quiet(text):
    assert scan(text) == [], f"false positive: {[f.kind for f in scan(text)]}"


def test_every_allowlisted_value_is_actually_quiet():
    """The allowlist is only real if scanning its members produces nothing."""
    for value in ALLOW:
        assert scan(value) == [], f"allowlisted {value!r} still fired"


# ── overlap resolution ───────────────────────────────────────────────────────

def test_stronger_pattern_wins_an_overlap():
    """A DSN contains an email-shaped user:pass@host fragment. It must report
    as credentials — the severe reading — exactly once, not twice."""
    findings = scan("postgresql://writer:pw123456@host.internal:5432/db")
    assert [f.kind for f in findings] == ["db credentials"]


def test_findings_are_ordered_and_non_overlapping():
    text = "sk-ant-api03-AAAA1111BBBB2222 then /root/dan then bob@example.org"
    fs = scan(text)
    assert len(fs) == 3
    assert [f.start for f in fs] == sorted(f.start for f in fs)
    for a, b in zip(fs, fs[1:]):
        assert a.end <= b.start


# ── note traversal ───────────────────────────────────────────────────────────

NOTE = {
    "slug": "a-note",
    "title": "A title with /home/dan in it",
    "tagline": "Clean tagline.",
    "metaDescription": "Also clean.",
    "bullets": ["harmless", "key AKIAIOSFODNN7EXAMPLE here"],
    "sections": [{
        "h": "Heading",
        "body": [
            "A clean paragraph.",
            {"list": ["fine", "mail dan@example.org"]},
            {"numbered": ["also fine"]},
        ],
    }],
    # Generated provenance, not authored prose — cites session ids on purpose.
    "copyDraft": "Draft from lead 2026-07-12-x, session 37e71c90 turns 210-260",
}


def test_scan_note_reports_field_paths():
    paths = {p for p, _ in scan_note(NOTE)}
    assert paths == {"title", "bullets[1]", "sections[0].body[1].list[1]"}


def test_scan_note_ignores_the_provenance_stamp():
    """copyDraft is code-generated and deliberately cites session ids. Scanning
    it would fire on every single draft, which is how a gate becomes noise."""
    assert not any(p == "copyDraft" for p, _ in scan_note(NOTE))
    assert "session 37e71c90" in NOTE["copyDraft"]  # still there, just not scanned


def test_clean_note_reports_nothing():
    clean = {"title": "T", "tagline": "t", "metaDescription": "m",
             "bullets": ["a"], "sections": [{"h": "H", "body": ["b"]}]}
    assert scan_note(clean) == []


# ── applying ─────────────────────────────────────────────────────────────────

def test_apply_replaces_with_a_visible_marker():
    text = "the key sk-ant-api03-AAAA1111BBBB2222 was in the log"
    out = apply_redactions(text, scan(text))
    assert REDACTED in out
    assert "sk-ant-" not in out
    assert out.startswith("the key ") and out.endswith(" was in the log")


def test_apply_handles_multiple_findings_without_shifting_offsets():
    text = "/root/dan mailed bob@example.org from 203.0.113.44"
    fs = scan(text)
    assert len(fs) == 3
    out = apply_redactions(text, fs)
    assert out == f"{REDACTED} mailed {REDACTED} from {REDACTED}"


def test_apply_with_no_findings_is_identity():
    text = "nothing sensitive here at all"
    assert apply_redactions(text, []) == text


def test_marker_is_not_a_blackout():
    """Deliberate: a visible marker, not a censor's block and not a silent
    deletion. On a site whose posture is 'here are the receipts', saying where
    something was withheld is honest; a seamless removal misrepresents the
    sentence."""
    assert REDACTED == "[redacted]"
    assert "█" not in REDACTED     # no full block glyph
    assert REDACTED.strip() != ""       # not an empty deletion


# ── the contract itself ──────────────────────────────────────────────────────

def test_no_bare_hex_pattern_exists():
    """Regression guard. A 40-hex rule is the obvious thing to add and would
    fire on every commit SHA the notes cite as receipts. If someone adds one,
    this fails and points at why."""
    for kind, rx, _why in PATTERNS:
        assert "a-f0-9]{40" not in rx.replace(" ", ""), f"{kind} looks like a bare-SHA rule"
        assert "0-9a-f]{40" not in rx.replace(" ", ""), f"{kind} looks like a bare-SHA rule"


def test_every_pattern_explains_itself():
    for kind, _rx, why in PATTERNS:
        assert why and why[0].isupper() and why.endswith("."), kind
