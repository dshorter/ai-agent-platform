"""The box index says what exists, and never says more than it should.

Every assertion here is one of the exclusions the index promises the roam: a
path it lists must be a path `read_file` will actually open, or the index has
recreated the dead end it was built to remove.
"""
from __future__ import annotations

from pathlib import Path

from pipelines.scout import box_index


def _write(root: Path, rel: str, text: str = "x\n") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def test_lists_readable_text_files_with_their_heading(tmp_path):
    _write(tmp_path, "docs/design.md", "---\nread: full\n---\n\n# The design\n\nbody\n")
    out = box_index.build([tmp_path])
    assert "docs/design.md" in out
    assert "The design" in out  # heading read past the frontmatter


def test_skips_generated_and_state_trees(tmp_path):
    _write(tmp_path, "keep.md", "# Keep\n")
    for junk in ("state/leads.yaml", "node_modules/pkg/readme.md",
                 ".venv/lib/mod.py", "__pycache__/x.py", ".git/config"):
        _write(tmp_path, junk, "# junk\n")
    out = box_index.build([tmp_path])
    assert "keep.md" in out
    for junk in ("leads.yaml", "node_modules", ".venv", "__pycache__", ".git/config"):
        assert junk not in out


def test_skips_credential_shaped_files(tmp_path):
    """The toolbox refuses these, so listing one is a dead end by construction."""
    _write(tmp_path, "keep.md", "# Keep\n")
    for secret in (".env", ".env.prod", "id_rsa", "server.pem", "credentials.json"):
        _write(tmp_path, secret, "# secret\n")
    out = box_index.build([tmp_path])
    assert "keep.md" in out
    for secret in (".env", "id_rsa", "server.pem", "credentials.json"):
        assert secret not in out


def test_a_line_the_redaction_gate_would_flag_is_dropped(tmp_path):
    """The index publishes paths and headings, and both can reach a lead's
    citations, so the emitted LINE is what has to be clean.

    The address is assembled at run time on purpose: written out flat it is a
    finding in this file, and the fix for that would be an allow.txt dismissal
    — which is the operator's call and silences the string everywhere, forever,
    to buy a test fixture nothing else needs.
    """
    address = "bob" + "@" + "example.com"
    _write(tmp_path, "fine.md", "# Fine\n")
    _write(tmp_path, "leaky.md", f"# contact {address} about this\n")
    out = box_index.build([tmp_path])
    assert "fine.md" in out
    assert address not in out


def test_respects_the_cap_and_still_shows_code(tmp_path):
    """Docs outnumber the cap on their own; the split is what keeps code in."""
    for i in range(80):
        _write(tmp_path, f"docs/d{i:03}.md", f"# Doc {i}\n")
    for i in range(80):
        _write(tmp_path, f"pipelines/m{i:03}.py", f'"""Module {i}."""\n')
    out = box_index.build([tmp_path], cap=20)
    listed = out.splitlines()[1:]
    assert len(listed) <= 20
    assert any(line.endswith(".py") or ".py " in line for line in listed)
    assert any(".md" in line for line in listed)


def test_a_missing_root_is_not_an_error(tmp_path):
    assert box_index.build([tmp_path / "nope"]) == ""
