"""One triage pass: new-lead queue -> Wire Editor proposals + chief shadow
-> proposals artifact. Spec: publishing-automation-plan.md Phase 2.

Stateless like its siblings: connect, read the ledger fresh, two plain
calls, persist the artifact + agent_decisions spine rows, exit. Writes
NOTHING but the gitignored artifact — verdicts are applied by the operator
via lead_mark, and the Scout never sees any of this (pineapple rule).
"""
from __future__ import annotations

import datetime
import json
import logging
import re

import psycopg
from anthropic import Anthropic

from agents.scout_agent import ScoutCall
from agents.wire_editor_agent import WireEditorAgent
from pipelines.blog_pipeline.logging_context import (
    DecisionWriter,
    SequenceAwareLogManager,
)
from pipelines.blog_pipeline.pricing import compute_cost
from pipelines.director.store import complete_run, create_run
from pipelines.wire_editor.config import WireEditorConfig
from pipelines.writer import assignment

log = logging.getLogger("uzelhub_crew.wire_editor")

VERDICTS = {"claim", "spike", "hold"}
REGISTERS = {"note", "blog", "newsletter", "ticker"}


def _record(ctx, call: ScoutCall, payload: dict) -> float:
    ctx.llm_model = call.model
    ctx.llm_provider = "anthropic"
    ctx.token_count_input = call.input_tokens
    ctx.token_count_output = call.output_tokens
    ctx.token_count_cache_create = call.cache_creation_input_tokens
    ctx.token_count_cache_read = call.cache_read_input_tokens
    cost = (
        compute_cost(
            call.model,
            call.input_tokens,
            call.output_tokens,
            call.cache_creation_input_tokens,
            call.cache_read_input_tokens,
        )
        or 0.0
    )
    ctx.cost_usd = cost
    ctx.payload = payload
    return cost


def _one_line(text: str, width: int = 300) -> str:
    flat = " ".join(str(text).split())
    return flat[:width] + ("…" if len(flat) > width else "")


def _queue_text(new: list[dict], context: dict[str, list[str]]) -> str:
    lines = [f"NEW LEADS ({len(new)}):"]
    for l in new:
        lines.append(
            f"- id: {l['id']}\n  filed: {l.get('filed', '?')} | scout-register: "
            f"{l.get('register', '?')} | span: {l.get('agent_span', '?')}\n"
            f"  pitch: {_one_line(l.get('pitch', ''))}\n"
            f"  why_now: {_one_line(l.get('why_now', ''), 160)}"
        )
    for name, ids in context.items():
        lines.append(f"\nALREADY {name.upper()} ({len(ids)}): {', '.join(ids) or '(none)'}")
    return "\n".join(lines)


def _shortlist_text(new_by_id: dict[str, dict], proposals: list[dict]) -> str:
    lines = ["WIRE EDITOR SHORTLIST:"]
    for p in proposals:
        lead = new_by_id.get(p["id"], {})
        flags = f" | flags: {','.join(p.get('flags', []))}" if p.get("flags") else ""
        lines.append(
            f"- id: {p['id']}\n  pitch: {_one_line(lead.get('pitch', ''), 240)}\n"
            f"  wire: {p['verdict']} ({p.get('register', '?')}) — {p.get('reason', '')}{flags}"
        )
    return "\n".join(lines)


def _validate(proposals: list[dict], new_ids: set[str]) -> list[dict]:
    """Every new lead gets exactly one proposal; unknown ids are dropped,
    missing ones surface honestly as holds."""
    seen: dict[str, dict] = {}
    for p in proposals:
        pid = str(p.get("id", ""))
        if pid in new_ids and pid not in seen and p.get("verdict") in VERDICTS:
            if p.get("register") not in REGISTERS:
                p["register"] = "note"
            seen[pid] = p
    for missing in sorted(new_ids - set(seen)):
        seen[missing] = {
            "id": missing,
            "verdict": "hold",
            "register": "note",
            "reason": "(wire editor returned no verdict — operator judgment)",
        }
    return list(seen.values())


