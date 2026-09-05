"""Celery wrappers around the import pipeline.

The pipeline holds the logic; these add the queue boundary and the retry policy.
Every pipeline entry point claims its row with a conditional UPDATE first, so
retrying or redelivering any of these tasks is safe.
"""

from celery import shared_task
from celery.utils.log import get_task_logger

from social_api.services.imports import pipeline

logger = get_task_logger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 10


@shared_task(bind=True, max_retries=MAX_RETRIES, default_retry_delay=RETRY_DELAY_SECONDS)
def plan_batch(self, batch_id):
    """Scan an upload into chunks and fan them out."""
    pipeline.plan_batch(batch_id)


@shared_task(bind=True, max_retries=MAX_RETRIES, default_retry_delay=RETRY_DELAY_SECONDS)
def process_chunk(self, chunk_id):
    """Import one chunk's byte range."""
    try:
        pipeline.process_chunk(chunk_id)
    except Exception as exc:  # noqa: BLE001 - retried, then recorded
        if self.request.retries >= self.max_retries:
            # Out of retries. Count the chunk as failed so the batch can still
            # reach a terminal state instead of hanging on it forever.
            pipeline.abandon_chunk(chunk_id, exc)
            return
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=MAX_RETRIES, default_retry_delay=RETRY_DELAY_SECONDS)
def finalise_batch(self, batch_id):
    """Close out a batch and delete its upload."""
    pipeline.finalise_batch(batch_id)
