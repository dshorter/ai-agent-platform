# 🚀 Quick Reference: Documentation Reorganization
**Created:** Thursday, October 30, 2025 - 11:04 PM EST  
**Keep this open while reorganizing!**

---

## 📋 Quick Decision Tree

```
Is it about...
│
├─ 🏗️ Infrastructure (VPS, Docker, nginx, security)?
│  └─ Move to: 01-infrastructure/
│     ├─ Deployment stuff? → deployment/
│     ├─ Network/security? → networking/
│     └─ Monitoring? → monitoring/
│
├─ 🔄 n8n Workflows (agents, integrations, SMS)?
│  └─ Move to: 02-n8n-workflows/
│     ├─ System design? → architecture/
│     ├─ Dev process? → development/
│     └─ Twilio/SMS/LLM? → integration/
│
├─ 🗄️ Database (schema, ERDs, migrations)?
│  └─ Move to: 03-database/
│     ├─ Source schema? → schema/
│     └─ Visual diagrams? → visualizations/
│
├─ 👥 Customer-Facing (slides, briefs, demos)?
│  └─ Move to: 04-customer-facing/
│     ├─ Presentation? → presentations/
│     └─ Solution brief? → solution-briefs/
│
├─ 💻 Development (code, tests, troubleshooting)?
│  └─ Move to: 05-development/
│     ├─ Code example? → code-examples/
│     ├─ Test guide? → testing/
│     └─ FAQ/issues? → troubleshooting/
│
└─ 📦 Old/Deprecated?
   └─ Move to: 99-archive/
```

---

## ⚡ File Quick Reference

| Current Filename | New Location | Quick Reason |
|-----------------|--------------|--------------|
| `landing_page_deployment.md` | `01-infrastructure/deployment/` | Infrastructure |
| `nginx-setup.md` | **DELETE** | Duplicate! |
| `security-architecture.md` | `01-infrastructure/networking/` | Network security |
| `safe-reboot/` | `01-infrastructure/deployment/safe-reboot/` | Deployment automation |
| `N8n Agent...pdf` | `02-n8n-workflows/architecture/` | Workflow architecture |
| `n8n Version...pdf` | `02-n8n-workflows/development/` | Dev process |
| `n8n Workflow...pdf` | `02-n8n-workflows/architecture/` | Workflow design |
| `Production Baseline...pdf` | `02-n8n-workflows/architecture/` | System architecture |
| `Technical Validation...pdf` | `02-n8n-workflows/integration/` | SMS/LLM integration |
| `SMS Endpoint...pdf` | `02-n8n-workflows/integration/` | SMS integration |
| `Twilio Hello...pdf` | `02-n8n-workflows/integration/` | SMS example |
| `Workflow_Improvement...md` | `02-n8n-workflows/development/` | Dev checklist |
| `hvac_database_diagram.html` | `03-database/visualizations/` | Visual diagram |
| `hvac_database_erd.html` | `03-database/visualizations/` | ERD diagram |
| `hvac_database_erd.mermaid` | `03-database/schema/` | Schema source |
| `slide-1-problem.html` | `04-customer-facing/presentations/` | Customer slide |
| `slide-2-proof.html` | `04-customer-facing/presentations/` | Customer slide |
| `sequence-aware-logging.py` | `05-development/code-examples/` | Code example |

---

## 🛠️ Commands Cheat Sheet

### Create Folders
```bash
cd docs/
mkdir -p 01-infrastructure/{deployment/{safe-reboot},networking,monitoring}
mkdir -p 02-n8n-workflows/{architecture,development,integration}
mkdir -p 03-database/{schema,visualizations}
mkdir -p 04-customer-facing/{presentations,solution-briefs}
mkdir -p 05-development/{code-examples,testing,troubleshooting}
mkdir -p 99-archive
```

### Move a File (preserves git history)
```bash
git mv old-filename.md new-folder/new-filename.md
```

### Move a Folder
```bash
git mv old-folder/ new-location/old-folder/
```

### Delete a File
```bash
git rm duplicate-file.md
```

### Check Status
```bash
git status
tree docs/  # See the new structure
```

---

## ✅ Validation Checklist

After reorganizing, verify:

- [ ] No files in docs/ root except README.md
- [ ] All 5 main folders exist (01-05)
- [ ] Each folder has subfolders as planned
- [ ] `nginx-setup.md` is deleted
- [ ] All PDFs have clean names (no spaces)
- [ ] `sequence-aware-logging.py` is in code-examples/
- [ ] Git history preserved (used `git mv` not `rm` + `add`)
- [ ] No broken links in any docs
- [ ] README.md created in docs/ root

---

## 🎯 Git Workflow

### Step 1: Make Changes
```bash
# Run the reorganization script or do it manually
./reorganize_docs.sh
```

### Step 2: Check What Changed
```bash
git status
# Should show:
# - renamed files (git mv preserves history)
# - deleted files (nginx-setup.md)
# - new files (READMEs)
```

### Step 3: Verify
```bash
# Make sure nothing broke
tree docs/
# Check that links still work (if any)
```

### Step 4: Commit
```bash
git add docs/
git commit -m "DOCS: Reorganize documentation structure for better discoverability

- Created 5 main categories (infrastructure, n8n, database, customer, dev)
- Moved 18 files to appropriate locations
- Deleted duplicate nginx-setup.md
- Fixed PDF filenames (removed spaces, fixed typos)
- Added READMEs for navigation
- Moved code files to proper locations"
```

### Step 5: Push
```bash
git push origin main
```

---

## 🚨 Emergency Rollback

If something goes wrong:

```bash
# Undo uncommitted changes
git reset --hard HEAD

# Undo last commit (but keep changes)
git reset HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1
```

---

## 💡 Pro Tips

1. **Use `git mv` not `mv`**
   - Preserves file history in git
   - GitHub shows "renamed" not "deleted + added"

2. **Check Before Deleting**
   - Make sure `nginx-setup.md` is actually a duplicate
   - Compare file contents first

3. **Test Links After**
   - If any docs reference other docs, update paths
   - Check if scripts reference old paths

4. **Create READMEs Last**
   - Move files first
   - Then create navigation READMEs

5. **Commit in Phases** (optional)
   - Phase 1: Create folders + move files
   - Phase 2: Add READMEs
   - Makes it easier to track changes

---

## 📊 Success Metrics

You'll know it worked when:

✅ You can find any doc in <30 seconds  
✅ New team members understand structure instantly  
✅ No confusion about which doc to use  
✅ Each category has clear purpose  
✅ Professional organization  

---

## 🔥 Remember

**"Ascension by Repo is a Lie"** 

This reorganization isn't about having perfect docs.  
It's about finding docs fast so you can **ship faster**.

---

**⏱️ Total Time: ~20 minutes**
- 5 min: Create folders
- 10 min: Move files
- 5 min: Create READMEs

**💰 Value: Hours saved every week not hunting for docs**

---

**Questions? Issues? Just ask! 🚀**
