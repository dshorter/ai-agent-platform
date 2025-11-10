# HVAC Digital Twin → Repeatable Template Learnings

**Document Purpose:** Lightweight capture zone for patterns, gotchas, and insights that will accelerate building the next vertical (restaurant, law firm, dental practice, etc.). Not organized. Not polished. Just CAPTURED.

**Update Philosophy:** If Future You would want to know it, 2 sentences is enough to jog the memory.

**Last Updated:** 2025-11-06

---

## 🔧 TECHNICAL GOTCHAS (The "Don't Step On This Landmine Again" List)

### n8n Platform Constraints
- **Crypto library blocked by security policy:** n8n restricts `require('crypto')` in Code nodes. Use native Crypto node instead for UUID/execution ID generation.
- **`.first()` syntax required:** When a node is set to "Run Once for All Items" mode, you must use `$input.first().json` to access data. Regular `$input.json` will fail silently.
- **PostgreSQL JSONB fields need stringification:** Any nested object being inserted into a JSONB column must be wrapped with `JSON.stringify()` or n8n will throw datatype errors.
- **Boolean coercion trap:** The string `"false"` is truthy in JavaScript. Always use actual boolean values or explicit comparisons.
- **Date format consistency:** PostgreSQL expects ISO 8601 format timestamps. Use `new Date().toISOString()` everywhere for consistency.

### Workflow Execution Patterns
- **Static data persistence:** `$getWorkflowStaticData('global')` persists between executions. Perfect for caching, but remember to implement TTL cleanup to prevent stale data.
- **Error handling in loops:** When using "Budget Checker" loop pattern, errors inside the loop don't automatically flow to error handlers. Need explicit error routing.

---

## 🎨 WORKFLOW PATTERNS THAT WORKED

### The Agentic Loop Pattern
```
State Init → Agent Logic → Validator → Gate → Decision Point → [Loop or Complete]
```
- This pattern creates self-documenting, auditable agent behavior
- Each step logs to database, making debugging trivial
- State object carries context through entire flow
- Budget checker prevents infinite loops

### Idempotency Gate Implementation
- Cache key: `scenario_name::event_type::customer_id::timestamp_prefix`
- Store in workflow static data with TTL
- Return early on cache hit to save database writes
- Update cache with generated event_id after successful insert
- **Key insight:** Idempotency at the workflow level, not database level, gives us more control

### Dual-Path Logging (Cache Hit + Cache Miss)
- Both paths converge at counter updater
- Allows different logging strategies while maintaining single exit point
- Makes debugging easier because every execution path is visible

---

## 🚨 THINGS THAT SLOWED US DOWN (And How To Avoid Next Time)

### Debugging Without Console Timestamps
- Started without timestamps in logs - pain in the ass
- Solution: `console.log('[' + new Date().toISOString() + '] NodeName - Message')`
- Standardize this pattern from Day 1 next time

### PostgreSQL Node Parameter Mysteries
- n8n's PostgreSQL node silently fails if you don't set parameters exactly right
- Always verify: Schema selected, Table selected, Columns mapped correctly
- Test with DBeaver first to verify connection and schema structure

### Workflow Testing Without Production Data
- Hard to validate event generation logic without realistic scenarios
- Solution: Pre-built scenario policies in static data (winter_emergency_surge, etc.)
- Keep 3 scenarios ready: normal, stress test, edge case

---

## 💡 INFRASTRUCTURE WINS (Reusable Components)

### Database Schema Pattern: LOG003 Sequence-Aware Logging
- `workflow_executions` table: Tracks every workflow run
- `agent_decisions` table: Tracks every agent decision with parent/child relationships
- `hvac_events` table: Domain-specific business events
- **The magic:** workflow_sequence_id ties multi-step agent flows together across workflows

### The Three-Table Strategy
1. Events table (business domain)
2. Workflow executions (infrastructure)
3. Agent decisions (intelligence layer)

This separation means:
- Business metrics live in domain tables
- Infrastructure metrics live in execution tables  
- Intelligence insights live in decision tables
- Each can scale/evolve independently

### Docker Compose + GitHub Actions Deployment
- Single source of truth: repo
- Automatic deployment on push to main
- Secrets managed via 1Password + GitHub Actions secrets
- **Win:** Deploy new workflows by just pushing JSON to repo

