# 📥 Hopper Workflow - Project Knowledge to Filesystem
**Created:** Thursday, October 30, 2025 - 11:18 PM EST  
**Purpose:** Manage artifacts from project knowledge with proper versioning

---

## 🎯 The Problem

**Project Knowledge is great for context but bad for organization:**
- ❌ No timestamps on files (can't see when created)
- ❌ Allows duplicate filenames (confusion!)
- ❌ No version control (can't see what changed)
- ❌ No audit trail (who changed what when?)

**Solution:** Use filesystem + git as source of truth, project knowledge as reference.

---

## 🔄 The Hopper Workflow

```
┌─────────────────────────────────────┐
│  Chat Session with Claude           │
│  • Creates artifacts                │
│  • Adds to project knowledge        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  00-hopper/ (Staging Area)          │
│  • Download artifacts here          │
│  • Add date prefix to filename      │
│  • Git commit with chat date        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Weekly Triage (Every Friday)       │
│  • Review hopper contents           │
│  • Rename duplicates                │
│  • Move to proper categories        │
│  • Delete outdated versions         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Organized docs/ Structure          │
│  • Files in correct categories      │
│  • Git history preserved            │
│  • No duplicates                    │
│  • Timestamps via git               │
└─────────────────────────────────────┘
```

---

## 📁 Hopper Directory

### Location
```
docs/00-hopper/
```

### Naming Convention
```
YYYY-MM-DD-descriptive-name.ext

Examples:
✅ 2025-10-30-doc-reorg-plan.md
✅ 2025-10-30-hvac-schema-v2.sql
✅ 2025-10-29-solution-brief-draft.docx

❌ doc-reorg-plan.md  (no date)
❌ plan.md            (not descriptive)
```

---

## 🚀 Step-by-Step Process

### After Each Chat Session

#### Step 1: Identify New Artifacts
Ask yourself:
- Did Claude create any new documents?
- Did we update any existing documents?
- Are these in project knowledge?

#### Step 2: Download to Hopper
```bash
# Create hopper if it doesn't exist
mkdir -p docs/00-hopper

# Download from project knowledge to hopper
# (Manual download for now, or use Claude to create files)

# Add date prefix
mv document.md docs/00-hopper/2025-10-30-document.md
```

#### Step 3: Git Commit
```bash
git add docs/00-hopper/
git commit -m "HOPPER: Add artifacts from chat on Oct 30, 2025

- Added doc-reorg-plan.md
- Added hvac-schema-updates.sql
- Added solution-brief-v3.docx"

git push origin main
```

---

## 📅 Weekly Triage (Every Friday 4 PM)

### Step 1: Review Hopper Contents
```bash
cd docs/00-hopper
ls -la

# Check what's accumulated this week
git log --since="7 days ago" --oneline -- .
```

### Step 2: Identify Duplicates
```bash
# Find files with similar names
ls *.md | sort

# Example output:
# 2025-10-25-solution-brief.md
# 2025-10-30-solution-brief.md  ← Need to decide which to keep
```

### Step 3: Triage Decision Matrix

**For each file, ask:**

| Question | Keep in Hopper | Archive Old | Move to Category |
|----------|----------------|-------------|------------------|
| Is this the latest version? | - | ❌ Old → archive | ✅ Latest → category |
| Still WIP (work in progress)? | ✅ Keep | - | - |
| Obsolete/deprecated? | - | ✅ Archive | - |
| Duplicates another file? | - | ✅ Archive | ✅ Keep latest |
| Ready for final home? | - | - | ✅ Move |

### Step 4: Execute Moves
```bash
# Move finalized files to proper categories
git mv 00-hopper/2025-10-30-solution-brief.md \
       04-customer-facing/solution-briefs/intelligence-moat-v3.md

git mv 00-hopper/2025-10-30-hvac-schema.sql \
       03-database/schema/hvac-schema-2025-10-30.sql

# Archive old versions
git mv 00-hopper/2025-10-25-solution-brief.md \
       99-archive/solution-brief-v2-archived.md

# Commit the reorganization
git commit -m "TRIAGE: Weekly hopper cleanup - Oct 30, 2025

Moved:
- solution-brief.md → 04-customer-facing/ (latest version)
- hvac-schema.sql → 03-database/ (updated schema)

Archived:
- solution-brief-v2.md (superseded by v3)"

git push origin main
```

---

## 🎯 Hopper README Template

```markdown
# 📥 Hopper - Staging Area for New Documents

**Purpose:** Temporary holding area for artifacts downloaded from project knowledge before final organization.

## 📋 Rules

1. **All files must have date prefix:** `YYYY-MM-DD-filename.ext`
2. **Files stay here temporarily** (days to weeks, not months)
3. **Weekly triage** moves files to proper categories
4. **No direct edits** - files here are "as downloaded" from chats

## 🔄 Workflow

```
New Artifact → Hopper → Weekly Triage → Final Category
```

## 📅 Triage Schedule

**Every Friday at 4 PM:**
1. Review all files in hopper
2. Identify duplicates
3. Move finalized files to proper categories
4. Archive obsolete versions
5. Keep WIP files in hopper

## 🎯 Current Contents

*(This section updated each Friday during triage)*

**Last Triaged:** [Date]

**Files Waiting:**
- [ ] `2025-10-30-file1.md` - Needs review
- [ ] `2025-10-29-file2.sql` - WIP

**Next Triage:** [Next Friday Date]
```

---

## 🔧 Advanced: Automation Ideas

### Auto-Add Date Prefix Script
```bash
#!/bin/bash
# add-to-hopper.sh - Add file to hopper with date prefix

if [ $# -eq 0 ]; then
    echo "Usage: ./add-to-hopper.sh filename.ext"
    exit 1
fi

FILENAME=$1
DATE=$(date +%Y-%m-%d)
BASENAME=$(basename "$FILENAME")

# Move to hopper with date prefix
mv "$FILENAME" "docs/00-hopper/${DATE}-${BASENAME}"

echo "✅ Added to hopper: ${DATE}-${BASENAME}"
```

### Hopper Status Script
```bash
#!/bin/bash
# hopper-status.sh - Show hopper status

echo "📥 Hopper Status"
echo "================"
echo ""

cd docs/00-hopper

FILE_COUNT=$(ls -1 | wc -l)
echo "Files in hopper: $FILE_COUNT"
echo ""

echo "📅 Oldest file:"
ls -t | tail -1
echo ""

echo "📅 Newest file:"
ls -t | head -1
echo ""

echo "🔥 Files older than 14 days:"
find . -type f -mtime +14 | wc -l
```

---

## 💡 Pro Tips

### 1. Batch Downloads
After a productive chat session:
```bash
# Create dated subfolder for this chat
mkdir docs/00-hopper/2025-10-30-chat/

# Put all artifacts from this chat in this folder
# Makes it easy to triage as a batch later
```

### 2. Use Git Tags
```bash
# Tag significant triage sessions
git tag -a triage-2025-10-30 -m "Weekly triage Oct 30"
git push --tags

# Later, see what was in hopper at any triage date
git show triage-2025-10-30:docs/00-hopper/
```

### 3. Hopper Size Alert
```bash
# Add to your weekly routine
FILE_COUNT=$(ls docs/00-hopper | wc -l)
if [ $FILE_COUNT -gt 20 ]; then
    echo "⚠️  Hopper has $FILE_COUNT files! Time to triage!"
fi
```

---

## 🎯 Success Criteria

✅ Hopper never has more than 20 files  
✅ No file stays in hopper longer than 2 weeks  
✅ All files have date prefixes  
✅ Weekly triage happens consistently  
✅ Git history shows clear audit trail  
✅ No duplicate filenames in final categories  

---

## 🔄 Maintenance

### Monthly Audit (Last Friday of Month)
1. Check for files in hopper older than 30 days
2. Force-triage or archive anything stale
3. Review if naming conventions are working
4. Adjust workflow if needed

---

## 🚫 What NOT to Put in Hopper

- ❌ Final versions (go directly to proper category)
- ❌ Files already in git (no need to "re-stage")
- ❌ Temporary notes/scratchpad (use scratch.md in root)
- ❌ Large binary files (use .gitignore, link from project knowledge)

---

## 📊 Example Git History

```
* 2025-10-30 TRIAGE: Weekly hopper cleanup
* 2025-10-29 HOPPER: Add chat artifacts from Oct 29
* 2025-10-27 HOPPER: Add solution brief v3 draft
* 2025-10-23 TRIAGE: Weekly hopper cleanup
* 2025-10-22 HOPPER: Add database schema updates
```

**See the pattern?** Clear audit trail of what came in when, and when it was organized.

---

**🔥 Hopper = Your staging area for knowledge management! 📥**
