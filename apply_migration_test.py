#!/usr/bin/env python
import os
import sys
import django
from django.core.management import execute_from_command_line

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'asma_backend.settings')
django.setup()

# Try to show migrations
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

try:
    executor = MigrationExecutor(connection)
    applied = executor.loader.applied_migrations
    print("Applied migrations for accounts:")
    for app, name in sorted(applied):
        if app == 'accounts':
            print(f"  {app}.{name}")

    print("\nAll migration files for accounts:")
    from django.db.migrations.loader import MigrationLoader
    loader = MigrationLoader(connection)
    for app, name in sorted(loader.disk_migrations.keys()):
        if app == 'accounts':
            applied_marker = "[APPLIED]" if (app, name) in applied else "[PENDING]"
            print(f"  {app}.{name} {applied_marker}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()