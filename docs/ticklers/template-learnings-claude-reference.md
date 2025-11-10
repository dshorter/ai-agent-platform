# Template Learnings - Quick Reference for Claude

## 📍 Location
**Main Document:** `docs/05-development/HVAC_Digital_Twin_Template_Learnings.md`  
**Tickler:** `docs/ticklers/template-learnings-active.md`

## 🎯 Purpose
This is the **pattern library** for rapidly building new verticals. When Dan says "we need to build [X] Digital Twin," this doc contains the blueprint.

## 🔔 When to Remind Dan
- When finishing a major workflow component (event generator ✅, event processor, etc.)
- When hitting a technical gotcha worth documenting
- When discovering a workflow pattern that worked well
- Weekly during development sprints
- Before starting a new vertical implementation

## 📝 What Gets Captured
- ✅ n8n platform constraints and workarounds
- ✅ Workflow patterns that are reusable
- ✅ Database schema insights
- ✅ Business translation strategies
- ✅ Things that slowed development
- ✅ Infrastructure wins worth repeating

## 💬 Reminder Phrasing Examples
- "That idempotency pattern worked great - want to capture it in the template learnings?"
- "We just solved that PostgreSQL JSONB issue - should we add that gotcha to the doc?"
- "Before we move to the next workflow, want to spend 2 minutes updating template learnings?"
- "That scenario-based testing saved us time - worth noting for next vertical?"

## 🚫 What NOT to Capture
- Generic best practices available online
- One-off solutions that won't repeat
- Obvious things that don't need documentation

## ⚡ The Process
```
1. Notice insight during development
2. Open HVAC_Digital_Twin_Template_Learnings.md
3. Add 1-2 sentences in relevant section
4. Back to building (30 seconds max)
```

## 🎯 The Payoff
When building Restaurant Digital Twin or Law Firm Digital Twin:
- Read the doc (15 minutes)
- Avoid all the gotchas already solved
- Reuse proven patterns
- **Result:** 3-5 hours saved minimum per new vertical

---

**Key Philosophy:** "If Future You building the next vertical would want to know it, capture it NOW in 2 sentences."

**Last Updated:** 2025-11-06
