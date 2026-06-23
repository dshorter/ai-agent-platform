# Crawl-to-Publish Plan

The sequence of phases that takes the Uzelhub crew from "3 sample drafts in Ghost" to "drip-publishing pipeline operating at scale."

Captured here so picking up later doesn't require re-deriving the plan from conversation.

**Principle: follow the sequence in order, not by perceived priority.** Each phase produces an artifact the next phase depends on. Reordering creates blocking dependencies that don't show up until the work is in flight.

---

## Phase 0 — Pre-crawl prep

Small, do first. The crawl is the gating step for everything analytical; a couple of prep moves prevent the corpus from baking in fixable problems.

### 0.1 Temporal-neutrality nudge

Add one sentence to `agents/content_agent.py:CONTENT_SYSTEM_PROMPT`:

> Avoid time-anchored phrases like "this week," "yesterday," or "now." Prefer perfect tense ("I built X to do Y") so posts read accurately whenever they publish.

Why: drafts will publish weeks or months after generation. Time-anchored language breaks. Single sentence. Highest leverage move available before the crawl. The first three sample drafts already show some "this week" anchors — fixable now, not retroactively.

### 0.2 (Optional) Cache token capture

Plumb `cache_creation_input_tokens` and `cache_read_input_tokens` from the Anthropic usage object through `Draft` → `ExecutionContext` → `agent_decisions`. The backlog crawl is the load case where caching pays off; capturing the data validates the cost model with real hit-ratios.

Skip if speed-to-data matters more than cost-validation. Re-doable later.

### 0.3 (Optional) Cost cap safety net

Env var `PIPELINE_MAX_COST_USD` that aborts the run if cumulative `cost_usd` exceeds threshold. Cheap insurance against runaway crawls.

---

## Phase 1 — Backlog crawl

Single command:

```bash
python -m pipelines.blog_pipeline.runner
```

(No `--max-batches`. Dry-run output indicated ~277 batches.)

**Expected:** ~277 drafts in Ghost as `status: draft`, ~$10 total at current rates, ~couple hours wall time.

**Produces (what later phases consume):**

- ~277 rows in `posts` with full `descriptor` JSONB
- Commit→article traceability via `posts.input_id → pipeline_inputs.event_payload.commits`
- Per-call cost/token data in `agent_decisions`
- Raw markdown bodies (no header/outro/links applied — finisher runs at publish time, not here)

---

## Phase 2 — Analytical surface

Two tasks; both read from the corpus produced in Phase 1.

### 2.1 Build `pipelines/blog_pipeline/link_ranker.py`

Function: given a draft's descriptor, return top K previously-drafted posts by descriptor overlap.

Logic:

- Pull all `posts.descriptor` JSONB
- Score overlap on `topics`, `concepts`, `systems_mentioned`, `decisions_made`, `primary_keyword`
- Return top K (e.g. K=5) with overlap scores

Wire into `runner.py` between `marketer.extract` and `marketer.package`. Store ranked candidates in `posts.link_candidates` JSONB (new column).

Computed at draft time, consumed at publish time.

### 2.2 Story-arc classification

One batch pass over the corpus. Haiku-class — cheap.

For each post: read body, return one tag from a controlled vocabulary:

- `problem → diagnosis → fix`
- `attempt → failure → pivot`
- `constraint → design choice → consequence`
- `walkthrough → revealed insight`
- `delight / polish moment`
- `other`

Store in `posts.story_arc` (new column) or extend the `descriptor` JSONB.

Run once after Phase 1; switch to per-draft after to avoid re-running on every new post.

---

## Phase 3 — Blog Director review

Walk `blog-director-checklist.md` for each draft in Ghost. Mark `posts.blog_director_action`:

- `approve` → eligible for drip publish
- `iterate` → needs redraft (returns to draft pipeline)
- `discard` → never publish (kept for analysis only)
- `NULL` → not yet reviewed

Doesn't have to be sequential. The drip queue picks up approved drafts in publish-date order regardless.

Notable observations during review → log to `prompt-tuning.md` per the cadence principle. Don't tune the prompt mid-review unless a clear pattern emerges across 5+ drafts.

---

## Phase 4 — Publish infrastructure (detailed)

The biggest implementation phase. Two new components plus a small schema addition.

### 4.1 `pipelines/blog_pipeline/body_finisher.py`

Runs at **publish time, not draft time.** This is the architectural commitment that makes link-to-published-only work cleanly, and that lets posts be temporally framed at the right moment.