def _artifact(
    config: WireEditorConfig,
    stamp: datetime.datetime,
    clusters: list[dict],
    proposals: list[dict],
    shadow_by_id: dict[str, dict],
) -> str:
    q = lambda s: '"' + " ".join(str(s).split()).replace('"', "'") + '"'
    out = [
        f"# Wire Editor proposals — {stamp:%Y-%m-%d %H:%M} "
        f"(wire: {config.wire_model}, chief shadow: {config.chief_model})",
        "# Apply verdicts (the operator's pen, the artifact never self-applies):",
        "#   .venv/bin/python -m pipelines.scout.lead_mark <id> --to claimed|spiked --by editor",
        "# Concordance report: python -m pipelines.wire_editor --concordance",
        f"date: {stamp:%Y-%m-%d}",
        "clusters:",
    ]
    for c in clusters or []:
        ids = ", ".join(str(i) for i in c.get("ids", []))
        out.append(f"  - theme: {q(c.get('theme', '?'))}")
        out.append(f"    ids: [{ids}]")
    out.append("proposals:")
    for p in proposals:
        s = shadow_by_id.get(p["id"], {})
        out.append(f"  - id: {p['id']}")
        out.append(f"    wire: {p['verdict']}")
        out.append(f"    register: {p.get('register', 'note')}")
        out.append(f"    reason: {q(p.get('reason', ''))}")
        if p.get("flags"):
            out.append(f"    flags: [{', '.join(p['flags'])}]")
        out.append(f"    chief: {s.get('stance', 'silent')}")
        if s:
            out.append(f"    chief_verdict: {s.get('verdict', p['verdict'])}")
            out.append(f"    chief_reason: {q(s.get('reason', ''))}")
    return "\n".join(out) + "\n"


def run_pass(config: WireEditorConfig, dry_run: bool = False) -> dict:
    leads = assignment.load_leads(config.leads_path)
    new = [l for l in leads if l.get("status") == "new"]
    summary: dict = {"queue": len(leads), "new": len(new)}
    if not new:
        summary["skipped"] = "no new leads to triage"
        return summary
    context = {
        s: [l["id"] for l in leads if l.get("status") == s]
        for s in ("claimed", "drafted", "approved", "published", "spiked", "rejected")
    }
    new_by_id = {l["id"]: l for l in new}

    agent = WireEditorAgent(
        Anthropic(api_key=config.anthropic_api_key),
        wire_model=config.wire_model,
        chief_model=config.chief_model,
    )
    conn = psycopg.connect(config.postgres_dsn)
    log_manager = SequenceAwareLogManager(db_writer=DecisionWriter(conn))
    run_id = create_run(conn, "wire_editor")
    status = "success"
    try:
        with log_manager.task_sequence(
            task_id=str(run_id), description=f"wire_editor: triage {len(new)} new leads"
        ):
            with log_manager.tool_sequence("wire_triage", reason=f"{len(new)} new") as ctx:
                triage = agent.triage(_queue_text(new, context))
                if triage.stop_reason == "max_tokens":
                    raise SystemExit(
                        "REFUSED: triage output truncated (max_tokens) — raise "
                        "WIRE_MAX_TOKENS in agents/wire_editor_agent.py; a silent "
                        "fallback artifact would masquerade as a triage"
                    )
                data = triage.data if isinstance(triage.data, dict) else {}
                proposals = _validate(list(data.get("proposals", [])), set(new_by_id))
                cost_w = _record(
                    ctx, triage,
                    {"new": len(new), "proposals": len(proposals),
                     "stop_reason": triage.stop_reason, "dry_run": dry_run},
                )
            with log_manager.tool_sequence("chief_shadow", reason="gate-1 shadow") as ctx:
                shadow = agent.shadow(_shortlist_text(new_by_id, proposals))
                if shadow.stop_reason == "max_tokens":
                    raise SystemExit(
                        "REFUSED: chief-shadow output truncated (max_tokens) — "
                        "raise WIRE_MAX_TOKENS; partial shadow would corrupt the "
                        "concordance metric"
                    )
                sdata = shadow.data if isinstance(shadow.data, dict) else {}
                shadow_by_id = {
                    str(s.get("id")): s
                    for s in sdata.get("shadow", [])
                    if str(s.get("id")) in new_by_id
                }
                cost_c = _record(
                    ctx, shadow,
                    {"shadowed": len(shadow_by_id),
                     "differs": sum(1 for s in shadow_by_id.values() if s.get("stance") == "differ"),
                     "stop_reason": shadow.stop_reason, "dry_run": dry_run},
                )

        stamp = datetime.datetime.now()
        text = _artifact(config, stamp, data.get("clusters", []), proposals, shadow_by_id)
        summary.update(
            proposals=len(proposals),
            claims=sum(1 for p in proposals if p["verdict"] == "claim"),
            spikes=sum(1 for p in proposals if p["verdict"] == "spike"),
            holds=sum(1 for p in proposals if p["verdict"] == "hold"),
            chief_differs=sum(1 for s in shadow_by_id.values() if s.get("stance") == "differ"),
            cost_usd=round(cost_w + cost_c, 4),
        )
        if dry_run:
            print(text)
            summary["dry_run"] = True
            return summary
        config.proposals_dir.mkdir(parents=True, exist_ok=True)
        path = config.proposals_dir / f"{stamp:%Y-%m-%d}.yaml"
        if path.exists():
            path = config.proposals_dir / f"{stamp:%Y-%m-%d-%H%M}.yaml"
        path.write_text(text, encoding="utf-8")
        summary["artifact"] = str(path)
        return summary
    except Exception:
        status = "error"
        raise
    finally:
        complete_run(conn, run_id, status)
        conn.close()


