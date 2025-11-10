# PROJECT INSTRUCTIONS ADDITION - Template Learnings & Smart Fallback

## ADD THIS TO YOUR CLAUDE PROJECT INSTRUCTIONS:

---

## 🎯 TEMPLATE LEARNINGS DOCUMENT

When working on HVAC Digital Twin or planning future verticals (Restaurant, Law Firm, Dental, etc.), Claude should reference the template learnings document:

**Primary Location (Most Current):** `C:\Users\codes\source\repos\ai-agent-platform\docs\05-development\HVAC_Digital_Twin_Template_Learnings.md`

**Fallback Location:** Project Knowledge - "HVAC Digital Twin template learnings patterns gotchas"

**Purpose:** Contains all the n8n gotchas, workflow patterns, infrastructure wins, and business translation strategies that will accelerate building the next vertical.

**When to Reference:**
- User mentions building a new vertical (restaurant, law firm, etc.)
- User hits a technical issue that might be documented
- Before starting a new major workflow component
- When user says "remember when we solved [X]?"
- User explicitly asks "what have we learned?"

**When to Update:**
- User solves a technical gotcha (>15 min debugging)
- User discovers a reusable workflow pattern
- User finds a business translation that works
- User has an "ah-ha" moment about architecture
- Finishing a major workflow component

**Update Process:** Use Filesystem MCP to read current file, add 1-2 sentences, write back. Takes 30 seconds.

---

## 🔄 SMART DOCUMENT FALLBACK LOGIC

Claude has access to documents in TWO locations:
1. **User's Filesystem** (via Filesystem MCP) - MOST CURRENT
2. **Project Knowledge** (via project_knowledge_search) - Might be behind

### Priority Order for Document Access:

**For Living/Active Documents (that change frequently):**
```
1st: Try Filesystem MCP (user's actual working files)
2nd: Fall back to project_knowledge_search if filesystem fails
3rd: Tell user "can't find document" if both fail
```

**Documents that follow this pattern:**
- PROJECT_STATE_2025.md
- HVAC_Digital_Twin_Template_Learnings.md
- Any file in docs/05-development/ or docs/ticklers/
- workflow JSON files in n8n-workflows/
- Database schemas in database/

**For Reference/Static Documents (rarely change):**
```
1st: Try project_knowledge_search (faster, already indexed)
2nd: Fall back to Filesystem if not in project knowledge
```

**Documents that follow this pattern:**
- Solution briefs
- Architecture diagrams
- Benchmarking analysis
- Historical planning docs

### Implementation Example:

```
User: "What's in our template learnings doc?"

Claude's Logic:
1. Try: Filesystem read of docs/05-development/HVAC_Digital_Twin_Template_Learnings.md
2. If that fails: project_knowledge_search for "template learnings"
3. If both fail: "I don't see that document in either location"
```

### Why This Order?

**Filesystem First (for active docs):**
- User might have just updated it 2 minutes ago
- Git commits happen on filesystem before project knowledge upload
- Ensures Claude sees the freshest version

**Project Knowledge First (for reference docs):**
- Already indexed and searchable
- Faster retrieval
- These docs don't change often anyway

### Special Cases:

**PROJECT_STATE_2025.md:**
- ALWAYS check filesystem first
- This is THE source of truth for current project state
- User updates this frequently

**Workflow JSON files:**
- Check n8n-workflows/ directory on filesystem
- Repo is canonical, project knowledge might be stale

**Template Learnings:**
- Check filesystem first (gets updated during active development)
- Project knowledge second (in case user is asking from different machine)

---

## 📍 CRITICAL FILE PATHS REFERENCE

**When user references these, Claude knows where to look:**

### Active Development Docs (Filesystem Priority)
```
PROJECT_STATE_2025.md
  → C:\Users\codes\source\repos\ai-agent-platform\docs\PROJECT_STATE_2025.md
  → Fallback: project_knowledge_search "PROJECT_STATE_2025"

Template Learnings
  → C:\Users\codes\source\repos\ai-agent-platform\docs\05-development\HVAC_Digital_Twin_Template_Learnings.md
  → Fallback: project_knowledge_search "HVAC template learnings"

n8n Workflows
  → C:\Users\codes\source\repos\ai-agent-platform\n8n-workflows\*.json
  → Fallback: project_knowledge_search "event generator workflow"

Database Schemas
  → C:\Users\codes\source\repos\ai-agent-platform\database\*.sql
  → Fallback: project_knowledge_search "hvac database schema"
```

### Reference Docs (Project Knowledge Priority)
```
Solution Briefs
  → project_knowledge_search first
  → Fallback: Filesystem if needed

Architecture Diagrams
  → project_knowledge_search first
  → Fallback: Filesystem if needed

Historical Planning
  → project_knowledge_search first
  → These rarely need filesystem access
```

---

## 🎯 CLAUDE'S CHECKLIST FOR DOCUMENT ACCESS

When user asks about a document:

1. **Identify document type:**
   - [ ] Active development doc? → Filesystem first
   - [ ] Reference/static doc? → Project knowledge first

2. **Try primary source:**
   - [ ] Attempt access via preferred method
   - [ ] Log result (success or failure)

3. **Try fallback:**
   - [ ] If primary fails, try secondary method
   - [ ] Log result

4. **Report status:**
   - [ ] "Found in [location]" if successful
   - [ ] "Couldn't find in either location" if both fail
   - [ ] Never say "I don't have access" without trying both

5. **Use the document:**
   - [ ] Reference the content
   - [ ] Cite specific sections when relevant
   - [ ] Suggest updates if user hits documented gotchas

---

## 🔔 REMINDER PHRASES FOR CLAUDE

**When to mention template learnings:**
- "That pattern worked great - want to capture it in template learnings?"
- "We just solved that [X] issue - should we add it to the doc?"
- "Before moving to next workflow, want to update template learnings?"
- "That scenario testing saved time - worth noting for next vertical?"

**When to check filesystem vs project knowledge:**
- "Let me check the latest version on your filesystem..."
- "Found it in project knowledge, but let me verify filesystem for freshest version..."
- "Filesystem shows [X], which is more recent than project knowledge version"

---

## ⚡ TL;DR FOR CLAUDE

**Active docs (change frequently):** Filesystem → Project Knowledge  
**Static docs (rarely change):** Project Knowledge → Filesystem  
**Template Learnings:** Filesystem first, always  
**PROJECT_STATE_2025:** Filesystem first, always  
**Workflows/Database:** Filesystem first (repo is truth)  
**Solution Briefs/Architecture:** Project Knowledge first (faster)  

**Golden Rule:** Try both before saying "I don't have access"

---

## ✅ AFTER ADDING THIS TO PROJECT INSTRUCTIONS

**Test it:**
1. Start new chat
2. Ask: "What's in our template learnings?"
3. Claude should: Check filesystem first, find the doc, cite content
4. Ask: "What's our current project state?"
5. Claude should: Check filesystem PROJECT_STATE_2025.md, cite current stage

**Expected behavior:**
- Claude always tries filesystem for active docs
- Claude gracefully falls back to project knowledge
- Claude never says "I don't have access" without trying both
- Claude knows when to remind user to update template learnings

---

*Add this entire section to your Claude project instructions after the AUTO-LOAD CONTEXT section*
*Last Updated: 2025-11-06*
