"""Celery entry point.

Run a worker with::

    celery -A social_search_engine worker -l info

Task modules are discovered from every installed app's ``tasks`` package.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "social_search_engine.settings")

app = Celery("social_search_engine")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