def concordance(config: WireEditorConfig) -> str:
    """Wire + chief suggestions vs the operator's actual lead_mark verdicts —
    the gate-① maturity metric, read from artifacts + the ledger's stamps."""
    leads = {l["id"]: l for l in assignment.load_leads(config.leads_path)}
    files = sorted(config.proposals_dir.glob("*.yaml")) if config.proposals_dir.is_dir() else []
    if not files:
        return "no proposals artifacts yet — run a pass first"
    out, tw = [], {"wire": [0, 0], "chief": [0, 0]}
    for f in files:
        text = f.read_text(encoding="utf-8")
        rows = re.findall(
            r"^  - id: (\S+)\n    wire: (\w+)\n(?:.*\n)*?    chief: (\w+)\n"
            r"    chief_verdict: (\w+)",
            text, re.M,
        )
        n = agree_w = agree_c = decided = 0
        for lead_id, wire_v, _stance, chief_v in rows:
            lead = leads.get(lead_id, {})
            st = lead.get("status", "new")
            if st in ("new",):
                continue  # operator hasn't disposed yet
            # Operator's verdict, collapsed to the proposal vocabulary. Only
            # `spiked` counts as a spike: `rejected` means the lead WAS claimed
            # and the resulting draft failed, which is a verdict on the Writer,
            # not on this desk's routing. Folding it into "spike" would score
            # the Wire Editor down for a call it got right.
            op = "spike" if st == "spiked" else "claim"
            decided += 1
            agree_w += op == wire_v
            agree_c += op == chief_v
        n = decided
        if n:
            tw["wire"][0] += agree_w; tw["wire"][1] += n
            tw["chief"][0] += agree_c; tw["chief"][1] += n
            out.append(
                f"{f.name}: {n} disposed — wire {agree_w}/{n}, chief {agree_c}/{n}"
            )
        else:
            out.append(f"{f.name}: 0 disposed yet")
    for who, (a, n) in tw.items():
        if n:
            out.append(f"TOTAL {who}: {a}/{n} = {a / n:.0%} concordance")
    return "\n".join(out)
