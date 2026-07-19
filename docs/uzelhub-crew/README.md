# Uzelhub Crew — Documentation

The Uzelhub Crew is the agent system that turns commits from `predictor_ingest` into blog drafts in Dan's voice and publishes them to Ghost (`blog.uzelhub.com`) for Blog Director review.

Pipeline shape: `git commits → Content agent (drafts) → Marketer agents (extract + package) → Ghost (creates draft) → Blog Director review`. Each call is single-shot dataflow, not an agent loop.

---

## Live operating docs

Read these when doing ongoing work.

- **[blog-director-checklist.md](blog-director-checklist.md)** — per-draft review attentions. What to notice when a draft lands in Ghost. The attention checklist, not a rubric.
- **[prompt-tuning.md](prompt-tuning.md)** — running log of observations across drafts, plus the operating principles for *when* to tune (don't edit the prompt after one good sample) and Sprint One+ backlogs (corpus-level analysis, mermaid diagram support).
- **[crawl-to-publish-plan.md](crawl-to-publish-plan.md)** — the active forward roadmap for the **Ghost/blog track**: pre-crawl prep → backlog crawl → analytical surface → Blog Director review → publish infrastructure → drip operate. Follow the sequence; reordering creates blocking dependencies.
- **[publishing-automation-plan.md](publishing-automation-plan.md)** (`read: full`) — the active forward roadmap for the **notes/newsroom track** (opened 2026-07-18): ledger lifecycle states → Director editorial pass → Writer tuning → scrub pre-flight → one-command publish → syndication APIs. Same sequencing rule; also names the deliberate human gates that are never phases.
- **Scout leads** — `pipelines/scout/state/leads.yaml`, the Scout's story queue (v1, shipped 2026-07-12). **Local-only, deliberately not committed:** this repo's origin is public, and leads are transcript-derived — the redaction gate (NEWSROOM, absolute) forbids publishing them unscrubbed. The Scout appends `status: new` leads; the Editor (operator today) flips to `claimed`/`spiked`. Spikes are never fed back to the Scout (pineapple rule). Runs daily at 05:45 via `scout-pass.timer` (root: ingestion reads the 0600 session logs); manually: `python -m pipelines.scout --pass` (`--dry-run` rehearses without consuming coverage). Synthesis has a bounded read-only roam (Director's ToolBox + `read_transcript`) — where it digs is its own call, and the `tool_calls` trace in `agent_decisions` records the foraging. **A/B in flight:** week of 07-13 on Fable 5, week of 07-19 on Sonnet 5, readout 07-26 (VTODOs on the ops calendar; operator judges lead quality).

The first two are paired: per-draft notable moments get logged from the checklist into prompt-tuning.md; tuning decisions emerge from patterns in the log, not single drafts. The third is the implementation roadmap that connects them at scale.

## Forward design (not yet built)

- **[NEWSROOM.md](NEWSROOM.md)** (`read: full`) — the content operation as a newsroom: the Scout / Writer / Editor org chart, the Scout in full (its sources, session-logs-read-by-cursor, the opaque scratchpad, the redaction gate), content types + editorial cadence, and the v1-vs-mature forks. The **Writer *is* the content agent**; the **Editor *is* the Director's weekly editorial pass**. Read it whole — the Scout spec spans four sections. *(Moved here from `uzelhub-web/marketing/` on 2026-07-12 to sit with the crew; a frozen `NEWSROOM.ARCHIVED.md` stays in that repo for commit history.)* **§Scout shipped as v1 on 2026-07-12** — the walk-and-file fork, operator as editor; see the Scout-leads entry above and the code table below.
- **[super-flywheel.md](super-flywheel.md)** (`read: full`) — whiteboard sketch (2026-07-13): prompt tuning for agents every __ turns, from their own observability. Three commitments captured — manual approval always, "no changes needed" is a first-class verdict, the Scout is (probably) out (pineapple rule at the meta-level). The manual ancestor is prompt-tuning.md; the content agent is the first patient when built.
- **[sysadmin-agent-design.md](sysadmin-agent-design.md)** — architectural design for the Sprint One+ Sysadmin / server maintenance agent. Scope boundaries, integration with `safe-reboot` / `backup.timer`, operating loop, tool surface, lessons-learned from the manual 2026-05-26/27 ops work. *What the agent does.*
- **[server-maintenance-agent-persona.md](server-maintenance-agent-persona.md)** — first-draft persona / prompt-shape for the same agent. Identity, voice (SRE-terse), how-it-thinks principles, what-it-refuses list, three worked examples. Pairs with the design doc. *How the agent acts.* Open questions for the operator at the end.

## Archive

Sprint Zero is genuinely done — the pipeline works, the backlog crawl ran
(all ~277 drafts created, ~2026-05-30 or earlier), and Phase 0.1 is live in
`agents/content_agent.py`. Moved to `archive/` 2026-07-11.

- **[archive/sprint-zero-kickoff.md](archive/sprint-zero-kickoff.md)** — original Sprint Zero scaffolding plan from the cloud session.
- **[archive/ssh-session-handoff.md](archive/ssh-session-handoff.md)** — procedure for picking up Sprint Zero on the Hetzner VPS after the cloud session.

---

## Where things live in code (not in docs)

Some things are code-resident by design. Look here:

| What | Where |
|---|---|
| Content agent prompt | `agents/content_agent.py` (`CONTENT_SYSTEM_PROMPT`) |
| Marketer agent prompts | `agents/marketer_agent.py` |
| Scout prompts (triage + synthesis) | `agents/scout_agent.py` |
| Scout pipeline (ingest / walk / leads) | `pipelines/scout/` — cursor, map, and the leads queue in `pipelines/scout/state/` (gitignored; leads are transcript-derived, redaction-gated) |
| Scout ore table | `scout_session_log` (Postgres) — `database/ai_agent_platform/002_scout_session_log.sql` |
| Pipeline runner / orchestrator | `pipelines/blog_pipeline/runner.py` |
| Markdown → HTML conversion | `_body_to_html` in `runner.py` (markdown-it-py + mermaid HTML-card wrap) |
| Per-model token pricing | `pipelines/blog_pipeline/pricing.py` |
| Ghost API client | `pipelines/blog_pipeline/ghost_publisher.py` |
| Commit batching | `pipelines/blog_pipeline/commit_batcher.py` |
| Sequence-aware logging + decision writer | `pipelines/blog_pipeline/logging_context.py` |
| Decision trace table | `agent_decisions` (Postgres) — populated by `DecisionWriter` |

Mermaid rendering lives in **Ghost admin → Settings → Code Injection → Site Footer** (loads `mermaid@11` from CDN). Not a repo artifact.

---

## Schema notes

The `posts` table is keyed on `ghost_post_id` (UNIQUE) and holds one row per Ghost draft. Commit→article traceability is `posts.input_id → pipeline_inputs.input_id → event_payload.commits[*].sha` — a two-hop join with one JSONB unwrap.

**Currently 1:1 input→article.** Each batch produces one article. The schema tolerates one commit appearing in multiple articles (no uniqueness constraint on commit sha across inputs), but we haven't generated that case yet.

**When many-to-many becomes real** (e.g. synthesis posts that draw from several past batches, or follow-ups revisiting earlier material), the call is whether to denormalize (list of input_ids on the post row) or add a `post_commits` join table keyed on `(post_id, commit_sha)`. The join table is the right move once cross-article commit reuse is a regular thing — it gives indexed lookups in both directions. Don't add it preemptively; the JSONB path covers the rare case.

---

## Per-draft flow

1. Pipeline runs (`python -m pipelines.blog_pipeline.runner --max-batches N`). New drafts appear in Ghost as `status: draft`.
2. Blog Director opens the draft in Ghost, clicks **Preview** (admin editor doesn't render HTML cards or run footer JS).
3. Blog Director walks through `blog-director-checklist.md` — voice, story, human stake, SEO, length, sanity, cross-sample diff.
4. Notable moments → logged in `prompt-tuning.md` as observations. One entry per pattern candidate.
5. The agent prompt is **not** touched after a single observation. Tuning waits for patterns across multiple drafts (per the cadence principle in prompt-tuning.md's preamble).
