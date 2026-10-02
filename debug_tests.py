import os
import django
from django.test.runner import DiscoverRunner

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookclub.settings')
django.setup()

runner = DiscoverRunner(verbosity=2, interactive=False)
failures = runner.run_tests(['books.tests'])
print('FAILURES_COUNT=', failures)
