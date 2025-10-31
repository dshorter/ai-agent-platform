#!/usr/bin/env python3
"""
migrate_project_to_docs.py
Created: Thursday, October 30, 2025 - 6:18 PM EST
Purpose: Copy files from /mnt/project (Project Knowledge) to local docs/ structure
"""

import shutil
import os
from pathlib import Path
from datetime import datetime

# Get timestamp
now = datetime.now()
timestamp = now.strftime("%A, %B %d, %Y - %I:%M:%S %p EST")

print("=" * 70)
print("📁 Project Knowledge → Local Docs Migration Script")
print(f"Created: {timestamp}")
print("=" * 70)
print()

# Define paths
PROJECT_ROOT = Path(r"C:\Users\codes\source\repos\ai-agent-platform")
PROJECT_KNOWLEDGE = Path("/mnt/project")  # This is the Claude project knowledge path
DOCS_DIR = PROJECT_ROOT / "docs"

# File mapping: {source_filename: destination_path}
FILE_MIGRATIONS = {
    # Strategy docs → 90-misc/strategy/
    "90-Day_Side_Hustle_to_Startup_Master_Plan": "90-misc/strategy/90-day-master-plan.md",
    "AI_Agent_Observability_Market__2024-2025_Transformation_and_Growth_Analysis.md": "90-misc/strategy/market-analysis-2024-2025.md",
    "Solution_benchmark_analysis": "90-misc/strategy/solution-benchmark-analysis.md",
    "Core_Concepts__The_Intelligence_Moat_Philosophy.md": "90-misc/strategy/intelligence-moat-philosophy.md",
    
    # Business features → 90-misc/business-features/
    "Power_BI_Connector_MV": "90-misc/business-features/power-bi-connector-mvp.md",
    "SMB_Onboarding_Wizard_": "90-misc/business-features/smb-onboarding-wizard.md",
    "Gap_Analysis_": "90-misc/business-features/gap-analysis.md",
    "Business_Metrics_Layer_MVP": "90-misc/business-features/business-metrics-layer-mvp.md",
    
    # Project context → 90-misc/project-context/
    "PROJECT_STATE_2025.md": "90-misc/project-context/PROJECT_STATE_2025.md",
    "HVAC_Digital_Twin_Conversation_Context.md": "90-misc/project-context/hvac-conversation-context.md",
    "HVAC_Demo_Account_Tree.md": "90-misc/project-context/hvac-demo-account-tree.md",
    "Chat_context": "90-misc/project-context/chat-context.md",
    "First_context_": "90-misc/project-context/first-context.md",
    "hvac_digital_twin_project_plan.xlsx": "90-misc/project-context/hvac-project-plan.xlsx",
    
    # Customer facing → 04-customer-facing/solution-briefs/
    "Intelligence_Moat_Solution_Brief.docx": "04-customer-facing/solution-briefs/intelligence-moat-solution-brief.docx",
    
    # Infrastructure → 01-infrastructure/deployment/
    "Complete_Hetzner_VPS_Setup_Guide_for_AI_Agent_Platform": "01-infrastructure/deployment/hetzner-vps-setup-guide.md",
    
    # n8n workflows → 02-n8n-workflows/integration/
    "Twilio_SMS_Setup_Guide_-_Step_9.md": "02-n8n-workflows/integration/twilio-sms-setup-guide.md",
    "Set_up_for__ngrok___sms_____": "02-n8n-workflows/integration/ngrok-sms-setup.md",
    
    # Development → 05-development/
    "AI_Agent_Observability_-_Documentation_Standards__Startup_Speed_Edition_.md": "05-development/documentation-standards.md",
    "Sequence_aware__logging_system__LOG003_": "05-development/code-examples/sequence-aware-logging-log003.md",
    "-Friendly_Logging_Formatter_-_February_04__2025_-_LOG002.txt": "05-development/code-examples/friendly-logging-formatter-log002.txt",
}

