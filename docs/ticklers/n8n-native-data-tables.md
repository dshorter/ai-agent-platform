# n8n Native Data Tables - Feature Tickler

**Date Captured:** November 2, 2025 - 10:52 PM EST  
**Status:** DOCUMENTED BUT NOT PURSUED (Staying on Mission!)  
**Priority:** Low (Investigate AFTER HVAC Demo Complete)

---

## What We Saw

Banner notification in n8n UI:
```
"Introducing native data tables"
Data tables and Python task runner
```

---

## Why This Matters (Maybe)

**Potential Relevance:**
- Could replace PostgreSQL for some demo use cases
- Might simplify workflow state management
- Python task runner = new capability we don't have

**But Also:**
- We already have working PostgreSQL setup ✅
- Our HVAC schema is designed and deployed ✅
- Don't need another data layer right now

---

## Action Items (For Future)

**When to Investigate:**
- [ ] After HVAC Event Generator is working
- [ ] After Primary Agent workflow deployed
- [ ] After first successful demo run
- [ ] When we have 2+ hours to research properly

**Questions to Answer:**
1. Does it replace or complement PostgreSQL?
2. Can it handle relational data like our HVAC schema?
3. What's the Python task runner capability?
4. Any performance benefits over Postgres nodes?
5. Does it cost extra or require Enterprise?

**Research Resources:**
- n8n docs: https://docs.n8n.io
- n8n community forum
- Check n8n changelog/release notes

---

## Decision Log

**Why We're Not Chasing This Now:**
> "Ascension by repo is a lie" - We have working infrastructure.  
> We don't switch horses mid-stream.  
> Document the rabbit, don't chase it.  
> Stay on mission: Ship the HVAC demo.

**Revisit Date:** After first successful demo (estimated 2-3 weeks)

---

## Notes

This is the EXACT scenario where founders get distracted:
- New shiny feature appears ✨
- Sounds potentially useful
- Could "improve" what we're building
- **BUT**: We're 95% done with current approach

**The Trap:** Spending 3 hours investigating this = delaying demo by 3 hours  
**The Win:** 2-minute tickler = documented for later, mission continues

*This is what discipline looks like.*

---

**Created by:** Claude + User collaboration  
**Philosophy:** Document, don't distract. Ship, don't polish.