**Input:** a row from `posts` with `blog_director_action='approve'` and `status='draft'`.

**Output:** finished body markdown + finished body HTML, ready for Ghost.

**Operations, in order:**

1. **Header (prepend).** Templated paragraph above the body. Parameterized by:
   - Project provenance — Pipeline / Explorer / both — derived from the post's commits' file paths matched against `config/uzelhub_links.yaml` `projects.*.path_prefixes`
   - Commit date range — from `pipeline_inputs.event_payload.commits[*].author_date`, formatted as a human-readable span ("From the buildout, late April 2026 →")
   - Optionally a one-sentence bridge between the project context and the post topic

2. **Term substitution.** Apply `config/uzelhub_links.yaml` `terms:`. Word-boundary regex, first-occurrence-only per term, skip fenced code blocks.

3. **Internal links.** Read `posts.link_candidates` from the row. Filter to only currently-published candidates (`WHERE status='published'`). Insert links inline at descriptor-overlap positions, with a cap of 2–3 internal links per post.

4. **Outro (append).** Templated paragraph below the body. Parameterized by project provenance — mentions Pipeline / Explorer / Uzelhub with linked anchors from the YAML.

**Idempotency:** wrap header and outro in HTML comment markers (`<!-- crew:header -->...<!-- /crew:header -->`, similarly outro). Re-runs strip-and-replace cleanly. Term substitution and link insertion are idempotent on text that already has markdown links (won't re-link an existing link).

**Configuration:** `config/uzelhub_links.yaml` already exists with `terms:` and `projects:`. Add a `templates:` section for header and outro variants.

### 4.2 Publish pipeline — `pipelines/blog_pipeline/publisher.py`

A new entry point, separate from the draft pipeline:

```bash
python -m pipelines.blog_pipeline.publisher
```

**Logic per invocation:**

1. Query for the next eligible draft:

   ```sql
   SELECT post_id FROM posts
   WHERE blog_director_action = 'approve'
     AND status = 'draft'
     AND published_at IS NULL
   ORDER BY suggested_publish_date NULLS LAST, post_id
   LIMIT 1;
   ```

2. Run `body_finisher` on that post.
3. PUT the finished HTML to Ghost via the Admin API (same flow as the recovery exercise).
4. Trigger publish: PUT `status='published'` to Ghost.
5. Update `posts.status='published'`, `posts.published_at=now()` in DB.
6. Log decision row in `agent_decisions` (`publisher.publish` step).

If the query returns no rows, exit cleanly. The cron schedule controls drip cadence; the script just publishes one per invocation.

### 4.3 Schema changes

Two small ALTERs:

```sql
ALTER TABLE posts ADD COLUMN link_candidates JSONB;
ALTER TABLE posts ADD COLUMN story_arc VARCHAR(64);
```

Both nullable. Existing rows backfill at next pipeline pass or via batch update.

---

## Phase 5 — Operate

Cron schedule for the publish pipeline:

- Daily at 9am UTC: `0 9 * * *`
- Every 3 days at 9am: `0 9 */3 * *`
- Weekly Mondays: `0 9 * * 1`

The cron interval IS the drip rate. Script's `LIMIT 1` does the rest.

The draft pipeline (existing `runner.py`) runs on its own cadence (e.g. hourly or daily) to pick up new commits. Two cron jobs total, two independent rates.

---

## Parked (decide after corpus exists)

- **Forward-reference convention.** Editor's note vs. series-header vs. aggregator-index for posts that want to point at later posts. Static back-only links remain the link architecture; the question is just how to surface forward connections without breaking that.
- **`post_commits` join table.** Only when synthesis/follow-up posts that span multiple batches actually arise. Until then, the JSONB path covers the rare case.
- **Image hero / favicon final assets.** Separate brand-side track, not blocking pipeline work. Master OG asset already produced.
- **Marketing page for Explorer.** Currently `config/uzelhub_links.yaml` points Explorer references at `predictor/about.html` as a TODO. Becomes more pressing after first articles publish.
- **Cache-aware cost model.** If Phase 0.2 was skipped, plumb later. The data gets interesting after the corpus exists and publishing cadence is steady.

---

## Sequencing principle

**Follow the sequence.** Reordering by perceived priority introduces dependencies that block later. The order has been chosen specifically to keep each phase unblocked when its turn comes.

The only items that can move freely are inside Phase 0 (0.2 and 0.3 are optional and independent).
