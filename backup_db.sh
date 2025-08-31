#!/bin/bash
# Database backup script for PythonAnywhere
# Add this to your scheduled tasks

cd /home/yourusername/budget-palnner  # Replace yourusername
cp budget.db "backups/budget_backup_$(date +%Y%m%d_%H%M%S).db"

# Keep only last 30 backups
ls -t backups/budget_backup_*.db | tail -n +31 | xargs rm -f
