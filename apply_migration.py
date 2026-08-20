#!/usr/bin/env python
"""
Script to apply the OTP status fields migration.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'asma_backend.settings')
sys.path.append('/d/desktop/virtualenv.worktrees/asma_backend-1')

try:
    django.setup()
    from django.core.management import execute_from_command_line
    print("Applying migration for OTP status fields...")
    execute_from_command_line(['manage.py', 'migrate', 'accounts'])
    print("Migration applied successfully!")
except Exception as e:
    print(f"Error applying migration: {e}")
    sys.exit(1)