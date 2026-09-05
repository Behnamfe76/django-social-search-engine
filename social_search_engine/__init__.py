# Imported here so Celery's app is configured whenever Django starts, which is
# what makes ``@shared_task`` bind to it.
from social_search_engine.celery import app as celery_app

__all__ = ["celery_app"]
