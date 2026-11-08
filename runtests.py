#!/usr/bin/env python
"""Run the prblm-builder test suite against the bundled test project.

    python runtests.py                 # all tests
    python runtests.py prblm_builder.tests.test_builder.ReconcileTests
    python runtests.py makemigrations  # regenerate the test app's migrations
"""
import os
import sys

import django
from django.conf import settings
from django.core.management import call_command
from django.test.utils import get_runner


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    django.setup()
    args = sys.argv[1:]
    if args[:1] == ["makemigrations"]:
        call_command("makemigrations", "testapp")
        return 0
    runner = get_runner(settings)(verbosity=2)
    failures = runner.run_tests(args or ["prblm_builder", "tests"])
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
