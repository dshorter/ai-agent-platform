"""The content-type vocabulary must be the same word list everywhere.

`spec-content-types.md` is the Editor's routing table and has carried FIVE
types since it was written: ticker, newsletter, note, blog, and paper. The
Scout's pitch schema carried four. So the fifth type was structurally
unpitchable — and worse than absent, because `wire_editor/run.py` coerced any
unknown value to "note" with no log at all. A value that can be produced but
not routed is invisible by construction, which is the same shape as the NOT
NULL foreign key that made five of six sources unable to produce a jewel
(`jewels-are-transcript-only-2026-09-03.md`).

Found and closed 2026-09-06 by adding `paper`, scoped deliberately: a rough
ABSTRACT WITH REFERENCES, never the paper itself. The sink stays unplaced,
which the spec says is intentional.

Renamed 2026-09-06: the field was called `register` until the glossary
reserved that word for the tonal band a surface writes in (a property OF a
type, never the type itself). The word here, at every site, is `type`.

This file states the vocabulary independently rather than importing it from one
of the sites — the same reasoning `test_stop_guards.py` gives for keeping its
own copy of the non-streaming cap. A test that imported the list could never
catch a site drifting away from it.
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# The routing table's five types, in the Scout's vocabulary.
TYPES = {"ticker", "newsletter", "note", "blog", "paper"}


def _pipe_enums(path: str) -> list[set[str]]:
    """Every `"type": "a|b|c"` literal in a source file, as sets.

    The alternation is required, not optional: unlike `register`, the word
    `type` is also the JSON-schema keyword, so `"type": "object"` and
    `"type": "ephemeral"` sit in the same files as the routing enums. Matching
    only pipe-separated values is what keeps this test about the vocabulary.
    """
    text = (REPO / path).read_text()
    return [set(m.split("|")) for m in
            re.findall(r'"type":\s*"([a-z]+(?:\|[a-z]+)+)"', text)]


def _list_literal(path: str, name: str) -> set[str]:
    """A module-level `NAME = [...]` or `NAME = {...}` of bare strings."""
    text = (REPO / path).read_text()
    m = re.search(rf"^{name}\s*=\s*[\[{{]([^\]}}]+)[\]}}]", text, re.M)
    assert m, f"{name} not found in {path}"
    return set(re.findall(r'"([a-z]+)"', m.group(1)))


def test_the_scout_can_pitch_every_type_the_editor_routes():
    """The gap that motivated this file: five types routed, four pitchable."""
    for enum in _pipe_enums("agents/scout_agent.py"):
        assert enum == TYPES


@pytest.mark.parametrize("path", ["agents/wire_editor_agent.py"])
def test_the_wire_editor_can_suggest_every_type(path):
    """The Editor sorts by type, so it needs the whole table — both its
    proposal schema and the chief's shadow schema."""
    enums = _pipe_enums(path)
    assert len(enums) == 2, "expected the proposal and shadow schemas"
    for enum in enums:
        assert enum == TYPES


def test_every_consumer_knows_every_type():
    """A type missing from one of these is silently mis-binned, not an error:
    wire_editor coerces to 'note', and the assay simply has no row for it — so
    the lead vanishes from the one instrument built to be unflattering."""
    assert _list_literal("pipelines/wire_editor/run.py", "TYPES") == TYPES
    assert _list_literal("tools/leads_assay.py", "TYPES") == TYPES
    assert _list_literal("tools/draft_review.py", "    order") == TYPES


def test_the_unknown_type_fallback_is_not_silent():
    """The fallback to 'note' is correct; doing it without a word was the bug.
    It ran that way from the day it was written."""
    text = (REPO / "pipelines/wire_editor/run.py").read_text()
    block = text[text.index('if p.get("type") not in TYPES'):][:900]
    assert "log.warning" in block, (
        "an unknown type must announce itself — a silent coercion is how "
        "the fifth content type stayed invisible"
    )


def test_the_word_register_is_not_the_content_type_anywhere():
    """The rename's own guard. `register` is the tonal band (a property of a
    type) and `registered` is an unrelated verb (project roots, a bot menu).
    Neither may name the content type again — that collision is what made the
    word unreadable in the first place."""
    # Scoped to the desks that carry a content type. The Director and the
    # sysadmin use `register` as an ordinary verb (registered project roots,
    # register the bot menu) and are not part of this vocabulary.
    scope = ("agents/", "pipelines/scout/", "pipelines/wire_editor/",
             "pipelines/writer/", "tools/")
    bad = []
    for path in sorted(REPO.glob("**/*.py")):
        rel = path.relative_to(REPO).as_posix()
        if not rel.startswith(scope):
            continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            for m in re.finditer(r"\bregister\w*", line, re.I):
                word = m.group(0).lower()
                if word.startswith("registered") or word.startswith("registering"):
                    continue  # the verb: registered project roots, register the menu
                bad.append(f"{rel}:{n}: {line.strip()[:110]}")
    # The tonal-band sense is allowed, and only at these sites.
    allowed = {
        "agents/sysadmin_agent.py",  # "terse SRE pager-note register" — voice
    }
    leaks = [b for b in bad if b.split(":")[0] not in allowed]
    assert not leaks, "register is the tonal band, never the content type:\n" + "\n".join(leaks)
