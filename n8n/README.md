# EcoSense n8n Automation

This folder contains an importable n8n workflow template for Company/Industry operations.

## Files

- `ecosense_weekly_workflow.json` - Weekly schedule -> run EcoSense automation script -> send notification email.

## How to use

1. Import `ecosense_weekly_workflow.json` into n8n.
2. Update the command path if your project is in a different directory.
3. Configure email credentials for the `Send Ops Email` node.
4. Activate the workflow.

## Automation script

Workflow runs:

`python "d:/EcoSense LG/scripts/company_automation.py" --query "Provide weekly operational priorities and compliance-ready summary."`

Outputs:

- JSON summary: `outputs/automation/weekly_summary_*.json`
- PDFs: `outputs/reports/ecosense_report_*.pdf`
