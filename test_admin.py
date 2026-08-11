#!/usr/bin/env python
import os
import sys
import django
from django.conf import settings

# Add the project directory to the path
sys.path.insert(0, 'D:/desktop/virtualenv.worktrees/asma_backend-1')

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'asma_backend.settings')
django.setup()

# Now test the imports
try:
    from store.admin_site import admin_site
    print("SUCCESS: admin_site imported")
    print("admin_site:", admin_site)
    print("Type:", type(admin_site))
    if admin_site is not None:
        print("register:", admin_site.register)
        print("callable:", callable(admin_site.register))

        # Test importing admin models
        from store.admin import CategoryAdmin
        print("SUCCESS: CategoryAdmin imported")

        # Test registration
        from store.models import Category
        print("SUCCESS: Category model imported")

        # Try to register (this is what was failing)
        admin_site.register(Category, CategoryAdmin)
        print("SUCCESS: Category registered with admin_site")
    else:
        print("ERROR: admin_site is None")

except Exception as e:
    print("ERROR:", e)
    import traceback
    traceback.print_exc()