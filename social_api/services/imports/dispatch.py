"""Indirection between the pipeline and the queue.

Task modules import the pipeline. If the pipeline imported the tasks back the two
would be circular, and -- more usefully -- the pipeline would stop being runnable
without a broker. These lazy hand-offs are the only place the two meet.
"""


def plan_batch(batch_id):
    from social_api.tasks.imports import plan_batch as task

    task.delay(batch_id)


def process_chunk(chunk_id):
    from social_api.tasks.imports import process_chunk as task

    task.delay(chunk_id)


def finalise_batch(batch_id):
    from social_api.tasks.imports import finalise_batch as task

    task.delay(batch_id)