---

## 📊 DATA MODEL INSIGHTS

### Event Payload Strategy
- Core fields as columns for queryability: event_type, customer_id, urgency, timestamp
- Flexible metadata in JSONB payload field
- Allows schema evolution without ALTER TABLE statements
- Perfect for adding scenario-specific data without schema changes

### The scenario_name Pattern
- Every generated event includes which scenario created it
- Enables filtering test data from production data
- Allows comparing scenario outcomes
- **Future use:** Can replay scenarios or compare scenario effectiveness

### Urgency as a First-Class Field
- Not buried in metadata - it's a top-level integer (1-10)
- Enables priority queuing in event processors
- Drives routing decisions in agent logic
- Maps to business metrics (high urgency = potential revenue loss)

---

## 🎯 BUSINESS TRANSLATION MOVES

### "Scenario" Instead of "Test Case"
- Technical people say "test case"
- Business people understand "scenario"
- **Example:** "winter emergency surge" resonates better than "high-volume test #3"

### Metrics That Matter to SMBs
- Events created → Customer contacts
- Urgency level → Priority
- Estimated revenue → Dollar impact
- Processing time → Response speed
- **Key:** Every technical metric maps to a business outcome

### The "Digital Twin" Framing
- Technical: "Event generator with realistic distribution"
- Business: "Digital twin that simulates your actual business"
- Digital twin language makes it feel real, not a toy demo

---

## 🔄 PATTERNS TO REPLICATE FOR NEXT VERTICAL

### When Building Restaurant Digital Twin:
1. **Events table:** restaurant_events (reservation_request, complaint, delivery_issue, etc.)
2. **Scenarios:** lunch_rush, delivery_storm, special_event_night
3. **Customers:** Replace HVAC customers with restaurant regulars
4. **Revenue field:** Estimated order value
5. **Urgency:** Table wait time or delivery delay

### When Building Law Firm Digital Twin:
1. **Events table:** legal_events (client_intake, document_request, court_deadline, etc.)
2. **Scenarios:** trial_prep_week, intake_surge, deadline_cluster
3. **Customers:** Replace with case types
4. **Revenue field:** Estimated case value
5. **Urgency:** Deadline proximity

### The Universal Template:
```
1. Identify business events (what happens in this vertical?)
2. Create scenarios (what patterns stress the business?)
3. Map urgency to business pain (what causes customer loss?)
4. Connect to revenue (what's the dollar impact?)
5. Use same three-table pattern (events, executions, decisions)
```

---

## 🚀 SPEED WINS (Things That Made Us Faster)

### Pre-Built Scenario Library
- Having 3 scenarios ready to go = instant demo variety
- No need to manually craft test data
- Realistic distributions baked in

### Function Library in Code Nodes
- `generateRunId()`, `generateUUID()`, `actionId()` patterns
- Copy-paste between workflows
- **Next time:** Consider extracting to shared library or n8n credential

### Console Logging Standard
- Settled on `[timestamp] NodeName - Message` format
- Makes log parsing trivial
- Grep-friendly for debugging

---

## 📝 NOTES TO SELF

- Idempotency is easier at the application layer than the database layer
- State objects are your friend - pass full context, not fragments
- Three-table pattern (business, infrastructure, intelligence) is gold
- LLM-friendly JSON responses need structured prompts
- n8n static data = good for caching, needs manual TTL cleanup
- Always test database connectivity with DBeaver before blaming n8n
- Scenario names in every event = future analytics gold mine

---

## 🎓 LESSONS LEARNED

### What Worked
- Building production-grade from Day 1 (no "prototype then rebuild")
- Systematic debugging (trace execution paths, not guessing)
- Three-table logging strategy (complete observability)
- Scenario-based testing (realistic data from the start)

### What We'd Do Different
- Start with console log timestamps (saved hours of debugging)
- Document n8n quirks as we hit them (this doc!)
- Test database nodes in isolation before complex workflows
- Keep a "working patterns" library from project start

### The "Ship Beats Perfect" Mindset
- Event generator isn't perfect, but it WORKS
- Generated 30 events in production successfully
- Idempotency works, logging works, database writes work
- That's enough to move to the next workflow

---

*Remember: This doc exists to make Future Us faster. When in doubt, jot it down. Two sentences now = hours saved later.*
