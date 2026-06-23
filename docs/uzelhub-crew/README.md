# Uzelhub Crew — Documentation

The Uzelhub Crew is the agent system that turns commits from `predictor_ingest` into blog drafts in Dan's voice and publishes them to Ghost (`blog.uzelhub.com`) for Blog Director review.

Pipeline shape: `git commits → Content agent (drafts) → Marketer agents (extract + package) → Ghost (creates draft) → Blog Director review`. Each call is single-shot dataflow, not an agent loop.

---

## Live operating docs

Read these when doing ongoing work.

- **[blog-director-checklist.md](blog-director-checklist.md)** — per-draft review attentions. What to notice when a draft lands in Ghost. The attention checklist, not a rubric.
- **[prompt-tuning.md](prompt-tuning.md)** — running log of observations across drafts, plus the operating principles for *when* to tune (don't edit the prompt after one good sample) and Sprint One+ backlogs (corpus-level analysis, mermaid diagram support).

The two are paired: per-draft notable moments get logged from the checklist into prompt-tuning.md; tuning decisions emerge from patterns in the log, not single drafts.

## Historical / point-in-time

Self-labeled with status headers. Kept for reference; not part of the live operating loop.

- **[sprint-zero-kickoff.md](sprint-zero-kickoff.md)** — original Sprint Zero scaffolding plan from the cloud session.
- **[ssh-session-handoff.md](ssh-session-handoff.md)** — procedure for picking up Sprint Zero on the Hetzner VPS after the cloud session.

These can move to an archive folder when Sprint Zero work is genuinely done. For now their headers do enough self-labeling to keep them in place without contributing to drift.

---

## Where things live in code (not in docs)

Some things are code-resident by design. Look here:

| What | Where |
|---|---|
| Content agent prompt | `agents/content_agent.py` (`CONTENT_SYSTEM_PROMPT`) |
| Marketer agent prompts | `agents/marketer_agent.py` |
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
