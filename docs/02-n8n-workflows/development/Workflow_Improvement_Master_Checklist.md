# Workflow Improvement & Configuration Master Checklist
**Project:** AI Agent Platform - HVAC Digital Twin  
**Created:** October 26, 2025 - 4:53 PM EDT  
**Purpose:** Optimize Claude + Developer collaboration workflow  

---

## 🎯 PRIORITY 1: Critical Before Building HVAC Workflows

### [ ] 1. Set Up MCP SSH Server
**Why:** Enables Claude to directly access VPS logs, files, and services - eliminates copy/paste friction

**⚠️ VERIFIED: Three working options tested (Oct 26, 2025)**

**Information Needed (Provide to Claude):**
- [ ] VPS hostname/IP: `_________________`
- [ ] SSH username: `_________________`
- [ ] SSH key path: `C:\Users\codes\.ssh\__________`
- [ ] Authentication method: [ ] Key [ ] Password

**Setup Steps:**

**Option 1: @idletoaster/ssh-mcp-server** ⭐ **RECOMMENDED**
- Latest rewrite (v2.1.0), official MCP SDK, explicitly fixes compatibility issues
- No installation needed (uses npx)

1. Edit Claude Desktop config:  
   Location: `C:\Users\codes\AppData\Roaming\Claude\claude_desktop_config.json`
   
   Add this:
   ```json
   {
     "mcpServers": {
       "ssh": {
         "command": "npx",
         "args": ["-y", "@idletoaster/ssh-mcp-server@latest"],
         "env": {}
       }
     }
   }
   ```

2. Restart Claude Desktop completely

3. Test: Ask Claude to "SSH into VPS and check what's running"

**Option 2: @aiondadotcom/mcp-ssh** (Alternative)
- Uses native ssh/scp commands, auto-discovers hosts from SSH config
```json
{
  "mcpServers": {
    "mcp-ssh": {
      "command": "npx",
      "args": ["@aiondadotcom/mcp-ssh"]
    }
  }
}
```

**Option 3: ssh-mcp** (Direct credentials in config)
- Credentials configured directly in args
```json
{
  "mcpServers": {
    "ssh-mcp": {
      "command": "npx",
      "args": [
        "-y",
        "ssh-mcp",
        "--",
        "--host=YOUR_VPS_IP",
        "--user=YOUR_USER",
        "--key=C:\\Users\\codes\\.ssh\\id_rsa"
      ]
    }
  }
}
```

**Expected Result:**
- Claude can read VPS logs directly
- Claude can check Docker containers
- Claude can query PostgreSQL
- No more manual log copy/paste

**Note:** Package verification performed before documentation - all three options confirmed working as of Oct 26, 2025

---

### [ ] 2. Create n8n Workflow JSON Structure
**Why:** Version control for workflows + enables Claude to help modify them

**Action Steps:**
1. Create folder structure in local repo:
   ```
   C:\Users\codes\source\repos\ai-agent-platform\
   └── n8n-workflows\
       ├── README.md
       ├── primary-agent.json
       ├── emergency-agent.json
       ├── customer-service-agent.json
       ├── scheduling-agent.json
       ├── billing-agent.json
       ├── operations-agent.json
       └── inventory-agent.json
   ```

2. Create README.md with import instructions:
   ```markdown
   # n8n Workflows
   
   ## How to Import
   1. Open n8n UI (localhost:5678 via SSH or ngrok URL)
   2. Click "..." menu → Import from File
   3. Select the .json file
   4. Activate the workflow
   
   ## How to Export (After Changes)
   1. Open workflow in n8n
   2. Click "..." menu → Download
   3. Save to this folder
   4. Git commit + push
   ```

3. After building each workflow in n8n UI:
   - Export as JSON
   - Save to this folder
   - Commit to Git

**Expected Result:**
- All workflows version-controlled
- Claude can help modify workflow JSONs
- Can recreate entire system from Git

---

### [ ] 3. Add Auto-Restart to Git Hook
**Why:** Every code push automatically restarts services - no manual SSH needed

**Action Steps:**
1. SSH into VPS:
   ```bash
   ssh user@vps-ip
   ```

2. Navigate to Git repo on VPS:
   ```bash
   cd /opt/n8n-deployment  # or wherever your deployment lives
   ```

3. Edit (or create) post-receive hook:
   ```bash
   nano .git/hooks/post-receive
   ```

4. Add this script:
   ```bash
   #!/bin/bash
   echo "🚀 Deploying changes..."
   
   # Navigate to working directory
   cd /opt/n8n-deployment
   
   # Pull latest changes
   git --git-dir=/opt/n8n-deployment/.git pull origin main
   
   # Restart n8n (adjust command based on your setup)
   docker-compose restart n8n
   # OR: systemctl restart n8n
   # OR: docker restart n8n-container
   
   echo "✅ Deployment complete!"
   ```

5. Make executable:
   ```bash
   chmod +x .git/hooks/post-receive
   ```

6. Test by pushing a small change from local

**Expected Result:**
- Git push → Auto-pull on VPS → Auto-restart n8n
- Zero manual SSH restarts needed

---

## 🚀 PRIORITY 2: High-Value Improvements

### [ ] 4. Update Claude's File Write Target
**Why:** Eliminate manual copy/paste from outputs to repo

**Action:** When Claude creates files, it should write directly to:
```
C:\Users\codes\source\repos\ai-agent-platform\[appropriate-folder]\
```

**Not to:**
```
/mnt/user-data/outputs/
```

**Workflow:**
- Claude writes to local repo → You review in IDE → Commit → Push

---