# README templates
README_TEMPLATES = {
    "docs/README.md": """# Documentation Index

**Last Updated:** {timestamp}

## 📁 Folder Structure

### Staging
- **00-hopper/** - New files from Claude chats (triage weekly)

### Production Documentation
- **01-infrastructure/** - VPS, Docker, networking, security
- **02-n8n-workflows/** - n8n workflow documentation
- **03-database/** - Database schemas and visualizations
- **04-customer-facing/** - Presentations and solution briefs
- **05-development/** - Code examples and dev resources

### Miscellaneous
- **90-misc/** - Strategy, business features, project context
- **99-archive/** - Deprecated or outdated files

## 🔄 Hopper Workflow

1. Download artifacts from Claude chats → Save to `00-hopper/`
2. Weekly triage (Friday, 15 min):
   - Review new files in hopper
   - Move to appropriate category
   - Update relevant READMEs
3. Commit changes with descriptive message

## 📖 Philosophy

- **Project Knowledge:** Add freely, duplicates OK (9% capacity used)
- **Local Docs:** Single source of truth, clean organization
- **Hopper:** Bridge between chats and filesystem

---

*"Ascension by Repo is a Lie" - organized docs help ship faster!*
""",

    "docs/00-hopper/README.md": """# 00-hopper - Staging Area

**Purpose:** Temporary holding area for files downloaded from Claude chats

## Workflow

1. **Download** artifacts from Claude chats
2. **Save** to this folder with date prefix: `YYYY-MM-DD-filename.ext`
3. **Triage** weekly (Friday afternoon, 15 min):
   - Review files
   - Move to appropriate category
   - Delete if no longer needed
4. **Commit** changes

## Keep It Empty

This folder should be empty most of the time. If files pile up, schedule triage time.

---

*Weekly triage = 15 minutes of intentional organization*
""",

    "docs/01-infrastructure/README.md": """# 01-infrastructure - Infrastructure Documentation

**Purpose:** VPS deployment, Docker, networking, and security configuration

## Contents

- **deployment/** - Landing page, safe reboot system, deployment guides
- **networking/** - Security architecture, network configuration
- **monitoring/** - Health checks and system monitoring

## Key Documents

- `deployment/landing_page_deployment.md` - Static landing page deployment
- `deployment/safe-reboot/` - Safe reboot and health check system
- `networking/security-architecture.md` - Security hardening guide

---

*Production infrastructure on Hetzner VPS - $5/month*
""",

    "docs/02-n8n-workflows/README.md": """# 02-n8n-workflows - n8n Workflow Documentation

**Purpose:** n8n workflow architecture, development practices, and integrations

## Contents

- **architecture/** - System design, JSON contracts, baseline architecture
- **development/** - Version control, improvement checklists
- **integration/** - SMS, Twilio, LLM integration guides

## Key Documents

- `architecture/production-baseline-twilio-sms-n8n.pdf` - Current production setup
- `architecture/n8n-agent-project-pure-json.pdf` - JSON-based agent architecture
- `integration/technical-validation-n8n-sms-llm.pdf` - Best practices

---

*n8n + Grok + RAG = Intelligence automation platform*
""",

    "docs/03-database/README.md": """# 03-database - Database Documentation

**Purpose:** Database schemas, ERDs, and visualizations

## Contents

- **schema/** - Mermaid ERD definitions
- **visualizations/** - HTML interactive diagrams

## Key Documents

- `schema/hvac_database_erd.mermaid` - HVAC database schema definition
- `visualizations/hvac_database_diagram.html` - Interactive diagram
- `visualizations/hvac_database_erd.html` - ERD visualization

---

*HVAC digital twin database schema*
""",

    "docs/04-customer-facing/README.md": """# 04-customer-facing - Customer Documentation

**Purpose:** Presentations, demos, and solution briefs for prospects

## Contents

- **presentations/** - Slide decks and pitch presentations
- **solution-briefs/** - Solution briefs and case studies

## Key Documents

- `presentations/slide-1-problem.html` - Intelligence Moat problem slide
- `presentations/slide-2-proof.html` - Monday Morning Advantage proof
- `solution-briefs/intelligence-moat-solution-brief.docx` - Full solution brief

---

*Materials for pilot partner conversations*
""",

    "docs/05-development/README.md": """# 05-development - Development Resources

**Purpose:** Code examples, testing guides, and troubleshooting

## Contents

- **code-examples/** - Reusable code patterns and examples
- **testing/** - Test scenarios and testing guides
- **troubleshooting/** - Common issues and solutions

## Key Documents

- `code-examples/sequence-aware-logging.py` - Advanced logging system
- `documentation-standards.md` - Documentation best practices

---

*Developer productivity and code quality resources*
""",

    "docs/90-misc/README.md": """# 90-misc - Miscellaneous Documentation

**Purpose:** Strategy, business features, and project context that don't fit main categories

## Contents

- **business-features/** - Feature specs and MVP definitions
- **strategy/** - Strategic plans and market analysis
- **project-context/** - Project history and context documents

## Why This Exists

Some documents don't fit cleanly into infrastructure/n8n/database categories but are still important. This folder prevents "orphan files" in the root.

---

*Organized chaos for the stuff that doesn't fit elsewhere*
""",
}

def create_readmes():
    """Create README files in each directory"""
    print("📝 Creating README files...")
    for path, content in README_TEMPLATES.items():
        full_path = PROJECT_ROOT / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content.format(timestamp=timestamp))
        print(f"  ✅ Created {path}")
    print()

def migrate_files():
    """Copy files from project knowledge to local docs"""
    print("📦 Migrating files from Project Knowledge...")
    print(f"  Source: {PROJECT_KNOWLEDGE}")
    print(f"  Destination: {DOCS_DIR}")
    print()
    
    migrated = []
    skipped = []
    
    for source_name, dest_path in FILE_MIGRATIONS.items():
        source_file = PROJECT_KNOWLEDGE / source_name
        dest_file = DOCS_DIR / dest_path
        
        # Check if source exists in project knowledge
        if not source_file.exists():
            skipped.append(f"{source_name} (not in /mnt/project)")
            continue
        
        # Create destination directory
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        try:
            shutil.copy2(source_file, dest_file)
            migrated.append(f"{source_name} → {dest_path}")
            print(f"  ✅ {source_name}")
            print(f"     → {dest_path}")
        except Exception as e:
            skipped.append(f"{source_name} (error: {e})")
    
    print()
    print("=" * 70)
    print("📊 Migration Summary")
    print("=" * 70)
    print(f"✅ Migrated: {len(migrated)} files")
    if skipped:
        print(f"⏩ Skipped: {len(skipped)} files")
        for item in skipped:
            print(f"   - {item}")
    print()

def main():
    """Main execution"""
    print("🎯 Starting migration process...")
    print()
    
    # Step 1: Create README files
    create_readmes()
    
    # Step 2: Migrate files
    migrate_files()
    
    # Final summary
    print("=" * 70)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 70)
    print()
    print("🎯 Next Steps:")
    print("  1. Review migrated files: ls -R docs/")
    print("  2. Check README files in each folder")
    print("  3. Test that everything looks good")
    print("  4. Commit: git add docs/ && git commit -m 'DOCS: Migrate project knowledge to local docs'")
    print("  5. Push: git push origin main")
    print()
    print("💡 Remember: Project Knowledge = Add freely, Local Docs = Source of truth")
    print()

if __name__ == "__main__":
    main()
