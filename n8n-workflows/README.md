# n8n Workflows - Version Control

**Generated:** Tuesday, October 28, 2025 at 4:37 PM EDT

This directory contains all n8n workflow definitions as JSON files for version control and deployment.

---

## 📁 Directory Structure

```
n8n-workflows/
├── README.md                          ← You are here
├── primary-agent.json                 ← Main routing agent
├── emergency-agent.json               ← High-priority handler
├── customer-service-agent.json        ← Customer inquiries
├── scheduling-agent.json              ← Appointment management
├── billing-agent.json                 ← Payment processing
├── operations-agent.json              ← Internal ops
└── inventory-agent.json               ← Stock management
```

---

## 📥 How to Import Workflows into n8n

### Method 1: Via n8n UI (Recommended)

1. **Access n8n:**
   - SSH tunnel: `ssh -L 5678:localhost:5678 agent-vps`
   - Open browser: `http://localhost:5678`
   - OR use ngrok URL: `https://agents-platform.ngrok.io/`

2. **Import workflow:**
   - Click **"Add workflow"** (top right)
   - Click **"..."** menu → **"Import from file"**
   - Select the `.json` file from this directory
   - Click **"Open"**

3. **Activate workflow:**
   - Click **"Inactive"** toggle (top right) → **"Active"**
   - Verify the workflow name and settings

### Method 2: Via n8n CLI (Advanced)

```bash
# SSH into VPS
ssh agent-vps

# Import workflow
docker exec n8n n8n import:workflow --input=/data/workflow.json

# List all workflows
docker exec n8n n8n list:workflow
```

---

## 📤 How to Export Workflows from n8n

### After Making Changes in n8n UI:

1. **Open the workflow** you want to export

2. **Export to file:**
   - Click **"..."** menu (top right)
   - Click **"Download"**
   - File saves to your Downloads folder

3. **Move to this directory:**
   ```bash
   # Windows
   move %USERPROFILE%\Downloads\workflow-name.json C:\Users\codes\source\repos\ai-agent-platform\n8n-workflows\

   # Or just drag-and-drop from Downloads to this folder
   ```

4. **Commit to Git:**
   ```bash
   cd C:\Users\codes\source\repos\ai-agent-platform
   git add n8n-workflows/
   git commit -m "Update workflow-name workflow"
   git push origin main
   ```

5. **VPS auto-updates** (if Git hooks are configured)

---

## 🔄 Workflow Development Cycle

```
1. Edit in n8n UI → Test
2. Export as JSON → Save to this folder
3. Git commit + push
4. (Optional) VPS auto-pulls changes
5. Repeat for next change
```

---

## 🎯 Workflow Naming Convention

**Format:** `{purpose}-{type}.json`

**Examples:**
- ✅ `sms-hello-world.json`
- ✅ `customer-support-agent.json`
- ✅ `data-pipeline-processor.json`
- ❌ `Workflow 1.json` (too generic)
- ❌ `test.json` (not descriptive)
- ❌ `New Workflow Copy.json` (includes "Copy")

---

## 🚨 Important Notes

### Version Control Best Practices:

1. **Export after every significant change** - Don't rely on n8n's internal versioning alone
2. **Use descriptive commit messages** - "Add error handling to billing agent"
3. **Test before committing** - Execute the workflow at least once
4. **Document breaking changes** - Add notes in commit message

### What Gets Version Controlled:

- ✅ Workflow structure (nodes, connections)
- ✅ Node configurations
- ✅ Credentials references (NOT the actual credentials)
- ✅ Webhook paths
- ❌ Execution history (stored in n8n database)
- ❌ Actual credential values (stored separately)

### Security:

- **Never commit actual API keys or passwords** in workflow JSON
- Use n8n's credential system (references only)
- The JSON files contain credential IDs, not values

---

## 🔧 Troubleshooting

### Workflow Import Failed

**Problem:** Import shows error or workflow doesn't work

**Solutions:**
1. Check n8n version compatibility
2. Verify all required credentials exist
3. Check for node version mismatches
4. Re-create credentials if needed

### Credentials Missing After Import

**Problem:** Workflow imported but credentials not found

**Solution:** 
- Credentials are NOT included in workflow JSON
- You must manually recreate them in n8n UI
- Or import credentials separately (if you have a backup)

### Workflow Not Updating on VPS

**Problem:** Pushed to Git but n8n doesn't have new version

**Solution:**
1. Check if Git auto-pull is configured
2. Manually SSH and pull: `cd /opt/ai-agent-platform && git pull`
3. Re-import workflow in n8n UI
4. Workflows are NOT auto-imported - must be done manually in UI

---

## 📚 Additional Resources

- [n8n Documentation](https://docs.n8n.io/)
- [n8n Workflow Templates](https://n8n.io/workflows)
- [n8n CLI Reference](https://docs.n8n.io/hosting/cli-commands/)
- [Git Workflow Guide](../docs/n8n%20Workflow%20Source%20Control%20Strategy.pdf)

---

## 🎯 Quick Reference

```bash
# Check n8n status
ssh agent-vps "docker ps | grep n8n"

# View n8n logs
ssh agent-vps "docker logs n8n --tail 50"

# Restart n8n
ssh agent-vps "docker restart n8n"

# Access n8n UI
ssh -L 5678:localhost:5678 agent-vps
# Then open: http://localhost:5678
```

---

**Last Updated:** Tuesday, October 28, 2025  
**Maintainer:** Daniel (codesurfer@gmail.com)  
**Project:** AI Agent Platform - n8n Orchestration