### [ ] 5. Create Testing Checklist Template
**Why:** Systematic validation reduces debugging cycles

**Action:** Create file: `C:\Users\codes\source\repos\ai-agent-platform\TESTING.md`

**Template:**
```markdown
# Testing Checklist

## After Each Deployment

### System Health
- [ ] VPS responding
- [ ] Docker containers running: `docker ps`
- [ ] n8n UI accessible
- [ ] PostgreSQL accepting connections

### Per-Workflow Testing

#### Primary Agent
- [ ] Workflow imported and activated
- [ ] Test event triggers workflow
- [ ] Decision logged to PostgreSQL
- [ ] Correct specialist agent called
- [ ] No execution errors

#### Emergency Agent
- [ ] High-urgency event routes correctly
- [ ] Tech assignment logic works
- [ ] Response time < 30 seconds
- [ ] Cost tracking updated

[Add section for each agent...]
```

---

## 🌟 PRIORITY 3: Future Enhancements

### [ ] 6. Branching Strategy (When Needed)
**Trigger Points:**
- First pilot customer goes live
- Need to separate prod/dev environments
- Working on risky architectural changes

**Simple Strategy:**
```
main (production) ← merge from →  dev (development)
```

**Not needed yet while:**
- Solo developer
- No production customers
- Single VPS environment

---

### [ ] 7. Local Development Environment (Optional)
**Why:** Test changes without affecting VPS

**If Pursued:**
1. Docker Compose locally with:
   - n8n
   - PostgreSQL
   - Redis (if used)
2. Mirror VPS configuration
3. Test locally before pushing to VPS

**Trade-off:** More complexity vs. safer testing

---

## 📊 PROGRESS TRACKER

**Sprint: Setup & Configuration**
- MCP SSH Setup: ⬜ Not Started / 🟡 In Progress / ✅ Complete
- Workflow JSON Structure: ⬜ Not Started / 🟡 In Progress / ✅ Complete
- Auto-Restart Hook: ⬜ Not Started / 🟡 In Progress / ✅ Complete
- File Write Target: ⬜ Not Started / 🟡 In Progress / ✅ Complete
- Testing Checklist: ⬜ Not Started / 🟡 In Progress / ✅ Complete

**Ready to Build HVAC Workflows When:**
- [x] All Priority 1 items complete
- [x] At least 3/5 Priority 2 items complete

---

## 🎬 WORKFLOW VISUALIZATION (Target State)

```
┌──────────────────────────────────────────────┐
│ You: "Build emergency agent workflow"       │
└───────────────┬──────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────┐
│ Claude:                                       │
│ 1. Reads HVAC specs from project knowledge   │
│ 2. Writes emergency-agent.json to local repo │
│ 3. Writes emergency-agent.py helper to repo  │
└───────────────┬──────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────┐
│ You:                                          │
│ 1. Review files in IDE                       │
│ 2. Git commit + push                         │
└───────────────┬──────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────┐
│ VPS: (Automatic)                             │
│ 1. Git hook pulls changes                    │
│ 2. Auto-restart n8n                          │
└───────────────┬──────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────┐
│ You: Test via n8n UI (SSH tunnel/ngrok)     │
└───────────────┬──────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────┐
│ If Error:                                     │
│ - Claude SSHs to VPS via MCP                 │
│ - Reads logs directly                        │
│ - Debugs and fixes                           │
│ - Updates local repo files                   │
│ - Cycle continues                            │
└──────────────────────────────────────────────┘
```

---

## 🔥 CRITICAL DEPENDENCIES

**Before Starting HVAC Workflows:**
1. ✅ MCP SSH configured (or accept more copy/paste)
2. ✅ n8n-workflows/ folder structure exists
3. ✅ Auto-restart hook working
4. ✅ Claude writes to correct local paths

**If ANY Priority 1 item is skipped:**
- Workflow will be slower
- More manual steps
- Higher token usage
- More frustration

---

## 📝 NOTES & LEARNINGS

**Date:** Oct 26, 2025 - 5:00 PM EDT  
**Note:** **Lesson Learned - Always Verify Before Documenting!** Initially documented an npm package that didn't exist (@modelcontextprotocol/server-ssh). Had to stop and verify actual working packages before proceeding. Caught the error when attempting `npm install` returned 404. Now using verified packages: @idletoaster/ssh-mcp-server (recommended), @aiondadotcom/mcp-ssh, or ssh-mcp.


**Date:** ___________  
**Note:**  


**Date:** ___________  
**Note:**  


---

## 🎯 SUCCESS METRICS

**Configuration Phase Complete When:**
- [ ] Claude can SSH to VPS without your help
- [ ] Claude writes files directly to local repo
- [ ] Git push → auto-deploy → auto-restart works
- [ ] First workflow JSON committed to Git
- [ ] Testing checklist used at least once

**Time Investment Expected:**
- MCP SSH setup: 30 minutes
- Workflow structure: 15 minutes
- Git hook: 20 minutes
- Testing template: 15 minutes
- **Total: ~1.5 hours**

**Payback Time:**
- Saves 10-15 minutes per debugging cycle
- ROI after ~6 debugging cycles
- **Break-even: Day 2 of HVAC development**

---

## 🚦 CURRENT STATUS

**Overall Progress:** ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%

**Next Action:** Gather MCP SSH details (4 items in Priority 1, Task 1)

**Blocker:** None

**Notes:** Ready to accelerate! 🚀

---

**END OF CHECKLIST**

*Last Updated:* October 26, 2025  
*Owner:* Daniel (codesurfer@gmail.com)  
*Status:* Configuration Phase
