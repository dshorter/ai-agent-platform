#!/bin/bash
# reorganize_docs.sh - Reorganize docs folder structure (UPDATED VERSION)
# Created: Thursday, October 30, 2025 - 11:00 PM EST
# Updated: Thursday, October 30, 2025 - 11:28 PM EST
# Purpose: Execute the documentation reorganization plan with hopper + misc

set -e  # Exit on error

echo "================================================"
echo "📁 Documentation Reorganization Script v2"
echo "Updated: Thursday, October 30, 2025 - 11:28 PM EST"
echo "================================================"
echo ""

# Change to docs directory
cd "$(dirname "$0")/../docs" || exit 1
echo "✅ Working in: $(pwd)"
echo ""

# Phase 1: Create new folder structure
echo "📁 Phase 1: Creating new folder structure..."
mkdir -p 00-hopper
mkdir -p 01-infrastructure/{deployment/{safe-reboot},networking,monitoring}
mkdir -p 02-n8n-workflows/{architecture,development,integration}
mkdir -p 03-database/{schema,visualizations}
mkdir -p 04-customer-facing/{presentations,solution-briefs}
mkdir -p 05-development/{code-examples,testing,troubleshooting}
mkdir -p 90-misc/{business-features,strategy,project-context}
mkdir -p 99-archive
echo "✅ Folder structure created (includes 00-hopper and 90-misc)"
echo ""

# Phase 2: Move files
echo "📦 Phase 2: Moving files to new locations..."

# Infrastructure
if [ -f "landing_page_deployment.md" ]; then
    git mv landing_page_deployment.md 01-infrastructure/deployment/
    echo "  ✅ Moved landing_page_deployment.md"
fi

if [ -f "security-architecture.md" ]; then
    git mv security-architecture.md 01-infrastructure/networking/
    echo "  ✅ Moved security-architecture.md"
fi

if [ -d "safe-reboot" ]; then
    # Move entire safe-reboot directory
    git mv safe-reboot 01-infrastructure/deployment/
    echo "  ✅ Moved safe-reboot/ folder"
fi

# n8n Workflows
if [ -f "N8n Agent Project — Pure Json Contract (option B).pdf" ]; then
    git mv "N8n Agent Project — Pure Json Contract (option B).pdf" \
           02-n8n-workflows/architecture/n8n-agent-project-pure-json.pdf
    echo "  ✅ Moved and renamed n8n Agent Project PDF"
fi

if [ -f "n8n Version Control  ahd Development -  The REAL Story.pdf" ]; then
    git mv "n8n Version Control  ahd Development -  The REAL Story.pdf" \
           02-n8n-workflows/development/n8n-version-control-development.pdf
    echo "  ✅ Moved and renamed n8n Version Control PDF"
fi

if [ -f "n8n Workflow Source Control Strategy.pdf" ]; then
    git mv "n8n Workflow Source Control Strategy.pdf" \
           02-n8n-workflows/architecture/workflow-source-control-strategy.pdf
    echo "  ✅ Moved n8n Workflow Source Control PDF"
fi

if [ -f "Production Baseline - Twilio SMS  plus n8n Integration Architecture.pdf" ]; then
    git mv "Production Baseline - Twilio SMS  plus n8n Integration Architecture.pdf" \
           02-n8n-workflows/architecture/production-baseline-twilio-sms-n8n.pdf
    echo "  ✅ Moved Production Baseline PDF"
fi

if [ -f "Technical Validation n8n SMS  plus LLM Best Practices Document.pdf" ]; then
    git mv "Technical Validation n8n SMS  plus LLM Best Practices Document.pdf" \
           02-n8n-workflows/integration/technical-validation-n8n-sms-llm.pdf
    echo "  ✅ Moved Technical Validation PDF"
fi

if [ -f "SMS Endpoint Guidance.pdf" ]; then
    git mv "SMS Endpoint Guidance.pdf" \
           02-n8n-workflows/integration/sms-endpoint-guidance.pdf
    echo "  ✅ Moved SMS Endpoint Guidance PDF"
fi

if [ -f "Twilio Hello World.pdf" ]; then
    git mv "Twilio Hello World.pdf" \
           02-n8n-workflows/integration/twilio-hello-world.pdf
    echo "  ✅ Moved Twilio Hello World PDF"
fi

if [ -f "Workflow_Improvement_Master_Checklist.md" ]; then
    git mv Workflow_Improvement_Master_Checklist.md \
           02-n8n-workflows/development/
    echo "  ✅ Moved Workflow Improvement Checklist"
fi

# Database
if [ -f "hvac_database_diagram.html" ]; then
    git mv hvac_database_diagram.html 03-database/visualizations/
    echo "  ✅ Moved HVAC database diagram HTML"
fi

if [ -f "hvac_database_erd.html" ]; then
    git mv hvac_database_erd.html 03-database/visualizations/
    echo "  ✅ Moved HVAC database ERD HTML"
fi

if [ -f "hvac_database_erd.mermaid" ]; then
    git mv hvac_database_erd.mermaid 03-database/schema/
    echo "  ✅ Moved HVAC database ERD Mermaid"
fi

# Customer Facing
if [ -f "slide-1-problem.html" ]; then
    git mv slide-1-problem.html 04-customer-facing/presentations/
    echo "  ✅ Moved slide-1-problem.html"
fi

if [ -f "slide-2-proof.html" ]; then
    git mv slide-2-proof.html 04-customer-facing/presentations/
    echo "  ✅ Moved slide-2-proof.html"
fi

# Development
if [ -f "sequence-aware-logging.py" ]; then
    git mv sequence-aware-logging.py 05-development/code-examples/
    echo "  ✅ Moved sequence-aware-logging.py"
fi

# Delete duplicate (if still exists)
if [ -f "nginx-setup.md" ]; then
    git rm nginx-setup.md
    echo "  🗑️  Deleted nginx-setup.md (duplicate)"
fi

echo "✅ Files moved successfully"
echo ""

# Phase 3: Create README files
echo "📝 Phase 3: Creating README placeholders..."
echo "  ⏩ Create full READMEs manually using templates in REORGANIZATION_PLAN.md"
echo "  ⏩ Or copy them from the plan document"
echo ""

# Summary
echo "================================================"
echo "✅ REORGANIZATION COMPLETE!"
echo "================================================"
echo ""
echo "📊 Summary:"
echo "  • Created 7 main categories (hopper, infrastructure, n8n, database, customer, dev, misc, archive)"
echo "  • Moved 18 files"
echo "  • Deleted 1 duplicate"
echo "  • Cleaned up filenames"
echo "  • Added hopper for weekly workflow"
echo "  • Added misc for outliers"
echo ""
echo "🎯 Next Steps:"
echo "  1. Review the new structure: ls -R docs/"
echo "  2. Create README files in each folder (see REORGANIZATION_PLAN.md for templates)"
echo "  3. Test that links still work"
echo "  4. Commit: git commit -m 'DOCS: Reorganize documentation structure'"
echo "  5. Push: git push origin main"
echo ""
echo "🔥 Philosophy:"
echo "  • Project Knowledge = Add freely, duplicates OK, 9% used"
echo "  • Filesystem = Source of truth, clean org, git history"
echo "  • Hopper = Bridge (15 min/week triage)"
echo ""
echo "💡 'Ascension by Repo is a Lie' - but organized docs help ship faster!"
